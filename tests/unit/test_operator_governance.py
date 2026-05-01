from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from app.domain.enums import DecisionStatus, OperatorAction
from app.domain.errors import PequiFluxError
from app.domain.models import FrontEndPayload
from app.services.operator_governance import finalize_operator_decision
from app.storage.sqlite_store import SQLiteStore


def _payload() -> FrontEndPayload:
    data = {
        "request_id": "REQ-001",
        "scenario_id": "S09_HUMAN_OVERRIDE",
        "variant": "full",
        "decision_status": "PREVIEW_READY",
        "recommended_truck": {
            "truck_id": "TRK-001",
            "queue_position_before": 1,
            "queue_position_after": 1,
        },
        "recommended_destination": {
            "destination_id": "DST-COV-01",
            "destination_type": "resource",
        },
        "reason_summary": "Preview ready.",
        "driver_message": {
            "message": "Driver message.",
            "template_id": "preview_ptbr_v1",
        },
        "operator_actions": ["approve", "block", "override"],
        "queue_diff": [],
        "gemma_visible_summary": {
            "parsed_fields": [],
            "exception_label": "RAIN_ON_OPEN_DESTINATION",
            "notes": [],
        },
        "latency_ms": {"validate_hard_constraints": 1},
        "benchmark_tags": [],
        "confidence_notes": [],
        "audit_record": {
            "decision_id": "DEC-001",
            "request_id": "REQ-001",
            "scenario_id": "S09_HUMAN_OVERRIDE",
            "variant": "full",
            "hard_constraints_checked": [
                {
                    "truck_id": "TRK-002",
                    "destination_id": "DST-COV-01",
                    "eligible": True,
                    "failed_constraints": [],
                },
                {
                    "truck_id": "TRK-003",
                    "destination_id": "DST-OPEN-01",
                    "eligible": False,
                    "failed_constraints": [
                        {
                            "constraint_id": "HC-01",
                            "severity": "hard",
                            "source": "weather_state",
                            "detail": "Open destination blocked by precipitation.",
                        }
                    ],
                },
            ],
            "fired_rules": ["PR-01"],
            "rejected_candidates": [],
            "recommended_pair": {
                "truck_id": "TRK-001",
                "destination_id": "DST-COV-01",
            },
            "fifo_break": False,
            "provenance": [{"field": "weather_state", "source": "weather_state"}],
            "latencies_ms": {"validate_hard_constraints": 1},
            "source_hashes": {"queue_csv_ref": "queue.csv", "ticket_ref": "ticket.txt"},
        },
    }
    return FrontEndPayload.model_validate(data)


def test_finalize_approve_persists_domain_objects_and_audit_update(tmp_path: Path) -> None:
    db_path = tmp_path / "pequiflux.db"
    store = SQLiteStore(path=str(db_path))
    payload = _payload()

    finalized, updated_audit = finalize_operator_decision(
        payload=payload,
        action_type=OperatorAction.APPROVE,
        reason="Supervisor approved the preview.",
        actor_id="OP-DEMO-01",
        sqlite_store=store,
    )

    assert finalized.final_status == DecisionStatus.APPROVED
    assert updated_audit.operator_action is not None
    assert updated_audit.operator_action["final_status"] == "APPROVED"

    with sqlite3.connect(db_path) as connection:
        finalization = connection.execute(
            "SELECT final_status, operator_action_json FROM decision_finalizations WHERE decision_id = ?",
            ("DEC-001",),
        ).fetchone()
        action = connection.execute(
            "SELECT action_type, actor_id FROM operator_actions WHERE decision_id = ?",
            ("DEC-001",),
        ).fetchone()
        audit_json = connection.execute(
            "SELECT audit_json FROM audit_records WHERE decision_id = ?",
            ("DEC-001",),
        ).fetchone()[0]

    assert finalization[0] == "APPROVED"
    assert json.loads(finalization[1])["reason"] == "Supervisor approved the preview."
    assert action == ("approve", "OP-DEMO-01")
    assert json.loads(audit_json)["operator_action"]["final_status"] == "APPROVED"


def test_finalize_override_uses_hard_constraint_validation() -> None:
    with pytest.raises(PequiFluxError, match="HC_07_OVERRIDE"):
        finalize_operator_decision(
            payload=_payload(),
            action_type=OperatorAction.OVERRIDE,
            reason="Try blocked open destination.",
            actor_id="OP-DEMO-01",
            requested_truck_id="TRK-003",
            requested_destination_id="DST-OPEN-01",
        )


def test_finalize_override_allows_eligible_pair() -> None:
    finalized, updated_audit = finalize_operator_decision(
        payload=_payload(),
        action_type=OperatorAction.OVERRIDE,
        reason="Supervisor selected another eligible pair.",
        actor_id="OP-DEMO-01",
        requested_truck_id="TRK-002",
        requested_destination_id="DST-COV-01",
    )

    assert finalized.final_status == DecisionStatus.OVERRIDDEN
    assert updated_audit.operator_action["requested_truck_id"] == "TRK-002"
