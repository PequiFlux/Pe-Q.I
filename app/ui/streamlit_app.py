from __future__ import annotations

import csv
import json
import os
from contextlib import nullcontext
from typing import Any

import streamlit as st

from app.domain.models import DecisionRequest, FrontEndPayload
from app.ui.components.audit_panel import (
    copilot_timeline_card,
    render_audit,
    render_driver_message,
    render_gemma_context,
    render_input_evidence,
    render_operator_action,
    render_status_bar,
    tool_badges_card,
)
from app.ui.components.common import LANGUAGE_KEY, copy_text, escape, is_english, runtime_label
from app.ui.components.decision_card import (
    blocked_constraints_card,
    gemma_extraction_card,
    queue_stack_card,
    recommended_decision_card,
)
from app.ui.components.validation_matrix import render_validation_matrix
from app.ui.scenario_loader import (
    build_request_from_inputs,
    load_case_defaults,
    load_manifest,
)
from app.ui.styles import inject_styles
from app.ui.ui_runner import run_payload

EXAMPLE_SCENARIO_ID = "S10_FIFO_BREAK_JUSTIFIED"
INPUT_KEYS = {
    "queue_csv": "yard_queue_csv",
    "ticket_text": "yard_ticket_text",
    "operator_note": "yard_operator_note",
    "weather_json": "yard_weather_json",
    "resource_json": "yard_resource_json",
    "queue_upload": "yard_queue_upload",
    "ticket_upload": "yard_ticket_upload",
    "upload_generation": "yard_upload_generation",
    "weather_mode": "yard_weather_mode",
    "resource_mode": "yard_resource_mode",
    "weather_precipitation": "yard_weather_precipitation",
    "weather_severity": "yard_weather_severity",
    "resource_available": "yard_resource_available",
    "resource_blocked": "yard_resource_blocked",
    "resource_wet": "yard_resource_wet",
    "analyze_example": "yard_analyze_example",
}


def main() -> None:
    st.set_page_config(page_title="PequiFlux Yard Copilot", layout="wide")
    inject_styles()

    manifest = load_manifest()
    case_by_id = {case["scenario_id"]: case for case in manifest["cases"]}
    example_case = case_by_id[EXAMPLE_SCENARIO_ID]

    with st.sidebar:
        st.markdown(_brand_block(), unsafe_allow_html=True)
        _render_language_selector()
        st.markdown(_sidebar_runtime_block(), unsafe_allow_html=True)

    _render_intro()
    _ensure_input_state()
    if payload := st.session_state.get("last_payload"):
        request = st.session_state.get("last_request")
    elif _ui_autorun_enabled():
        _load_example_into_state(example_case)
        st.session_state["active_case"] = EXAMPLE_SCENARIO_ID
        request, error = build_request_from_inputs(
            {**_state_defaults(), "uploaded_ticket": None},
            EXAMPLE_SCENARIO_ID,
            "full",
        )
        if error:
            _render_error(error)
            return
        assert request is not None
        payload = run_payload(request)
        st.session_state["last_payload"] = payload
        st.session_state["last_request"] = request
    else:
        payload = None
        request = None

    active_case_id = st.session_state.get("active_case", "UI_INTERACTIVE")
    inputs = _render_operator_input(
        example_case=example_case,
        expanded=True,
        use_expander=False,
    )

    if inputs["submitted"]:
        scenario_id = active_case_id if active_case_id in case_by_id else "UI_INTERACTIVE"
        request, error = build_request_from_inputs(inputs, scenario_id, "full")
        if error:
            _render_error(error)
            return
        assert request is not None
        payload = run_payload(request)
        st.session_state["last_payload"] = payload
        st.session_state["last_request"] = request

    if payload is None or request is None:
        _render_empty_state()
        return

    case = case_by_id.get(request.scenario_id, {"scenario_id": request.scenario_id})
    _render_outputs(payload, request, case)


def _render_intro() -> None:
    if _is_english():
        title = "New yard decision"
        summary = (
            "Send queue, document, note, weather, and resources. The system interprets "
            "the ticket, applies operational constraints, and returns an auditable "
            "decision for human approval."
        )
        proof = [
            ("Document", "interpreted"),
            ("Rules", "checked"),
            ("Operator", "approves or blocks"),
        ]
    else:
        title = "Nova decisão de pátio"
        summary = (
            "Envie fila, documento, nota, clima e recursos. O sistema interpreta o "
            "ticket, aplica restrições operacionais e devolve uma decisão auditável "
            "para aprovação humana."
        )
        proof = [
            ("Documento", "interpretado"),
            ("Regras", "conferidas"),
            ("Operador", "aprova ou bloqueia"),
        ]
    st.markdown(
        f"""
        <section class="hero">
          <div>
            <span class="eyebrow">PequiFlux Yard Copilot</span>
            <h1>{escape(title)}</h1>
            <p>{escape(summary)}</p>
          </div>
          <div class="hero-proof">
            <div><strong>{escape(proof[0][0])}</strong><span>{escape(proof[0][1])}</span></div>
            <div><strong>{escape(proof[1][0])}</strong><span>{escape(proof[1][1])}</span></div>
            <div><strong>{escape(proof[2][0])}</strong><span>{escape(proof[2][1])}</span></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_empty_state() -> None:
    if _is_english():
        title = "Fill in the fields or click Load example."
        summary = (
            f"Then use {escape(_analyze_button_label())} to generate status, truck, "
            "destination, operational reason, interpreted document, critical "
            "constraints, driver message, and human action."
        )
    else:
        title = "Preencha os campos ou clique em Carregar exemplo."
        summary = (
            f"Depois, use {escape(_analyze_button_label())} para gerar status, caminhão, "
            "destino, motivo operacional, documento interpretado, restrições críticas, "
            "mensagem ao motorista e ação humana."
        )
    st.markdown(
        f"""
        <article class="empty-state">
          <strong>{escape(title)}</strong>
          <p>{summary}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _render_operator_input(
    *,
    example_case: dict[str, Any],
    expanded: bool,
    use_expander: bool = True,
) -> dict[str, Any]:
    wrapper = (
        st.expander(_copy("Operational input", "Entrada operacional"), expanded=expanded)
        if use_expander
        else nullcontext()
    )
    with wrapper:
        section_title = _copy("Operational input", "Entrada operacional")
        section_note = _copy(
            "Load the queue, ticket, note, and operational context before analysis.",
            "Carregue a fila, o ticket, a nota e o contexto operacional antes da análise.",
        )
        st.markdown(
            f"""
            <div class="section-title compact-title">
              <div><h2>{escape(section_title)}</h2><p>{escape(section_note)}</p></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        submitted = bool(st.session_state.pop(INPUT_KEYS["analyze_example"], False))
        with st.container():
            _render_input_actions(example_case)
            top_a, top_b = st.columns([1.08, 0.92], gap="large")
            with top_a:
                st.markdown(
                    f'<div class="panel-title">1 · {escape(_copy("Truck queue", "Fila de caminhões"))}</div>',
                    unsafe_allow_html=True,
                )
                uploaded_queue = st.file_uploader(
                    _copy("Queue CSV: upload", "Fila CSV: upload"),
                    type=["csv"],
                    key=_upload_key("queue_upload"),
                    help=_copy(
                        "Minimum columns: truck_id, arrival_ts. Optional fields: status, vehicle_type, contract_priority_flag.",
                        "Colunas mínimas: truck_id, arrival_ts. Campos opcionais: status, vehicle_type, contract_priority_flag.",
                    ),
                )
                queue_csv = _queue_csv_value(uploaded_queue)
                st.markdown(_queue_source_note(uploaded_queue, queue_csv), unsafe_allow_html=True)
                st.markdown(_queue_preview(queue_csv), unsafe_allow_html=True)

            with top_b:
                st.markdown(
                    f'<div class="panel-title">2 · {escape(_copy("Ticket or document", "Ticket ou documento"))}</div>',
                    unsafe_allow_html=True,
                )
                uploaded_ticket = st.file_uploader(
                    _copy("Ticket/document: upload", "Ticket/documento: upload"),
                    type=["txt", "pdf", "png", "jpg", "jpeg"],
                    key=_upload_key("ticket_upload"),
                    help=_copy(
                        "TXT works in test mode. With PEQUIFLUX_GEMMA_RUNTIME=ollama, images are sent to the local document reader.",
                        "TXT funciona em modo teste. Com PEQUIFLUX_GEMMA_RUNTIME=ollama, imagens são enviadas ao leitor local de documento.",
                    ),
                )
                ticket_text = _ticket_text_value(uploaded_ticket)
                st.markdown(
                    _ticket_source_note(uploaded_ticket, ticket_text), unsafe_allow_html=True
                )

            mid_a, mid_b, mid_c = st.columns([1, 1, 1], gap="large")
            with mid_a:
                operator_note = _render_operator_note_input()
            with mid_b:
                st.markdown(
                    f'<div class="panel-title">4 · {escape(_copy("Weather", "Clima"))}</div>',
                    unsafe_allow_html=True,
                )
                weather_json = _render_weather_input()
            with mid_c:
                st.markdown(
                    f'<div class="panel-title">5 · {escape(_copy("Resources", "Recursos"))}</div>',
                    unsafe_allow_html=True,
                )
                resource_json = _render_resource_input()

            run_note = _copy(
                "Execution writes temporary files to cache/ui_sessions inside the container.",
                "A execução grava arquivos temporários em cache/ui_sessions dentro do container.",
            )
            st.markdown(
                f"""
                <div class="run-strip">
                  <div><strong>Runtime:</strong> {escape(runtime_label())}</div>
                  <div class="run-note">{escape(run_note)}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            submitted = (
                st.button(_analyze_button_label(), type="primary", width="stretch") or submitted
            )

    return {
        "submitted": submitted,
        "queue_csv": queue_csv,
        "uploaded_ticket": uploaded_ticket,
        "ticket_text": ticket_text,
        "operator_note": operator_note,
        "weather_json": weather_json,
        "resource_json": resource_json,
    }


def _render_operator_note_input() -> str:
    st.markdown(
        f'<div class="panel-title">3 · {escape(_copy("Operator note", "Nota do operador"))}</div>',
        unsafe_allow_html=True,
    )
    return st.text_area(
        _copy("Operator note", "Nota do operador"),
        height=140,
        key=INPUT_KEYS["operator_note"],
    )


def _render_weather_input() -> str:
    mode = st.radio(
        _copy("Weather", "Clima"),
        ["formulário", "JSON"],
        format_func=lambda value: _copy("form", "formulário") if value == "formulário" else value,
        horizontal=True,
        key=INPUT_KEYS["weather_mode"],
    )
    if mode == "JSON":
        return st.text_area(
            _copy("Weather JSON", "Clima JSON"),
            height=140,
            key=INPUT_KEYS["weather_json"],
        )
    precipitation = st.selectbox(
        _copy("Precipitation", "Precipitação"),
        ["none", "rain"],
        key=INPUT_KEYS["weather_precipitation"],
    )
    severity = st.selectbox(
        _copy("Severity", "Severidade"),
        ["none", "low", "medium", "high"],
        key=INPUT_KEYS["weather_severity"],
    )
    return json.dumps({"precipitation": precipitation, "severity": severity})


def _render_resource_input() -> str:
    mode = st.radio(
        _copy("Resources", "Recursos"),
        ["formulário", "JSON"],
        format_func=lambda value: _copy("form", "formulário") if value == "formulário" else value,
        horizontal=True,
        key=INPUT_KEYS["resource_mode"],
    )
    if mode == "JSON":
        return st.text_area(
            _copy("Resources JSON", "Recursos JSON"),
            height=140,
            key=INPUT_KEYS["resource_json"],
        )
    available = st.text_input(
        _copy("Available destinations", "Destinos disponíveis"),
        key=INPUT_KEYS["resource_available"],
        help=_copy(
            "Separate IDs with commas. Example: DST-COV-01, DST-COV-02",
            "Separe IDs por vírgula. Ex.: DST-COV-01, DST-COV-02",
        ),
    )
    blocked = st.text_input(
        _copy("Blocked destinations", "Destinos bloqueados"),
        key=INPUT_KEYS["resource_blocked"],
        help=_copy(
            "Separate IDs with commas. Example: DST-OPEN-01",
            "Separe IDs por vírgula. Ex.: DST-OPEN-01",
        ),
    )
    wet_destinations = st.text_input(
        _copy("Wet-load compatible destinations", "Destinos compatíveis com carga úmida"),
        key=INPUT_KEYS["resource_wet"],
        help=_copy(
            "Separate IDs with commas. These destinations accept dry and wet loads.",
            "Separe IDs por vírgula. Esses destinos aceitam dry e wet.",
        ),
    )
    wet_ids = set(_split_ids(wet_destinations))
    available_ids = list(dict.fromkeys([*_split_ids(available), *wet_ids]))
    resources = [
        {
            "resource_id": item,
            "status": "available",
            "capacity_pct": 85,
            "resource_type": "covered_hopper",
            "exposure": "covered",
            "allowed_vehicle_types": ["truck", "bitrem"],
            "supported_load_conditions": ["dry", "wet"] if item in wet_ids else ["dry"],
        }
        for item in available_ids
    ]
    resources.extend(
        {
            "resource_id": item,
            "status": "blocked",
            "capacity_pct": 100,
            "resource_type": "open_hopper",
            "exposure": "open",
            "allowed_vehicle_types": ["truck", "bitrem"],
            "supported_load_conditions": ["dry"],
        }
        for item in _split_ids(blocked)
    )
    return json.dumps(resources)


def _queue_csv_value(uploaded_queue: Any) -> str:
    if uploaded_queue is None:
        return st.session_state.get(INPUT_KEYS["queue_csv"], "")
    try:
        return uploaded_queue.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        return ""


def _ticket_text_value(uploaded_ticket: Any) -> str:
    if uploaded_ticket is None:
        return st.session_state.get(INPUT_KEYS["ticket_text"], "")
    if not uploaded_ticket.name.lower().endswith(".txt"):
        return ""
    try:
        return uploaded_ticket.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        return ""


def _queue_source_note(uploaded_queue: Any, queue_csv: str) -> str:
    if uploaded_queue is not None:
        source = _copy(
            f"Uploaded file: {uploaded_queue.name}", f"Arquivo carregado: {uploaded_queue.name}"
        )
    elif queue_csv:
        source = _copy(
            "Example loaded as fixture CSV.",
            "Exemplo carregado como CSV de fixture.",
        )
    else:
        source = _copy("No queue loaded.", "Nenhuma fila carregada.")
    return f'<div class="source-note">{escape(source)}</div>'


def _ticket_source_note(uploaded_ticket: Any, ticket_text: str) -> str:
    if uploaded_ticket is not None:
        source = _copy(
            f"Uploaded file: {uploaded_ticket.name}", f"Arquivo carregado: {uploaded_ticket.name}"
        )
    elif ticket_text:
        source = _copy(
            "Example loaded as fixture TXT ticket.",
            "Exemplo carregado como ticket TXT de fixture.",
        )
    else:
        source = _copy("No ticket loaded.", "Nenhum ticket carregado.")
    return f'<div class="source-note">{escape(source)}</div>'


def _split_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _render_input_actions(example_case: dict[str, Any]) -> None:
    left, middle, right = st.columns([0.18, 0.22, 0.18], gap="small")
    with left:
        if st.button(_copy("Load example", "Carregar exemplo"), width="stretch"):
            _load_example_into_state(example_case)
            st.session_state["active_case"] = EXAMPLE_SCENARIO_ID
            st.rerun()
    with middle:
        if st.button(
            _copy("Load and analyze example", "Carregar e analisar exemplo"), width="stretch"
        ):
            _load_example_into_state(example_case)
            st.session_state["active_case"] = EXAMPLE_SCENARIO_ID
            st.session_state[INPUT_KEYS["analyze_example"]] = True
            st.rerun()
    with right:
        if st.button(_copy("Clear fields", "Limpar campos"), width="stretch"):
            _clear_input_state()
            st.rerun()


def _render_outputs(
    payload: FrontEndPayload,
    request: DecisionRequest,
    case: dict[str, Any],
) -> None:
    title = _copy("2. Analysis result", "2. Resultado da análise")
    note = _copy(
        "Operational status, recommendation, document evidence, and critical constraints.",
        "Status operacional, recomendação, evidências do documento e restrições críticas.",
    )
    chip_text = _copy("auditable decision", "decisão auditável")
    st.markdown(
        f"""
        <div class="section-title">
          <div><h2>{escape(title)}</h2><p>{escape(note)}</p></div>
          <span class="chip success">{escape(chip_text)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_status_bar(payload)
    st.markdown(recommended_decision_card(payload), unsafe_allow_html=True)
    st.markdown(queue_stack_card(payload, request), unsafe_allow_html=True)
    first_left, first_right = st.columns([1, 1], gap="large")
    with first_left:
        st.markdown(gemma_extraction_card(payload, request), unsafe_allow_html=True)
    with first_right:
        st.markdown(blocked_constraints_card(payload), unsafe_allow_html=True)

    second_left, second_right = st.columns([1, 1], gap="large")
    with second_left:
        render_driver_message(payload)
    with second_right:
        render_operator_action(payload)

    _render_technical_audit_expander(payload, request, case)


def _render_technical_audit_expander(
    payload: FrontEndPayload,
    request: DecisionRequest,
    case: dict[str, Any],
) -> None:
    with st.expander(
        _copy("View technical audit", "Ver auditoria técnica"), expanded=_ui_autorun_enabled()
    ):
        render_input_evidence(payload, request, case)
        st.markdown(copilot_timeline_card(payload, request), unsafe_allow_html=True)
        left, right = st.columns([1.15, 0.85], gap="large")
        with left:
            render_validation_matrix(payload)
        with right:
            render_gemma_context(payload, request)
            st.markdown(tool_badges_card(payload), unsafe_allow_html=True)
        render_audit(payload)
        st.json(payload.model_dump(mode="json"))


def _render_error(error: str) -> None:
    title = _copy("Invalid input", "Entrada inválida")
    st.markdown(
        f"""
        <article class="error-card">
          <strong>{escape(title)}</strong>
          <p>{escape(error)}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _queue_preview(queue_csv: str) -> str:
    try:
        rows = list(csv.DictReader(queue_csv.splitlines()))
    except csv.Error:
        rows = []
    waiting = sum(1 for row in rows if (row.get("status") or "waiting").lower() == "waiting")
    priority = sum(1 for row in rows if (row.get("contract_priority_flag") or "").lower() == "true")
    rows_label = _copy("rows", "linhas")
    waiting_label = _copy("waiting", "aguardando")
    priority_label = _copy("priority", "prioridade")
    return f"""
    <div class="input-summary">
      <div><strong>{len(rows)}</strong><span>{escape(rows_label)}</span></div>
      <div><strong>{waiting}</strong><span>{escape(waiting_label)}</span></div>
      <div><strong>{priority}</strong><span>{escape(priority_label)}</span></div>
    </div>
    """


def _brand_block() -> str:
    subtitle = _copy("Yard Copilot · Operations", "Yard Copilot · Operação")
    return """
    <div class="brand">
      <div class="brand-mark"></div>
      <div>
        <h1>PequiFlux</h1>
        <p>{subtitle}</p>
      </div>
    </div>
    """.format(
        subtitle=escape(subtitle)
    )


def _render_language_selector() -> None:
    options = ["Português", "English"]
    st.radio(
        "Idioma / Language",
        options,
        index=options.index(st.session_state.get(LANGUAGE_KEY, "Português")),
        key=LANGUAGE_KEY,
        horizontal=True,
    )
    description = _copy(
        "English UI copy is enabled. The technical payload, scenario IDs, and audit JSON remain canonical.",
        "Interface em português ativada. Payload técnico, IDs de cenário e JSON de auditoria permanecem canônicos.",
    )
    st.markdown(f'<div class="source-note">{escape(description)}</div>', unsafe_allow_html=True)


def _sidebar_runtime_block() -> str:
    title = _copy("Execution", "Execução")
    note = _copy(
        "No operational fallback. If material truth is missing, the flow closes as BLOCKED or REVIEW_REQUIRED.",
        "Sem fallback operacional. Se faltar verdade material, o fluxo fecha em BLOCKED ou REVIEW_REQUIRED.",
    )
    return f"""
    <div class="side-card compact">
      <div class="side-kicker">{escape(title)}</div>
      <p>{escape(runtime_label())}</p>
      <p>{escape(_runtime_mode_note())}</p>
      <p>{escape(note)}</p>
    </div>
    """


def _runtime_mode_note() -> str:
    runtime = os.getenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama")
    if runtime == "text":
        return _copy(
            "Test mode: no Gemma/Ollama; use TXT or Load example.",
            "Modo teste: sem Gemma/Ollama; use TXT ou Carregar exemplo.",
        )
    if runtime == "ollama":
        return _copy("Gemma 4 active through Ollama.", "Gemma 4 ativo via Ollama.")
    return _copy(f"Custom runtime: {runtime}.", f"Runtime customizado: {runtime}.")


def _analyze_button_label() -> str:
    if os.getenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama") == "text":
        return _copy("Analyze in test mode", "Analisar em modo teste")
    return _copy("Analyze with Gemma 4", "Analisar com Gemma 4")


def _is_english() -> bool:
    return is_english()


def _copy(english: str, portuguese: str) -> str:
    return copy_text(english, portuguese)


def _empty_defaults() -> dict[str, Any]:
    return {
        "queue_csv": "",
        "ticket_text": "",
        "operator_note": "",
        "weather_json": '{\n  "precipitation": "none",\n  "severity": "none"\n}',
        "resource_json": "[]",
        "weather_mode": "JSON",
        "resource_mode": "JSON",
        "weather_precipitation": "none",
        "weather_severity": "none",
        "resource_available": "",
        "resource_blocked": "",
        "resource_wet": "",
        "upload_generation": 0,
    }


def _ensure_input_state() -> None:
    defaults = _empty_defaults()
    for field, value in defaults.items():
        key = INPUT_KEYS[field]
        if key in {INPUT_KEYS["queue_upload"], INPUT_KEYS["ticket_upload"]}:
            continue
        st.session_state.setdefault(key, value)


def _clear_input_state() -> None:
    for key in list(st.session_state.keys()):
        if key in INPUT_KEYS.values() or _is_upload_widget_key(key):
            st.session_state.pop(key, None)
    st.session_state.pop("active_case", None)
    st.session_state.pop("last_payload", None)
    st.session_state.pop("last_request", None)
    defaults = _empty_defaults()
    for field, value in defaults.items():
        key = INPUT_KEYS[field]
        st.session_state.setdefault(key, value)


def _state_defaults() -> dict[str, str]:
    _ensure_input_state()
    return {
        field: st.session_state[INPUT_KEYS[field]]
        for field in ("queue_csv", "ticket_text", "operator_note", "weather_json", "resource_json")
    }


def _load_example_into_state(case: dict[str, Any]) -> None:
    _reset_uploaders()
    defaults = load_case_defaults(case)
    for field in ("queue_csv", "ticket_text", "operator_note", "weather_json", "resource_json"):
        st.session_state[INPUT_KEYS[field]] = defaults[field]
    st.session_state[INPUT_KEYS["weather_mode"]] = "JSON"
    st.session_state[INPUT_KEYS["resource_mode"]] = "JSON"
    st.session_state.pop("last_payload", None)
    st.session_state.pop("last_request", None)


def _upload_key(field: str) -> str:
    generation = st.session_state.get(INPUT_KEYS["upload_generation"], 0)
    return f"{INPUT_KEYS[field]}_{generation}"


def _reset_uploaders() -> None:
    generation = int(st.session_state.get(INPUT_KEYS["upload_generation"], 0)) + 1
    for key in list(st.session_state.keys()):
        if _is_upload_widget_key(key):
            st.session_state.pop(key, None)
    st.session_state[INPUT_KEYS["upload_generation"]] = generation


def _is_upload_widget_key(key: str) -> bool:
    return key.startswith(f"{INPUT_KEYS['queue_upload']}_") or key.startswith(
        f"{INPUT_KEYS['ticket_upload']}_"
    )


def _ui_autorun_enabled() -> bool:
    return os.getenv("PEQUIFLUX_UI_AUTORUN", "").strip().lower() in {"1", "true", "yes"}


if __name__ == "__main__":
    main()
