from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.enums import FlowState
from app.domain.errors import PequiFluxError
from app.domain.models import DecisionRequest, ToolCallIntent
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.gemma import tool_gateway
from app.orchestration import tool_planner as tool_planner_module
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


class TextRuntimeReturningDisallowedTool(TextTicketRuntime):
    def generate_structured(self, *, prompt, response_model, metadata):
        if response_model is ToolCallIntent:
            return ToolCallIntent(
                tool_name="rank_candidates",
                request_id=str(metadata["request_id"]),
                purpose="test disallowed tool",
            )
        return super().generate_structured(
            prompt=prompt,
            response_model=response_model,
            metadata=metadata,
        )


class TextRuntimeReturningMismatchedRequestTool(TextTicketRuntime):
    def generate_structured(self, *, prompt, response_model, metadata):
        if response_model is ToolCallIntent:
            allowed_tools = metadata.get("allowed_tools") or []
            return ToolCallIntent(
                tool_name=allowed_tools[0],
                request_id="REQ-DIFFERENT",
                purpose="test mismatched request",
            )
        return super().generate_structured(
            prompt=prompt,
            response_model=response_model,
            metadata=metadata,
        )


class CapturingToolPlannerRuntime(TextTicketRuntime):
    def __init__(self) -> None:
        self.tool_requests: list[dict] = []

    def generate_structured(self, *, prompt, response_model, metadata):
        if response_model is ToolCallIntent:
            self.tool_requests.append(dict(metadata))
        return super().generate_structured(
            prompt=prompt,
            response_model=response_model,
            metadata=metadata,
        )


def _scenario_request(scenario_id: str, *, variant: str) -> DecisionRequest:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["scenario_id"] == scenario_id)
    return DecisionRequest.model_validate(case["request"]).model_copy(update={"variant": variant})


def _run_scenario(
    scenario_id: str,
    *,
    variant: str,
    runtime=None,
):
    request = _scenario_request(scenario_id, variant=variant)
    orchestrator = DecisionOrchestrator(
        gemma_adapter=GemmaAdapter(runtime=runtime or TextTicketRuntime()),
    )
    return orchestrator.run_decision(request)


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
    payload = _run_scenario("S10_FIFO_BREAK_JUSTIFIED", variant="full")

    assert payload.audit_record is not None
    tool_names = {record.tool_name for record in payload.audit_record.tool_calls}
    assert tool_names >= {
        "validate_hard_constraints",
        "rank_candidates",
        "generate_audit_payload",
    }
    assert {
        record.purpose for record in payload.audit_record.tool_calls if record.status == "executed"
    } == {"Deterministic CI tool intent."}
    assert {
        "choose_tool_validate_hard_constraints",
        "tool_validate_hard_constraints",
        "choose_tool_rank_candidates",
        "tool_rank_candidates",
        "choose_tool_generate_audit_payload",
        "tool_generate_audit_payload",
    } <= set(payload.latency_ms)
    assert payload.audit_record.latencies_ms == payload.latency_ms


def test_s10_full_tool_planner_offers_legal_tools_by_state():
    runtime = CapturingToolPlannerRuntime()

    payload = _run_scenario("S10_FIFO_BREAK_JUSTIFIED", variant="full", runtime=runtime)

    assert payload.decision_status == "PREVIEW_READY"
    assert [(item["current_state"], item["allowed_tools"]) for item in runtime.tool_requests] == [
        ("INTERPRETED", ["validate_hard_constraints"]),
        ("VALIDATED", ["rank_candidates"]),
        ("RANKED", ["generate_audit_payload"]),
    ]


def test_s10_full_payload_audits_tool_selection_error():
    payload = _run_scenario(
        "S10_FIFO_BREAK_JUSTIFIED",
        variant="full",
        runtime=TextRuntimeReturningDisallowedTool(),
    )

    assert payload.decision_status == "BLOCKED"
    assert payload.audit_record is not None
    assert [
        (record.tool_name, record.status, record.purpose, record.error_code)
        for record in payload.audit_record.tool_calls
    ] == [
        (
            "validate_hard_constraints",
            "error",
            "",
            "MODEL_TOOL_NOT_ALLOWED",
        )
    ]


@pytest.mark.parametrize("variant", ["fifo", "heuristic"])
def test_technical_variants_do_not_record_tool_calls(variant):
    payload = _run_scenario("S10_FIFO_BREAK_JUSTIFIED", variant=variant)

    assert payload.audit_record is not None
    assert payload.audit_record.tool_calls == []


def test_s10_full_payload_blocks_and_audits_request_id_mismatch():
    payload = _run_scenario(
        "S10_FIFO_BREAK_JUSTIFIED",
        variant="full",
        runtime=TextRuntimeReturningMismatchedRequestTool(),
    )

    assert payload.decision_status == "BLOCKED"
    assert payload.audit_record is not None
    assert [
        (record.tool_name, record.status, record.purpose, record.error_code)
        for record in payload.audit_record.tool_calls
    ] == [
        (
            "validate_hard_constraints",
            "error",
            "",
            "MODEL_TOOL_REQUEST_ID_MISMATCH",
        )
    ]


def test_s10_full_payload_uses_valid_tool_name_for_multi_tool_planner_error(monkeypatch):
    monkeypatch.setattr(
        tool_planner_module,
        "available_tools_for_state",
        lambda state: ["validate_hard_constraints", "rank_candidates"],
    )

    payload = _run_scenario(
        "S10_FIFO_BREAK_JUSTIFIED",
        variant="full",
        runtime=TextRuntimeReturningMismatchedRequestTool(),
    )

    assert payload.decision_status == "BLOCKED"
    assert payload.audit_record is not None
    assert [
        (record.tool_name, record.status, record.purpose, record.error_code)
        for record in payload.audit_record.tool_calls
    ] == [
        (
            "validate_hard_constraints",
            "error",
            "",
            "MODEL_TOOL_REQUEST_ID_MISMATCH",
        )
    ]


def test_s10_full_payload_blocks_and_audits_tool_order_error(monkeypatch):
    monkeypatch.setattr(
        tool_planner_module,
        "available_tools_for_state",
        lambda state: ["validate_hard_constraints"],
    )
    monkeypatch.setitem(
        tool_gateway.TOOL_STATE_ORDER,
        "validate_hard_constraints",
        {FlowState.RANKED.value},
    )

    payload = _run_scenario("S10_FIFO_BREAK_JUSTIFIED", variant="full")

    assert payload.decision_status == "BLOCKED"
    assert payload.audit_record is not None
    assert [
        (record.tool_name, record.status, record.purpose, record.error_code)
        for record in payload.audit_record.tool_calls
    ] == [
        (
            "validate_hard_constraints",
            "requested",
            "Deterministic CI tool intent.",
            None,
        ),
        (
            "validate_hard_constraints",
            "error",
            "Deterministic CI tool intent.",
            "TOOL_ORDER_ERROR",
        ),
    ]


def test_s10_full_payload_blocks_when_tool_step_limit_is_exceeded(monkeypatch):
    monkeypatch.setattr(tool_planner_module, "MAX_TOOL_STEPS", 1)

    payload = _run_scenario("S10_FIFO_BREAK_JUSTIFIED", variant="full")

    assert payload.decision_status == "BLOCKED"
    assert payload.audit_record is not None
    assert "exceeded 1 steps" in payload.reason_summary
    assert [(record.tool_name, record.status) for record in payload.audit_record.tool_calls] == [
        ("validate_hard_constraints", "requested"),
        ("validate_hard_constraints", "executed"),
    ]


def test_s03_review_required_full_payload_runs_audit_tool():
    payload = _run_scenario("S03_WET_LOAD", variant="full")

    assert payload.decision_status == "REVIEW_REQUIRED"
    assert payload.audit_record is not None
    audit_tool_records = [
        record
        for record in payload.audit_record.tool_calls
        if record.tool_name == "generate_audit_payload"
    ]
    assert [(record.status, record.purpose) for record in audit_tool_records] == [
        ("requested", "Deterministic CI tool intent."),
        ("executed", "Deterministic CI tool intent."),
    ]
