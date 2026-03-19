from __future__ import annotations

"""Utilities for layered optimization: cache, tool-call parsing, and usage stats."""

import copy
import hashlib
import json
import threading
from typing import Any


def resolve_model_name(llm: Any | None) -> str | None:
    if llm is None:
        return None
    for attr in ("model_name", "model", "name", "model_id"):
        value = getattr(llm, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return type(llm).__name__


def stable_cache_key(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def extract_response_token_usage(response: Any) -> dict[str, int | None]:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None

    usage_metadata = getattr(response, "usage_metadata", None)
    if isinstance(usage_metadata, dict):
        prompt_tokens = usage_metadata.get("input_tokens")
        completion_tokens = usage_metadata.get("output_tokens")
        total_tokens = usage_metadata.get("total_tokens")

    response_metadata = getattr(response, "response_metadata", None)
    if isinstance(response_metadata, dict):
        token_usage = response_metadata.get("token_usage")
        if isinstance(token_usage, dict):
            prompt_tokens = token_usage.get("prompt_tokens", prompt_tokens)
            completion_tokens = token_usage.get("completion_tokens", completion_tokens)
            total_tokens = token_usage.get("total_tokens", total_tokens)

    def _as_int(value: Any) -> int | None:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
        return None

    prompt_tokens = _as_int(prompt_tokens)
    completion_tokens = _as_int(completion_tokens)
    total_tokens = _as_int(total_tokens)
    if total_tokens is None and prompt_tokens is not None and completion_tokens is not None:
        total_tokens = prompt_tokens + completion_tokens

    return {
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": total_tokens,
    }


def extract_tool_call_arguments(raw_response: Any) -> dict[str, Any]:
    tool_calls = getattr(raw_response, "tool_calls", None)
    additional_kwargs = getattr(raw_response, "additional_kwargs", None)

    candidates: list[Any] = []
    if isinstance(tool_calls, list):
        candidates.extend(tool_calls)
    if isinstance(additional_kwargs, dict):
        nested = additional_kwargs.get("tool_calls")
        if isinstance(nested, list):
            candidates.extend(nested)

    if not candidates:
        raise ValueError("Model response does not contain tool calls.")

    for candidate in candidates:
        args: Any = None
        if isinstance(candidate, dict):
            if "args" in candidate:
                args = candidate.get("args")
            elif "arguments" in candidate:
                args = candidate.get("arguments")
            elif isinstance(candidate.get("function"), dict):
                fn_payload = candidate["function"]
                args = fn_payload.get("arguments")

        if isinstance(args, dict):
            return args
        if isinstance(args, str):
            parsed = json.loads(args)
            if isinstance(parsed, dict):
                return parsed

    raise ValueError("Tool call arguments are missing or invalid.")


class LayerCacheStore:
    """Thread-safe cache store for vault and agent layers."""

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self._vault: dict[str, dict[str, Any]] = {}
        self._agent: dict[str, dict[str, Any]] = {}
        self._lock = threading.Lock()

    def get_vault(self, key: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        with self._lock:
            value = self._vault.get(key)
        return copy.deepcopy(value) if value is not None else None

    def set_vault(self, key: str, value: dict[str, Any]) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._vault[key] = copy.deepcopy(value)

    def get_agent(self, key: str) -> dict[str, Any] | None:
        if not self.enabled:
            return None
        with self._lock:
            value = self._agent.get(key)
        return copy.deepcopy(value) if value is not None else None

    def set_agent(self, key: str, value: dict[str, Any]) -> None:
        if not self.enabled:
            return
        with self._lock:
            self._agent[key] = copy.deepcopy(value)

