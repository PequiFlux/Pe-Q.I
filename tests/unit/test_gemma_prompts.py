from __future__ import annotations

from app.gemma.prompts import build_tool_call_prompt


def test_build_tool_call_prompt_restricts_tool_intent_contract() -> None:
    prompt = build_tool_call_prompt(
        request_id="REQ-001",
        current_state="INTERPRETED",
        allowed_tools=["validate_hard_constraints", "rank_candidates"],
        context_summary="Ticket parsed and truth resolved.",
    )

    assert "ToolCallIntent schema" in prompt
    assert "Do not make dispatch decisions" in prompt
    assert "The tool arguments are restricted to request_id" in prompt
    assert "Request id: REQ-001" in prompt
    assert "Current state: INTERPRETED" in prompt
    assert "Allowed tools: validate_hard_constraints, rank_candidates" in prompt
