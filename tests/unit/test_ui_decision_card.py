from __future__ import annotations

from app.domain.models import FrontEndPayload
from app.ui.components.audit_panel import tool_badges_card
from app.ui.components.decision_card import recommended_decision_card


def _payload(status: str, *, audit_record: dict | None = None) -> FrontEndPayload:
    data = {
        "request_id": "REQ-UI-CARD",
        "scenario_id": "S10_FIFO_BREAK_JUSTIFIED",
        "variant": "full",
        "decision_status": status,
        "recommended_truck": (
            {
                "truck_id": "TRK-005",
                "queue_position_before": 5,
                "queue_position_after": 1,
            }
            if status == "PREVIEW_READY"
            else None
        ),
        "recommended_destination": (
            {
                "destination_id": "DST-COV-01",
                "destination_type": "resource",
            }
            if status == "PREVIEW_READY"
            else None
        ),
        "reason_summary": "Operational reason.",
        "reason_details": ["FIFO ordering preserved when possible."],
        "driver_message": {
            "message": "Driver message.",
            "template_id": "preview_ptbr_v1",
        },
        "operator_actions": ["approve", "block", "override"],
        "queue_diff": [],
        "gemma_visible_summary": {
            "parsed_fields": [],
            "exception_label": "NO_EXCEPTION",
            "notes": [],
        },
        "latency_ms": {},
        "benchmark_tags": [],
        "confidence_notes": [],
        "audit_record": audit_record,
    }
    return FrontEndPayload.model_validate(data)


def test_recommended_decision_card_title_matches_preview_ready() -> None:
    html = recommended_decision_card(_payload("PREVIEW_READY"))

    assert "TRK-005 deve ir para DST-COV-01" in html


def test_recommended_decision_card_title_matches_review_required() -> None:
    html = recommended_decision_card(_payload("REVIEW_REQUIRED"))

    assert "Decisão exige revisão humana" in html
    assert "deve ir para" not in html


def test_recommended_decision_card_title_matches_blocked() -> None:
    html = recommended_decision_card(_payload("BLOCKED"))

    assert "Sem despacho automático seguro" in html
    assert "deve ir para" not in html


def test_tool_badges_card_shows_gemma_requested_tool_sequence() -> None:
    html = tool_badges_card(
        _payload(
            "PREVIEW_READY",
            audit_record={
                "decision_id": "DEC-001",
                "request_id": "REQ-UI-CARD",
                "scenario_id": "S10_FIFO_BREAK_JUSTIFIED",
                "variant": "full",
                "tool_calls": [
                    {
                        "tool_name": "validate_hard_constraints",
                        "request_id": "REQ-UI-CARD",
                        "state": "INTERPRETED",
                        "status": "requested",
                        "purpose": "Deterministic CI tool intent.",
                    },
                    {
                        "tool_name": "validate_hard_constraints",
                        "request_id": "REQ-UI-CARD",
                        "state": "INTERPRETED",
                        "status": "executed",
                        "purpose": "Deterministic CI tool intent.",
                    },
                    {
                        "tool_name": "rank_candidates",
                        "request_id": "REQ-UI-CARD",
                        "state": "VALIDATED",
                        "status": "requested",
                        "purpose": "Ranking may only order eligible pairs.",
                    },
                    {
                        "tool_name": "rank_candidates",
                        "request_id": "REQ-UI-CARD",
                        "state": "VALIDATED",
                        "status": "executed",
                        "purpose": "Ranking may only order eligible pairs.",
                    },
                    {
                        "tool_name": "generate_audit_payload",
                        "request_id": "REQ-UI-CARD",
                        "state": "RANKED",
                        "status": "requested",
                        "purpose": "Audit payload must be generated from formal artifacts.",
                    },
                    {
                        "tool_name": "generate_audit_payload",
                        "request_id": "REQ-UI-CARD",
                        "state": "RANKED",
                        "status": "executed",
                        "purpose": "Audit payload must be generated from formal artifacts.",
                    },
                ],
            },
        )
    )

    assert "Gemma 4 solicitou:" in html
    assert "validate_hard_constraints" in html
    assert "rank_candidates" in html
    assert "generate_audit_payload" in html
    assert "solicitado → executado" in html
    assert "Motivo: Deterministic CI tool intent." in html
    assert "Estado: INTERPRETED" in html
