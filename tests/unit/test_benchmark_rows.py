from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import DecisionRequest
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.orchestration.orchestrator import DecisionOrchestrator
from bench.rows import (
    build_payload_row,
    build_raw_fifo_row,
    has_constraint_violation,
    matches_expected,
    ticket_field_accuracy,
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
