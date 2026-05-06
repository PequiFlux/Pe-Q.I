from __future__ import annotations

import json
from pathlib import Path

from app.domain.enums import FlowState
from app.domain.errors import PequiFluxError
from app.domain.models import DecisionRequest, ToolCallIntent
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.orchestration.orchestrator import DecisionOrchestrator


class RuntimeReturningTool:
    def __init__(self, tool_name: str, request_id: str):
        self.tool_name = tool_name
        self.request_id = request_id

    def generate_structured(self, *, prompt, response_model, metadata):
        return ToolCallIntent(
            tool_name=self.tool_name,
            request_id=self.request_id,
            purpose="test",
        )

    def summarize(self, *, prompt, metadata):
        return "summary"


def test_gemma_adapter_accepts_allowed_tool_call():
    adapter = GemmaAdapter(runtime=RuntimeReturningTool("validate_hard_constraints", "REQ-001"))
    intent = adapter.choose_tool(
        request_id="REQ-001",
        current_state=FlowState.INTERPRETED.value,
        allowed_tools=["validate_hard_constraints"],
        context_summary="test",
    )

    assert intent.tool_name == "validate_hard_constraints"


def test_gemma_adapter_rejects_disallowed_tool_call():
    adapter = GemmaAdapter(runtime=RuntimeReturningTool("rank_candidates", "REQ-001"))

    try:
        adapter.choose_tool(
            request_id="REQ-001",
            current_state=FlowState.INTERPRETED.value,
            allowed_tools=["validate_hard_constraints"],
            context_summary="test",
        )
    except PequiFluxError as exc:
        assert exc.code == "MODEL_TOOL_NOT_ALLOWED"
    else:
        raise AssertionError("Expected PequiFluxError")


def test_s10_full_payload_records_required_tool_calls():
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    case = next(
        item for item in manifest["cases"] if item["scenario_id"] == "S10_FIFO_BREAK_JUSTIFIED"
    )
    request = DecisionRequest.model_validate(case["request"]).model_copy(update={"variant": "full"})
    orchestrator = DecisionOrchestrator(
        gemma_adapter=GemmaAdapter(runtime=TextTicketRuntime()),
    )

    payload = orchestrator.run_decision(request)

    assert payload.audit_record is not None
    tool_names = {record.tool_name for record in payload.audit_record.tool_calls}
    assert tool_names >= {
        "validate_hard_constraints",
        "rank_candidates",
        "generate_audit_payload",
    }
