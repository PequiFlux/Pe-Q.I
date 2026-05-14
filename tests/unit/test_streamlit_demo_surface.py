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
                "parse_ticket_document": 1461,
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
                    },
                    {
                        "truck_id": "TRK-011",
                        "destination_id": "DST-COV-01",
                        "eligible": True,
                        "failed_constraints": [],
                    },
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
                    "parse_ticket_document": 1461,
                    "validate_hard_constraints": 7,
                    "rank_candidates": 5,
                    "generate_audit_payload": 3,
                },
                "tool_calls": [
                    {
                        "tool_name": "validate_hard_constraints",
                        "request_id": "REQ-UI-001",
                        "state": "constraints_ready",
                        "status": "executed",
                        "purpose": "Check hard constraints",
                    },
                    {
                        "tool_name": "rank_candidates",
                        "request_id": "REQ-UI-001",
                        "state": "ranking_ready",
                        "status": "executed",
                        "purpose": "Rank candidate trucks",
                    },
                    {
                        "tool_name": "generate_audit_payload",
                        "request_id": "REQ-UI-001",
                        "state": "audit_ready",
                        "status": "executed",
                        "purpose": "Build audit payload",
                    },
                ],
                "source_hashes": {"queue_csv_ref": "queue.csv", "ticket_ref": "ticket.txt"},
            },
        }
    )


def test_demo_script_button_labels_match_streamlit_surface(monkeypatch) -> None:
    source = (ROOT / "app/ui/streamlit_app.py").read_text(encoding="utf-8")
    translations = (ROOT / "app/ui/i18n.py").read_text(encoding="utf-8")
    surface = source + translations

    for label in [
        "Resultado da análise",
        "Entrada operacional",
        "Carregar exemplo",
        "Carregar e analisar exemplo",
        "Limpar campos",
        "Nova análise",
        "Ver auditoria técnica",
        "Prova Gemma 4",
        "Gemma 4 executando no fluxo real",
        "Tools executadas",
        "Modo teste ativo",
        "Disponível após carregar a fila de caminhões.",
        "Defina destinos disponíveis e restrições do turno.",
    ]:
        assert label in surface

    assert "Carregar caso" not in surface
    assert "Carregar e analisar caso" not in surface
    assert "1. Entrada operacional" not in surface
    assert "2. Resultado da análise" not in surface
    assert "3. Ação do operador" not in surface
    assert "4. Quais restrições" not in surface
    assert "Disponivel apos" not in surface
    assert "restricoes do turno" not in surface
    assert 'initial_sidebar_state="collapsed"' in source
    assert '<div class="yc-hero-title">' in source
    assert 'st.button(t("button.load_analyze", lang), type="primary", width="stretch")' in source
    assert "has_result = payload is not None and request is not None" in source
    assert "_render_result_navigation(lang)" in source
    assert "clear_input_state(INPUT_KEYS)" in source
    assert "use_expander=has_result" in source
    assert "expanded=not has_result" in source
    assert "st.rerun()" in source
    assert "expanded=False" in source
    assert "expanded=ui_autorun_enabled()" not in source

    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", "text")
    assert streamlit_app._analyze_button_label() == "Analisar em modo teste"
    assert "exemplo versionado" in streamlit_app._runtime_mode_note("pt")

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


def test_gemma_proof_card_surfaces_real_runtime_evidence(monkeypatch) -> None:
    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama")
    monkeypatch.setenv("GEMMA_MODEL", "gemma4:e2b")

    html = streamlit_app._gemma_proof_card(_preview_payload(), "pt")

    assert "Prova Gemma 4 para a banca" in html
    assert "Gemma 4 executando no fluxo real" in html
    assert "Ollama · gemma4:e2b" in html
    assert "1461 ms" in html
    assert "3 executadas" in html
    assert "validate_hard_constraints -&gt; rank_candidates -&gt; generate_audit_payload" in html
    assert "Fail closed" in html


def test_gemma_proof_card_warns_when_test_runtime_is_active(monkeypatch) -> None:
    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", "text")

    html = streamlit_app._gemma_proof_card(_preview_payload(), "pt")

    assert "Modo teste ativo" in html
    assert "Não use modo teste para a gravação da banca." in html


def test_validation_heatmap_uses_accented_portuguese_label() -> None:
    heatmap_html = _validation_heatmap(_preview_payload())

    assert "elegível" in heatmap_html
    assert "elegivel" not in heatmap_html


def test_demo_css_is_loaded_and_allows_wrapped_buttons_and_mobile_layout() -> None:
    loader_source = (ROOT / "app/ui/styles.py").read_text(encoding="utf-8")
    demo_css = (ROOT / "app/ui/styles.demo.css").read_text(encoding="utf-8")

    assert "styles.demo.css" in loader_source
    assert "white-space: normal" in demo_css
    assert "min-height: 44px" in demo_css
    assert "@media (max-width: 640px)" in demo_css
    assert ".yc-action-row," in demo_css
    assert ".queue-card.promoted" in demo_css


def test_demo_css_hides_streamlit_page_nav_and_styles_sidebar_language() -> None:
    base_css = (ROOT / "app/ui/styles.base.css").read_text(encoding="utf-8")

    assert 'div[data-testid="stSidebarNav"]' in base_css
    assert '[data-testid="stPageLink"]' in base_css
    assert 'section[data-testid="stSidebar"] div[data-testid="stRadio"]' in base_css
    assert "yc-bancada-kicker" in base_css
    assert "demo-proof" in base_css
    assert "grid-template-columns: 1fr;" in base_css
    assert "max-width: 1040px" in base_css
    assert "max-width: 100%;" in base_css


def test_preparation_panel_uses_human_case_title_and_keeps_canonical_id() -> None:
    html = streamlit_app._preparation_panel(
        {
            "scenario_id": "S10_FIFO_BREAK_JUSTIFIED",
            "description": "Primary narrative scenario.",
        },
        "pt",
    )

    assert "S10_FIFO_BREAK_JUSTIFIED" in html
    assert "S10 · fifo break justified" in html
    assert "yc-bancada-kicker" in html


def test_case_selector_accepts_canonical_id_and_display_label() -> None:
    cases = [
        {
            "scenario_id": "S10_FIFO_BREAK_JUSTIFIED",
            "description": "Primary narrative scenario.",
        }
    ]
    label = streamlit_app.scenario_label(cases[0])

    assert streamlit_app._resolve_case_id("S10_FIFO_BREAK_JUSTIFIED", cases) == (
        "S10_FIFO_BREAK_JUSTIFIED"
    )
    assert streamlit_app._resolve_case_id(label, cases) == "S10_FIFO_BREAK_JUSTIFIED"
    assert streamlit_app._format_case_option(cases, label) == label
    assert streamlit_app._format_case_option(cases, "UNKNOWN") == "UNKNOWN"
