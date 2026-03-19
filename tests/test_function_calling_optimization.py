from __future__ import annotations

import pytest

from ontology_negotiator.agents import NegotiationAgents
from ontology_negotiator.config import OptimizationConfig
from ontology_negotiator.errors import NegotiationExecutionError


class DummyToolResponse:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


class ToolSuccessLLM:
    model_name = "tool-success"

    def bind_tools(self, tools, tool_choice="any"):
        class Bound:
            def invoke(self, messages):
                return DummyToolResponse(
                    [
                        {
                            "name": "ProposalPayload",
                            "args": {
                                "label": "类",
                                "confidence_hint": 0.83,
                                "reason": "matches reusable template",
                                "core_evidence": ["evidence_pack.node.description"],
                                "uncertainties": [],
                                "revision_strategy": "keep focus",
                            },
                        }
                    ]
                )

        return Bound()

    def invoke(self, messages):
        return "{}"


class ToolFallbackLLM:
    model_name = "tool-fallback"

    def bind_tools(self, tools, tool_choice="any"):
        class Bound:
            def invoke(self, messages):
                return DummyToolResponse([{"name": "ProposalPayload", "args": "not-json"}])

        return Bound()

    def invoke(self, messages):
        return """{
          "label": "类",
          "confidence_hint": 0.74,
          "reason": "fallback json path",
          "core_evidence": [],
          "uncertainties": [],
          "revision_strategy": "retry"
        }"""


class ToolFailureLLM:
    model_name = "tool-failure"

    def bind_tools(self, tools, tool_choice="any"):
        class Bound:
            def invoke(self, messages):
                return DummyToolResponse([{"name": "ProposalPayload", "args": "not-json"}])

        return Bound()

    def invoke(self, messages):
        return """{
          "label": "类",
          "confidence_hint": 0.74,
          "reason": "should not be used"
        }"""


def _state() -> dict:
    return {
        "iterations": 1,
        "node_data": {"node_id": "node-1"},
        "graph_context": {"neighbors": [], "edges": []},
        "vault_context": {"matched": False, "evidence": [], "reason": "", "related_l2_nodes": []},
        "proposal": {},
        "critique": {},
        "history": [],
        "round_summaries": [],
        "llm_trace": [],
        "agent_errors": [],
        "cache_hits": {"vault": 0, "agent": 0, "total": 0},
        "persistent_evidence": [],
        "resolved_evidence": [],
        "evidence_events": [],
    }


def _payload() -> dict:
    return {
        "evidence_pack": {"node": {}, "graph": {}, "vault": {}},
        "working_memory": {},
        "last_critique": {},
        "iteration": 1,
    }


def test_tool_call_success_path() -> None:
    agents = NegotiationAgents(
        llm=ToolSuccessLLM(),
        optimization=OptimizationConfig(
            enable_tool_calling=True,
            tool_call_fallback_json=True,
            enable_layer_cache=False,
        ),
    )

    result = agents._invoke_agent(agent_name="proposer", payload=_payload(), state=_state())

    assert result["label"] == "类"
    assert result["confidence_hint"] == pytest.approx(0.83)


def test_tool_call_falls_back_to_json_when_enabled() -> None:
    state = _state()
    agents = NegotiationAgents(
        llm=ToolFallbackLLM(),
        optimization=OptimizationConfig(
            enable_tool_calling=True,
            tool_call_fallback_json=True,
            enable_layer_cache=False,
        ),
    )

    result = agents._invoke_agent(agent_name="proposer", payload=_payload(), state=state)

    assert result["reason"] == "fallback json path"
    assert any(item.get("stage") == "tool_call" for item in state["llm_trace"])


def test_tool_call_failure_raises_when_json_fallback_disabled() -> None:
    agents = NegotiationAgents(
        llm=ToolFailureLLM(),
        optimization=OptimizationConfig(
            enable_tool_calling=True,
            tool_call_fallback_json=False,
            enable_layer_cache=False,
        ),
    )

    with pytest.raises(NegotiationExecutionError) as exc_info:
        agents._invoke_agent(agent_name="proposer", payload=_payload(), state=_state())

    assert exc_info.value.stage == "tool_call"

