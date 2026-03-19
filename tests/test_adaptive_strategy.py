from __future__ import annotations

from typing import Any

from ontology_negotiator.agents import NegotiationAgents
from ontology_negotiator.config import OptimizationConfig


class DummyLLM:
    model_name = "dummy"


def _base_state() -> dict[str, Any]:
    return {
        "iterations": 2,
        "node_data": {"node_id": "node-1", "name": "node", "l_level": "L2", "description": "template node"},
        "graph_context": {"neighbors": [], "edges": []},
        "vault_context": {"matched": True, "evidence": ["foundation"], "reason": "", "related_l2_nodes": []},
        "proposal": {
            "label": "类",
            "confidence_hint": 0.92,
            "reason": "looks reusable",
            "core_evidence": ["node_data.description"],
            "uncertainties": [],
            "revision_strategy": "focus",
        },
        "critique": {
            "stance": "支持",
            "reason": "agrees",
            "counter_evidence": [],
            "suggested_label": "类",
            "open_questions": [],
            "consensus_signal": True,
            "remaining_gaps": [],
        },
        "history": [],
        "debate_focus": "",
        "debate_gaps": [],
        "round_summaries": [],
        "persistent_evidence": [],
        "resolved_evidence": [],
        "evidence_events": [],
        "loop_detected": False,
        "loop_reason": "",
        "case_closed": False,
        "agent_errors": [],
        "llm_trace": [],
        "cache_hits": {"vault": 0, "agent": 0, "total": 0},
    }


def _fake_arbiter_response() -> dict[str, Any]:
    return {
        "arbiter_action": "finalize",
        "decision_reason_type": "evidence_closed",
        "final_label": "类",
        "case_closed": True,
        "loop_detected": False,
        "loop_reason": "",
        "decision_reason": "ok",
        "next_focus": "",
        "retry_reason_type": None,
        "consensus_status": "closed",
        "resolved_evidence_ids": [],
        "retained_evidence_ids": [],
        "new_evidence_ids": [],
    }


def test_adaptive_fast_path_sets_execution_path_and_reason(monkeypatch) -> None:
    state = _base_state()
    agents = NegotiationAgents(
        llm=DummyLLM(),
        optimization=OptimizationConfig(
            enable_adaptive_rounds=True,
            fast_path_max_rounds=2,
            quality_guardrail_min_agreement=0.90,
            enable_tool_calling=False,
            enable_layer_cache=False,
        ),
    )

    def fake_invoke_agent(*, agent_name, payload, state):
        assert agent_name == "arbiter"
        return _fake_arbiter_response()

    monkeypatch.setattr(agents, "_invoke_agent", fake_invoke_agent)

    result = agents.arbiter_node(state)

    assert result["arbiter_action"] == "finalize"
    assert result["execution_path"] == "fast"
    assert "fast_path" in result["early_exit_reason"]


def test_adaptive_conflict_forces_deep_path(monkeypatch) -> None:
    state = _base_state()
    state["critique"]["stance"] = "反对"
    state["critique"]["consensus_signal"] = False

    agents = NegotiationAgents(
        llm=DummyLLM(),
        optimization=OptimizationConfig(
            enable_adaptive_rounds=True,
            fast_path_max_rounds=2,
            quality_guardrail_min_agreement=0.90,
            enable_tool_calling=False,
            enable_layer_cache=False,
        ),
    )

    def fake_invoke_agent(*, agent_name, payload, state):
        assert agent_name == "arbiter"
        return _fake_arbiter_response()

    monkeypatch.setattr(agents, "_invoke_agent", fake_invoke_agent)

    result = agents.arbiter_node(state)

    assert result["execution_path"] == "deep"

