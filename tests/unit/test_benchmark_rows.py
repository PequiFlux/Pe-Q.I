from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import DecisionRequest
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.orchestration.orchestrator import DecisionOrchestrator
from bench.rows import (
    audit_complete,
    build_payload_row,
    build_raw_fifo_row,
    has_constraint_violation,
    matches_expected,
    pair_rejected,
    ticket_field_accuracy,
    tool_call_metrics,
)


def _case(scenario_id: str) -> dict:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    return next(item for item in manifest["cases"] if item["scenario_id"] == scenario_id)


def _request(scenario_id: str, variant: str) -> DecisionRequest:
    return DecisionRequest.model_validate(_case(scenario_id)["request"]).model_copy(
        update={"variant": variant}
    )


def _expected(scenario_id: str) -> dict:
    case = _case(scenario_id)
    return json.loads(Path(case["files"]["expected_decision"]).read_text(encoding="utf-8"))


def _orchestrator() -> DecisionOrchestrator:
    return DecisionOrchestrator(gemma_adapter=GemmaAdapter(runtime=TextTicketRuntime()))


def test_build_raw_fifo_row_marks_constraint_violation_from_fifo_safe_audit() -> None:
    scenario_id = "S10_FIFO_BREAK_JUSTIFIED"
    fifo_safe_payload = _orchestrator().run_decision(_request(scenario_id, "fifo"))

    row = build_raw_fifo_row(
        request=_request(scenario_id, "full"),
        expected=_expected(scenario_id),
        fifo_safe_payload=fifo_safe_payload,
    )

    assert row["variant"] == "raw_fifo"
    assert row["recommended_truck"] == "TRK-001"
    assert row["recommended_destination"] == "DST-OPEN-01"
    assert row["constraint_violation"] is True
    assert row["decision_match_at_1"] is False
    assert row["tool_call_count"] == 0
    assert row["tool_call_success"] is False
    assert row["tool_path"] == ""
    assert row["tool_error_count"] == 0
    assert row["planner_step_count"] == 0


def test_build_raw_fifo_row_marks_unknown_destination_as_constraint_violation() -> None:
    scenario_id = "S15_UNKNOWN_DESTINATION_IN_TICKET"
    fifo_safe_payload = _orchestrator().run_decision(_request(scenario_id, "fifo"))

    row = build_raw_fifo_row(
        request=_request(scenario_id, "full"),
        expected=_expected(scenario_id),
        fifo_safe_payload=fifo_safe_payload,
    )

    assert row["recommended_truck"] == "TRK-051"
    assert row["recommended_destination"] == "DST-GHOST-99"
    assert row["constraint_violation"] is True
    assert row["decision_match_at_1"] is False


def test_pair_rejected_marks_unknown_destination_as_constraint_violation() -> None:
    scenario_id = "S15_UNKNOWN_DESTINATION_IN_TICKET"
    fifo_safe_payload = _orchestrator().run_decision(_request(scenario_id, "fifo"))

    assert fifo_safe_payload.audit_record is not None
    assert not any(
        checked["truck_id"] == "TRK-051" and checked["destination_id"] == "DST-UNKNOWN"
        for checked in fifo_safe_payload.audit_record.hard_constraints_checked
    )
    assert pair_rejected(fifo_safe_payload, "TRK-051", "DST-UNKNOWN") is True


def test_build_payload_row_and_expected_match_for_full_payload() -> None:
    scenario_id = "S10_FIFO_BREAK_JUSTIFIED"
    expected = _expected(scenario_id)
    payload = _orchestrator().run_decision(_request(scenario_id, "full"))

    row = build_payload_row(
        scenario_id=scenario_id,
        variant="full",
        payload=payload,
        expected=expected,
        ticket_field_accuracy=1.0,
    )

    assert matches_expected(payload, expected) is True
    assert has_constraint_violation(payload) is False
    assert row["decision_match_at_1"] is True
    assert row["constraint_violation"] is False
    assert row["fifo_break"] is True
    assert row["audit_complete"] is True
    assert row["tool_call_count"] == 6
    assert row["tool_call_success"] is True
    assert row["tool_path"] == "validate_hard_constraints>rank_candidates>generate_audit_payload"
    assert row["tool_error_count"] == 0
    assert row["planner_step_count"] == 3
    assert set(row) >= {
        "latency_ms_preprocess",
        "latency_ms_model",
        "latency_ms_rules",
        "latency_ms_audit",
        "latency_ms_total",
    }
    assert row["latency_ms_total"] == (
        row["latency_ms_preprocess"]
        + row["latency_ms_model"]
        + row["latency_ms_rules"]
        + row["latency_ms_audit"]
    )


def test_audit_complete_is_status_aware_for_preview_ready_payload() -> None:
    scenario_id = "S10_FIFO_BREAK_JUSTIFIED"
    payload = _orchestrator().run_decision(_request(scenario_id, "full"))

    assert payload.decision_status == "PREVIEW_READY"
    assert payload.audit_record is not None
    assert payload.audit_record.hard_constraints_checked
    assert payload.audit_record.recommended_pair is not None
    assert audit_complete(payload) is True


def test_audit_complete_requires_recommendation_for_preview_ready_payload() -> None:
    scenario_id = "S10_FIFO_BREAK_JUSTIFIED"
    payload = _orchestrator().run_decision(_request(scenario_id, "full"))
    assert payload.audit_record is not None

    payload_without_recommendation = payload.model_copy(
        update={
            "recommended_truck": None,
            "recommended_destination": None,
            "audit_record": payload.audit_record.model_copy(update={"recommended_pair": None}),
        }
    )

    assert audit_complete(payload_without_recommendation) is False


def test_audit_complete_is_status_aware_for_review_required_payload() -> None:
    scenario_id = "S03_WET_LOAD"
    payload = _orchestrator().run_decision(_request(scenario_id, "full"))

    assert payload.decision_status == "REVIEW_REQUIRED"
    assert payload.audit_record is not None
    assert payload.audit_record.hard_constraints_checked == []
    assert audit_complete(payload) is True
    assert tool_call_metrics(payload) == {
        "tool_call_count": 2,
        "tool_call_success": True,
        "tool_path": "generate_audit_payload",
        "tool_error_count": 0,
        "planner_step_count": 1,
    }


def test_audit_complete_requires_terminal_context_for_review_required_payload() -> None:
    scenario_id = "S03_WET_LOAD"
    payload = _orchestrator().run_decision(_request(scenario_id, "full"))

    payload_without_terminal_context = payload.model_copy(update={"reason_summary": ""})

    assert audit_complete(payload_without_terminal_context) is False


def test_audit_complete_is_status_aware_for_blocked_payload() -> None:
    scenario_id = "S16_ALL_DESTINATIONS_BLOCKED"
    payload = _orchestrator().run_decision(_request(scenario_id, "full"))

    assert payload.decision_status == "BLOCKED"
    assert payload.audit_record is not None
    assert payload.audit_record.hard_constraints_checked == []
    assert audit_complete(payload) is True
    assert tool_call_metrics(payload) == {
        "tool_call_count": 4,
        "tool_call_success": True,
        "tool_path": "validate_hard_constraints",
        "tool_error_count": 0,
        "planner_step_count": 2,
    }


def test_audit_complete_requires_terminal_context_for_blocked_payload() -> None:
    scenario_id = "S16_ALL_DESTINATIONS_BLOCKED"
    payload = _orchestrator().run_decision(_request(scenario_id, "full"))

    payload_without_terminal_context = payload.model_copy(update={"reason_summary": ""})

    assert audit_complete(payload_without_terminal_context) is False


def test_audit_complete_requires_all_source_hashes_for_terminal_payload() -> None:
    scenario_id = "S16_ALL_DESTINATIONS_BLOCKED"
    payload = _orchestrator().run_decision(_request(scenario_id, "full"))
    assert payload.audit_record is not None

    partial_hashes = {
        key: value
        for key, value in payload.audit_record.source_hashes.items()
        if key != "weather_state"
    }
    payload_without_weather_hash = payload.model_copy(
        update={
            "audit_record": payload.audit_record.model_copy(
                update={"source_hashes": partial_hashes}
            )
        }
    )

    assert audit_complete(payload_without_weather_hash) is False


def test_audit_complete_requires_provenance_for_terminal_payload() -> None:
    scenario_id = "S16_ALL_DESTINATIONS_BLOCKED"
    payload = _orchestrator().run_decision(_request(scenario_id, "full"))
    assert payload.audit_record is not None

    payload_without_provenance = payload.model_copy(
        update={"audit_record": payload.audit_record.model_copy(update={"provenance": []})}
    )

    assert audit_complete(payload_without_provenance) is False


def test_ticket_field_accuracy_scores_declared_fields() -> None:
    expected = {
        "ticket_id": "TCK-001",
        "truck_id": "TRK-001",
        "vehicle_type": "truck",
        "document_status": "clear",
        "document_block_flags": [],
        "load_condition": "dry",
        "contract_priority_flag": False,
        "destination_constraints": [],
    }
    observed = {**expected, "load_condition": "wet", "destination_constraints": ["covered"]}

    assert ticket_field_accuracy(observed, expected) == 0.75
