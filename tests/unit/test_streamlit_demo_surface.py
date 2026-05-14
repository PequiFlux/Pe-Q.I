from __future__ import annotations

from pathlib import Path

from app.domain.models import FrontEndPayload
from app.ui import streamlit_app
from app.ui.components.audit_panel import copilot_timeline_card, tool_badges_card
from app.ui.components.common import audit_status_label, display_status, reason_detail_label
from app.ui.components.decision_card import recommended_decision_card
from app.ui.components.validation_matrix import _validation_heatmap


ROOT = Path(__file__).resolve().parents[2]


def _preview_payload() -> FrontEndPayload:
    return FrontEndPayload.model_validate(
        {
            "request_id": "REQ-UI-001",
            "scenario_id": "S10_FIFO_BREAK_JUSTIFIED",
            "variant": "full",
            "decision_status": "PREVIEW_READY",
            "recommended_truck": {
                "truck_id": "TRK-010",
                "queue_position_before": 3,
                "queue_position_after": 1,
            },
            "recommended_destination": {
                "destination_id": "DST-COV-01",
                "destination_type": "resource",
            },
            "reason_summary": "FIFO break justified by Long wait time increased ranking priority.",
            "reason_details": [
                "FIFO ordering preserved when possible.",
                "Long wait time increased ranking priority.",
            ],
            "driver_message": {
                "message": "TRK-010, dirija-se ao destino DST-COV-01.",
                "template_id": "preview_ptbr_v1",
            },
            "operator_actions": ["approve", "block", "override"],
            "queue_diff": [
                {
                    "truck_id": "TRK-010",
                    "position_before": 3,
                    "position_after": None,
                    "decision": "called",
                    "reason": "FIFO break justified by Long wait time increased ranking priority.",
                },
                {
                    "truck_id": "TRK-011",
                    "position_before": 4,
                    "position_after": 3,
                    "decision": "shifted",
                    "reason": "shifted_after_called_truck_left_queue",
                },
            ],
            "gemma_visible_summary": {
                "parsed_fields": ["ticket_id", "truck_id", "load_condition"],
                "exception_label": "WET_LOAD",
                "notes": [],
            },
            "latency_ms": {
                "validate_hard_constraints": 7,
                "rank_candidates": 5,
                "generate_audit_payload": 3,
            },
            "benchmark_tags": [],
            "benchmark_observed": {
                "parsed_ticket": {
                    "ticket_id": "TCK-S10-005",
                    "truck_id": "TRK-010",
                    "load_condition": "wet",
                    "destination_constraints": ["DST-COV-01"],
                }
            },
            "confidence_notes": ["parse_confidence=0.96"],
            "audit_record": {
                "decision_id": "DEC-UI-001",
                "request_id": "REQ-UI-001",
                "scenario_id": "S10_FIFO_BREAK_JUSTIFIED",
                "variant": "full",
                "hard_constraints_checked": [
                    {
                        "truck_id": "TRK-010",
                        "destination_id": "DST-COV-01",
                        "eligible": True,
                        "failed_constraints": [],
                    }
                ],
                "fired_rules": ["PR-04_WAIT_SLA_PRESSURE"],
                "rejected_candidates": [],
                "recommended_pair": {
                    "truck_id": "TRK-010",
                    "destination_id": "DST-COV-01",
                },
                "fifo_break": True,
                "provenance": [],
                "latencies_ms": {
                    "validate_hard_constraints": 7,
                    "rank_candidates": 5,
                    "generate_audit_payload": 3,
                },
                "source_hashes": {"queue_csv_ref": "queue.csv", "ticket_ref": "ticket.txt"},
            },
        }
    )


def test_demo_script_button_labels_match_streamlit_surface(monkeypatch) -> None:
    source = (ROOT / "app/ui/streamlit_app.py").read_text(encoding="utf-8")
    translations = (ROOT / "app/ui/i18n.py").read_text(encoding="utf-8")
    surface = source + translations

    for label in [
        "Entrada operacional",
        "Carregar exemplo",
        "Carregar e analisar exemplo",
        "Limpar campos",
        "Ver auditoria técnica",
    ]:
        assert label in surface

    assert "Carregar caso" not in surface
    assert "Carregar e analisar caso" not in surface

    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", "text")
    assert streamlit_app._analyze_button_label() == "Analisar em modo teste"
    assert "exemplo versionado" in streamlit_app._runtime_mode_note()

    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama")
    assert streamlit_app._analyze_button_label() == "Analisar com Gemma 4"


def test_status_and_reason_labels_are_localized_for_operator_surface() -> None:
    assert display_status("PREVIEW_READY") == "prévia pronta"
    assert display_status("REVIEW_REQUIRED") == "revisão obrigatória"
    assert audit_status_label("skipped") == "IGNORADO"
    assert reason_detail_label("shifted_after_called_truck_left_queue") == (
        "avançou após saída do caminhão chamado"
    )


def test_primary_result_and_technical_cards_hide_raw_internal_status_labels() -> None:
    payload = _preview_payload()

    decision_html = recommended_decision_card(payload)
    timeline_html = copilot_timeline_card(payload, object())
    tools_html = tool_badges_card(payload)

    assert "prévia pronta" in decision_html
    assert "Quebra de FIFO justificada" in decision_html
    assert "PREVIEW_READY" not in decision_html
    assert "Long wait time" not in decision_html

    assert "pronto" in timeline_html
    assert ">ready<" not in timeline_html
    assert "ignorado" in tools_html
    assert ">skipped<" not in tools_html


def test_validation_heatmap_uses_accented_portuguese_label() -> None:
    heatmap_html = _validation_heatmap(_preview_payload())

    assert "elegível" in heatmap_html
    assert "elegivel" not in heatmap_html


def test_demo_css_is_loaded_and_allows_wrapped_buttons() -> None:
    loader_source = (ROOT / "app/ui/styles.py").read_text(encoding="utf-8")
    demo_css = (ROOT / "app/ui/styles.demo.css").read_text(encoding="utf-8")

    assert "styles.demo.css" in loader_source
    assert "white-space: normal" in demo_css
    assert "min-height: 44px" in demo_css
