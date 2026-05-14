from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from app.domain.errors import PequiFluxError
from app.domain.models import DecisionRequest, FrontEndPayload
from app.services.operator_governance import finalize_operator_decision
from app.storage.sqlite_store import SQLiteStore
from app.ui.components.common import (
    audit_status_label,
    chip,
    confidence_value,
    constraints_summary,
    display_status,
    escape,
    mini_metric,
    operator_action_label,
    operator_actions_label,
    ranking_summary,
    runtime_label,
    status_card,
    status_label,
    step_status,
    timeline_item,
    tool_status,
)


def render_input_evidence(
    payload: FrontEndPayload,
    request: DecisionRequest,
    case: dict[str, Any],
) -> None:
    left, right = st.columns([0.92, 1.08], gap="large")
    with left:
        st.markdown(_input_package_card(request, case), unsafe_allow_html=True)
    with right:
        st.markdown(_ticket_preview_card(request), unsafe_allow_html=True)


def render_status_bar(payload: FrontEndPayload) -> None:
    truck = payload.recommended_truck.truck_id if payload.recommended_truck else "-"
    destination = (
        payload.recommended_destination.destination_id if payload.recommended_destination else "-"
    )
    rejected = len(payload.audit_record.rejected_candidates) if payload.audit_record else 0
    latency = sum(payload.latency_ms.values())
    cards = [
        ("Status", display_status(str(payload.decision_status)), "estado final da prévia"),
        ("Caminhão", truck, "próxima chamada"),
        ("Destino", destination, "recurso recomendado"),
        ("Rejeições", str(rejected), "pares inelegíveis"),
        ("Latência", f"{latency} ms", "pipeline local"),
    ]
    for column, (label, value, note) in zip(st.columns(5), cards):
        with column:
            st.markdown(status_card(label, value, note), unsafe_allow_html=True)


def render_gemma_context(payload: FrontEndPayload, request: DecisionRequest) -> None:
    fields = "".join(
        f"<span>{escape(field)}</span>" for field in payload.gemma_visible_summary.parsed_fields
    )
    notes = "".join(f"<li>{escape(note)}</li>" for note in payload.confidence_notes)
    parse_status = tool_status(payload, "parse_ticket_document")
    preview = json.dumps(
        {
            "exception": payload.gemma_visible_summary.exception_label,
            "ticket_content_type": request.ticket_content_type,
            "fields": payload.gemma_visible_summary.parsed_fields,
            "review_notes": payload.gemma_visible_summary.notes,
        },
        indent=2,
        sort_keys=True,
    )
    st.markdown(
        f"""
        <article class="card">
          <div class="card-head">
            <div><h3>Documento interpretado pelo Gemma 4</h3><p>Resultado avançado da leitura estruturada, sem chat nem chain-of-thought.</p></div>
            {chip("avançado", "purple")}
          </div>
          <div class="field-cloud">{fields}</div>
          <div class="mini-metrics">
            {mini_metric("Runtime", runtime_label())}
            {mini_metric("Etapa", "parse_ticket_document")}
            {mini_metric("Tipo do arquivo", request.ticket_content_type)}
            {mini_metric("Status", audit_status_label(parse_status))}
            {mini_metric("Confiança", confidence_value(payload))}
          </div>
          <pre class="json-preview">{escape(preview)}</pre>
          <ul class="note-list">{notes}</ul>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_operator_action(payload: FrontEndPayload) -> None:
    st.markdown(
        '<article class="card streamlit-card narrative-card"><div class="card-head"><div><h3>3. Ação do operador</h3><p>O sistema recomenda; o operador aprova, bloqueia ou justifica sobrescrita sem burlar restrição dura.</p></div></div>',
        unsafe_allow_html=True,
    )
    action = st.radio(
        "Ação",
        options=[str(item) for item in payload.operator_actions],
        format_func=operator_action_label,
        horizontal=True,
    )
    reason = st.text_input("Motivo obrigatório", value="OP-DEMO-01 revisou a decisão.")
    requested_truck = None
    requested_destination = None
    if action.endswith("override"):
        requested_truck = st.selectbox(
            "Caminhão solicitado", [item.truck_id for item in payload.queue_diff]
        )
        destination_options = sorted(
            {
                entry["destination_id"]
                for entry in (
                    payload.audit_record.hard_constraints_checked if payload.audit_record else []
                )
            }
        )
        if destination_options:
            requested_destination = st.selectbox("Destino solicitado", destination_options)
        else:
            st.warning("Nenhum destino validado disponível para sobrescrita.")
    if st.button("Registrar ação", type="primary"):
        try:
            finalized, updated_audit = finalize_operator_decision(
                payload=payload,
                action_type=action,
                reason=reason,
                actor_id="OP-DEMO-01",
                requested_truck_id=requested_truck,
                requested_destination_id=requested_destination,
                sqlite_store=_ui_sqlite_store(),
            )
        except PequiFluxError as exc:
            st.error(exc.message)
        else:
            st.success("Ação humana finalizada e persistida.")
            st.session_state["operator_finalization"] = finalized.model_dump(mode="json")
            st.session_state["operator_audit_update"] = updated_audit.operator_action
    if "operator_finalization" in st.session_state:
        st.json(st.session_state["operator_finalization"])
    st.markdown("</article>", unsafe_allow_html=True)


def render_audit(payload: FrontEndPayload) -> None:
    steps = [
        ("requisição", payload.request_id),
        ("cenário", payload.scenario_id),
        ("variante", payload.variant),
        ("regras", ", ".join(payload.audit_record.fired_rules if payload.audit_record else [])),
    ]
    items = "".join(
        f'<div class="audit-step"><strong>{escape(label)}</strong><span>{escape(value)}</span></div>'
        for label, value in steps
    )
    st.markdown(
        f"""
        <article class="card">
          <div class="card-head">
            <div><h3>Trilha auditável</h3><p>Campos mínimos para reconstruir a decisão.</p></div>
            {chip("XAI", "green")}
          </div>
          <div class="audit-list">{items}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_driver_message(payload: FrontEndPayload) -> None:
    st.markdown(
        f"""
        <article class="card phone-card">
          <div class="phone">
            <div class="phone-head"><strong>PequiFlux</strong><span>Mensagem ao motorista</span></div>
            <div class="bubble">Seu check-in foi processado.</div>
            <div class="bubble me">{escape(payload.driver_message.message)}</div>
            <div class="phone-input">Mensagem</div>
          </div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _ui_sqlite_store() -> SQLiteStore:
    return SQLiteStore(path=os.getenv("PEQUIFLUX_SQLITE_PATH", "var/db/pequiflux_ui.db"))


def _input_package_card(request: DecisionRequest, case: dict[str, Any]) -> str:
    resources = request.resource_state
    blocked = sum(1 for resource in resources if resource.status.lower() == "blocked")
    available = sum(1 for resource in resources if resource.status.lower() == "available")
    scenario_title = case.get("title") or request.scenario_id
    package_items = [
        ("cenário", scenario_title),
        ("variante", request.variant),
        ("clima", f"{request.weather_state.precipitation}/{request.weather_state.severity}"),
        ("recursos", f"{len(resources)} totais · {available} livres · {blocked} bloqueados"),
        ("fila", Path(request.queue_csv_ref).name),
        ("ticket", Path(request.ticket_ref).name),
    ]
    items = "".join(
        f"<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in package_items
    )
    return f"""
    <article class="card input-package">
      <div class="card-head">
        <div><h3>Pacote operacional</h3><p>Entradas que alimentam Gemma, regras e auditoria.</p></div>
        {chip("I/O", "green")}
      </div>
      <div class="package-grid">{items}</div>
    </article>
    """


def _ticket_preview_card(request: DecisionRequest) -> str:
    ticket_path = Path(request.ticket_ref)
    preview = _ticket_preview_text(ticket_path, request.ticket_content_type)
    return f"""
    <article class="card ticket-preview">
      <div class="card-head">
        <div><h3>Ticket recebido</h3><p>Documento bruto ao lado do resumo estruturado do Gemma.</p></div>
        {chip(request.ticket_content_type, "purple")}
      </div>
      <div class="document-tile">
        <div class="document-icon">{_document_icon(request.ticket_content_type)}</div>
        <div>
          <strong>{escape(ticket_path.name)}</strong>
          <span>{escape(preview)}</span>
        </div>
      </div>
    </article>
    """


def _ticket_preview_text(ticket_path: Path, content_type: str) -> str:
    if content_type == "text/plain":
        try:
            text = ticket_path.read_text(encoding="utf-8").strip()
        except OSError:
            return "Texto indisponível no cache da execução."
        return " ".join(text.split())[:360] or "Ticket textual vazio."
    if content_type == "application/pdf":
        return "PDF encaminhado ao leitor local; a UI não mostra prompt nem OCR bruto."
    return "Imagem encaminhada ao leitor local; interpretação multimodal ocorre no container."


def _document_icon(content_type: str) -> str:
    if content_type == "application/pdf":
        return "PDF"
    if content_type.startswith("image/"):
        return "IMG"
    return "TXT"


def copilot_timeline_card(payload: FrontEndPayload, request: DecisionRequest) -> str:
    steps = [
        (
            "1. Documento interpretado",
            step_status(payload, "parse_ticket_document"),
            f"Campos: {', '.join(payload.gemma_visible_summary.parsed_fields[:5])}.",
        ),
        (
            "2. Regras conferidas",
            step_status(payload, "resolve_truth"),
            "Conflitos materiais e necessidade de revisão foram avaliados.",
        ),
        (
            "3. Alternativas bloqueadas",
            (
                "ok"
                if payload.audit_record and payload.audit_record.hard_constraints_checked
                else "review"
            ),
            constraints_summary(payload),
        ),
        (
            "4. Fila recalculada",
            step_status(payload, "rank_candidates"),
            ranking_summary(payload),
        ),
        (
            "5. Operador decide",
            "ready" if payload.operator_actions else "review",
            f"Ações disponíveis: {operator_actions_label(payload.operator_actions)}.",
        ),
    ]
    items = "".join(timeline_item(*step) for step in steps)
    return f"""
    <article class="card copilot-timeline">
      <div class="card-head">
        <div><h3>Linha do Copilot</h3><p>Leitura guiada do raciocínio operacional, sem chat livre.</p></div>
        {chip(display_status(str(payload.decision_status)), "blue")}
      </div>
      <div class="timeline">{items}</div>
    </article>
    """


def tool_badges_card(payload: FrontEndPayload) -> str:
    badges = [
        (
            "Documento interpretado",
            "parse_ticket_document",
            tool_status(payload, "parse_ticket_document"),
        ),
        ("Regras conferidas", "resolve_truth", tool_status(payload, "resolve_truth")),
        (
            "Alternativas bloqueadas",
            "validate_hard_constraints",
            tool_status(payload, "validate_hard_constraints"),
        ),
        ("Fila recalculada", "rank_candidates", tool_status(payload, "rank_candidates")),
        ("Auditoria gerada", "generate_audit_payload", "ok" if payload.audit_record else "blocked"),
    ]
    items = "".join(
        f'<div class="tool-badge {status}" title="{escape(technical)}"><strong>{escape(name)}</strong><span>{escape(status_label(status))}</span></div>'
        for name, technical, status in badges
    )
    tool_call_items = _gemma_tool_call_items(payload)
    return f"""
    <article class="card tools-card">
      <div class="card-head">
        <div><h3>Painel avançado</h3><p>Status das etapas internas permitidas pelo blueprint.</p></div>
        {chip("auditoria", "green")}
      </div>
      <div class="tool-grid">{items}</div>
      {tool_call_items}
    </article>
    """


def _gemma_tool_call_items(payload: FrontEndPayload) -> str:
    if not payload.audit_record or not payload.audit_record.tool_calls:
        return ""
    labels = {
        "requested": "solicitado",
        "executed": "executado",
        "error": "erro",
    }
    ordered_tools = [
        "validate_hard_constraints",
        "rank_candidates",
        "generate_audit_payload",
    ]
    grouped: dict[str, list[Any]] = {}
    for record in payload.audit_record.tool_calls:
        grouped.setdefault(record.tool_name, []).append(record)
    tool_names = [tool_name for tool_name in ordered_tools if tool_name in grouped]
    tool_names.extend(tool_name for tool_name in grouped if tool_name not in ordered_tools)

    items = "".join(
        _tool_call_audit_item(tool_name, grouped[tool_name], labels) for tool_name in tool_names
    )
    if not items:
        return ""
    return f"""
      <div class="tool-call-summary">
        <h4>Planejador de ferramentas Gemma</h4>
        <p>Estado → ferramenta → status executado sob whitelist.</p>
        <ol class="tool-call-list">{items}</ol>
      </div>
    """


def _tool_call_audit_item(tool_name: str, records: list[Any], labels: dict[str, str]) -> str:
    status_flow = " → ".join(
        labels.get(status, status)
        for status in _unique_in_order(record.status for record in records)
    )
    latest = records[-1]
    purpose = next((record.purpose for record in reversed(records) if record.purpose), "")
    state = latest.state
    error_code = next((record.error_code for record in reversed(records) if record.error_code), "")
    status_class = "error" if error_code else latest.status
    error_html = (
        f'<span class="tool-call-error">Erro: {escape(error_code)}</span>' if error_code else ""
    )
    return f"""
          <li class="tool-call-item {escape(status_class)}">
            <div class="tool-call-flow">
              <span class="tool-call-name">{escape(state)} → {escape(tool_name)}</span>
              <strong>{escape(status_flow)}</strong>
            </div>
            <div class="tool-call-meta">
              <span>Motivo: {escape(purpose or "não informado")}</span>
              <span>Estado: {escape(state)}</span>
              {error_html}
            </div>
          </li>
    """


def _unique_in_order(values) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique
