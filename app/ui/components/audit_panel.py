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
    document_interpreter_detail,
    document_interpreter_title,
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
from app.ui.i18n import Language, t


def render_input_evidence(
    payload: FrontEndPayload,
    request: DecisionRequest,
    case: dict[str, Any],
    lang: Language = "pt",
) -> None:
    left, right = st.columns([0.92, 1.08], gap="large")
    with left:
        st.markdown(_input_package_card(request, case, lang=lang), unsafe_allow_html=True)
    with right:
        st.markdown(_ticket_preview_card(request, lang=lang), unsafe_allow_html=True)


def render_status_bar(payload: FrontEndPayload, lang: Language = "pt") -> None:
    truck = payload.recommended_truck.truck_id if payload.recommended_truck else "-"
    destination = (
        payload.recommended_destination.destination_id if payload.recommended_destination else "-"
    )
    rejected = len(payload.audit_record.rejected_candidates) if payload.audit_record else 0
    latency = sum(payload.latency_ms.values())
    cards = [
        (
            t("decision.tile.status", lang),
            display_status(str(payload.decision_status), lang=lang),
            t("status.note.status", lang),
        ),
        (t("status.truck", lang), truck, t("status.note.truck", lang)),
        (t("status.destination", lang), destination, t("status.note.destination", lang)),
        (t("status.rejections", lang), str(rejected), t("status.note.rejections", lang)),
        (t("status.latency", lang), f"{latency} ms", t("status.note.latency", lang)),
    ]
    for column, (label, value, note) in zip(st.columns(5), cards):
        with column:
            st.markdown(status_card(label, value, note), unsafe_allow_html=True)


def render_gemma_context(
    payload: FrontEndPayload, request: DecisionRequest, lang: Language = "pt"
) -> None:
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
            <div><h3>{escape(document_interpreter_title(lang))}</h3><p>{escape(document_interpreter_detail(lang))}</p></div>
            {chip(t("audit.advanced", lang), "purple")}
          </div>
          <div class="field-cloud">{fields}</div>
          <div class="mini-metrics">
            {mini_metric(t("proof.runtime", lang), runtime_label())}
            {mini_metric(t("audit.step", lang), "parse_ticket_document")}
            {mini_metric(t("audit.file_type", lang), request.ticket_content_type)}
            {mini_metric(t("decision.tile.status", lang), audit_status_label(parse_status, lang=lang))}
            {mini_metric(t("audit.confidence", lang), confidence_value(payload))}
          </div>
          <pre class="json-preview">{escape(preview)}</pre>
          <ul class="note-list">{notes}</ul>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_operator_action(payload: FrontEndPayload, lang: Language = "pt") -> None:
    st.markdown(
        (
            '<article class="card streamlit-card narrative-card"><div class="card-head"><div>'
            f'<h3>{escape(t("operator.action.title", lang))}</h3>'
            f'<p>{escape(t("operator.action.copy", lang))}</p></div></div>'
        ),
        unsafe_allow_html=True,
    )
    action = st.radio(
        t("operator.action.label", lang),
        options=[str(item) for item in payload.operator_actions],
        format_func=lambda value: operator_action_label(value, lang=lang),
        horizontal=True,
    )
    reason = st.text_input(t("operator.reason", lang), value=t("operator.reason.default", lang))
    requested_truck = None
    requested_destination = None
    if action.endswith("override"):
        requested_truck = st.selectbox(
            t("operator.requested_truck", lang), [item.truck_id for item in payload.queue_diff]
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
            requested_destination = st.selectbox(
                t("operator.requested_destination", lang), destination_options
            )
        else:
            st.warning(t("operator.no_destination", lang))
    if st.button(t("operator.register_action", lang), type="primary"):
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
            st.success(t("operator.success", lang))
            st.session_state["operator_finalization"] = finalized.model_dump(mode="json")
            st.session_state["operator_audit_update"] = updated_audit.operator_action
    if "operator_finalization" in st.session_state:
        st.json(st.session_state["operator_finalization"])
    st.markdown("</article>", unsafe_allow_html=True)


def render_audit(payload: FrontEndPayload, lang: Language = "pt") -> None:
    steps = [
        (t("audit.request", lang), payload.request_id),
        (t("audit.scenario", lang), payload.scenario_id),
        (t("audit.variant", lang), payload.variant),
        (
            t("audit.rules", lang),
            ", ".join(payload.audit_record.fired_rules if payload.audit_record else []),
        ),
    ]
    items = "".join(
        f'<div class="audit-step"><strong>{escape(label)}</strong><span>{escape(value)}</span></div>'
        for label, value in steps
    )
    st.markdown(
        f"""
        <article class="card">
          <div class="card-head">
            <div><h3>{escape(t("audit.trail.title", lang))}</h3><p>{escape(t("audit.trail.copy", lang))}</p></div>
            {chip("XAI", "green")}
          </div>
          <div class="audit-list">{items}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def render_driver_message(payload: FrontEndPayload, lang: Language = "pt") -> None:
    message = _localized_driver_message(payload, lang)
    st.markdown(
        f"""
        <article class="card phone-card">
          <div class="phone">
            <div class="phone-head"><strong>PequiFlux</strong><span>{escape(t("driver.title", lang))}</span></div>
            <div class="bubble">{escape(t("driver.processed", lang))}</div>
            <div class="bubble me">{escape(message)}</div>
            <div class="phone-input">{escape(t("driver.input", lang))}</div>
          </div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _localized_driver_message(payload: FrontEndPayload, lang: Language) -> str:
    if lang == "pt":
        return payload.driver_message.message
    if (
        payload.decision_status == "PREVIEW_READY"
        and payload.recommended_truck
        and payload.recommended_destination
    ):
        return t(
            "driver.dispatch",
            lang,
            truck=payload.recommended_truck.truck_id,
            destination=payload.recommended_destination.destination_id,
            reason=payload.reason_summary,
        )
    if payload.decision_status == "BLOCKED":
        return t("driver.blocked", lang)
    return t("driver.review", lang)


def _ui_sqlite_store() -> SQLiteStore:
    return SQLiteStore(path=os.getenv("PEQUIFLUX_SQLITE_PATH", "var/db/pequiflux.db"))


def _input_package_card(
    request: DecisionRequest, case: dict[str, Any], lang: Language = "pt"
) -> str:
    resources = request.resource_state
    blocked = sum(1 for resource in resources if resource.status.lower() == "blocked")
    available = sum(1 for resource in resources if resource.status.lower() == "available")
    scenario_title = case.get("title") or request.scenario_id
    package_items = [
        (t("audit.scenario", lang), scenario_title),
        (t("audit.variant", lang), request.variant),
        (
            t("audit.weather", lang),
            f"{request.weather_state.precipitation}/{request.weather_state.severity}",
        ),
        (
            t("audit.resources", lang),
            t(
                "audit.resources.value",
                lang,
                total=len(resources),
                available=available,
                blocked=blocked,
            ),
        ),
        (t("audit.queue", lang), Path(request.queue_csv_ref).name),
        ("ticket", Path(request.ticket_ref).name),
    ]
    items = "".join(
        f"<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in package_items
    )
    return f"""
    <article class="card input-package">
      <div class="card-head">
        <div><h3>{escape(t("audit.package.title", lang))}</h3><p>{escape(t("audit.package.copy", lang))}</p></div>
        {chip("I/O", "green")}
      </div>
      <div class="package-grid">{items}</div>
    </article>
    """


def _ticket_preview_card(request: DecisionRequest, lang: Language = "pt") -> str:
    ticket_path = Path(request.ticket_ref)
    preview = _ticket_preview_text(ticket_path, request.ticket_content_type, lang=lang)
    return f"""
    <article class="card ticket-preview">
      <div class="card-head">
        <div><h3>{escape(t("audit.ticket.title", lang))}</h3><p>{escape(t("audit.ticket.copy", lang))}</p></div>
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


def _ticket_preview_text(ticket_path: Path, content_type: str, lang: Language = "pt") -> str:
    if content_type == "text/plain":
        try:
            text = ticket_path.read_text(encoding="utf-8").strip()
        except OSError:
            return t("audit.ticket.cache_missing", lang)
        return " ".join(text.split())[:360] or t("audit.ticket.empty", lang)
    if content_type == "application/pdf":
        return t("audit.ticket.pdf", lang)
    return t("audit.ticket.image", lang)


def _document_icon(content_type: str) -> str:
    if content_type == "application/pdf":
        return "PDF"
    if content_type.startswith("image/"):
        return "IMG"
    return "TXT"


def copilot_timeline_card(
    payload: FrontEndPayload, request: DecisionRequest, lang: Language = "pt"
) -> str:
    steps = [
        (
            t("timeline.document", lang),
            step_status(payload, "parse_ticket_document"),
            t(
                "timeline.fields",
                lang,
                fields=", ".join(payload.gemma_visible_summary.parsed_fields[:5]),
            ),
        ),
        (
            t("timeline.rules", lang),
            step_status(payload, "resolve_truth"),
            t("timeline.rules.copy", lang),
        ),
        (
            t("timeline.constraints", lang),
            (
                "ok"
                if payload.audit_record and payload.audit_record.hard_constraints_checked
                else "review"
            ),
            constraints_summary(payload, lang=lang),
        ),
        (
            t("timeline.queue", lang),
            step_status(payload, "rank_candidates"),
            ranking_summary(payload, lang=lang),
        ),
        (
            t("timeline.operator", lang),
            "ready" if payload.operator_actions else "review",
            t(
                "timeline.actions",
                lang,
                actions=operator_actions_label(payload.operator_actions, lang=lang),
            ),
        ),
    ]
    items = "".join(timeline_item(*step, lang=lang) for step in steps)
    return f"""
    <article class="card copilot-timeline">
      <div class="card-head">
        <div><h3>{escape(t("timeline.title", lang))}</h3><p>{escape(t("timeline.copy", lang))}</p></div>
        {chip(display_status(str(payload.decision_status), lang=lang), "blue")}
      </div>
      <div class="timeline">{items}</div>
    </article>
    """


def tool_badges_card(payload: FrontEndPayload, lang: Language = "pt") -> str:
    badges = [
        (
            t("tool.document", lang),
            "parse_ticket_document",
            tool_status(payload, "parse_ticket_document"),
        ),
        (t("tool.rules", lang), "resolve_truth", tool_status(payload, "resolve_truth")),
        (
            t("tool.constraints", lang),
            "validate_hard_constraints",
            tool_status(payload, "validate_hard_constraints"),
        ),
        (t("tool.queue", lang), "rank_candidates", tool_status(payload, "rank_candidates")),
        (
            t("tool.audit", lang),
            "generate_audit_payload",
            "ok" if payload.audit_record else "blocked",
        ),
    ]
    items = "".join(
        f'<div class="tool-badge {status}" title="{escape(technical)}"><strong>{escape(name)}</strong><span>{escape(status_label(status, lang=lang))}</span></div>'
        for name, technical, status in badges
    )
    tool_call_items = _gemma_tool_call_items(payload, lang=lang)
    return f"""
    <article class="card tools-card">
      <div class="card-head">
        <div><h3>{escape(t("tool.panel.title", lang))}</h3><p>{escape(t("tool.panel.copy", lang))}</p></div>
        {chip(t("tool.panel.badge", lang), "green")}
      </div>
      <div class="tool-grid">{items}</div>
      {tool_call_items}
    </article>
    """


def _gemma_tool_call_items(payload: FrontEndPayload, lang: Language = "pt") -> str:
    if not payload.audit_record or not payload.audit_record.tool_calls:
        return ""
    labels = (
        {
            "requested": "requested",
            "executed": "executed",
            "error": "error",
        }
        if lang == "en"
        else {
            "requested": "solicitado",
            "executed": "executado",
            "error": "erro",
        }
    )
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
        _tool_call_audit_item(tool_name, grouped[tool_name], labels, lang=lang)
        for tool_name in tool_names
    )
    if not items:
        return ""
    return (
        '<div class="tool-call-summary">'
        "<h4>Gemma Tool Planner</h4>"
        f'<p>{escape(t("tool.call.copy", lang))}</p>'
        f'<div class="tool-call-list">{items}</div>'
        "</div>"
    )


def _tool_call_audit_item(
    tool_name: str, records: list[Any], labels: dict[str, str], lang: Language = "pt"
) -> str:
    arrow = "→"
    status_flow = f" {arrow} ".join(
        labels.get(status, status)
        for status in _unique_in_order(record.status for record in records)
    )
    latest = records[-1]
    purpose = next((record.purpose for record in reversed(records) if record.purpose), "")
    state = latest.state
    error_code = next((record.error_code for record in reversed(records) if record.error_code), "")
    status_class = "error" if error_code else latest.status
    error_html = (
        f'<span class="tool-call-error">{escape(t("tool.call.error", lang))}: {escape(error_code)}</span>'
        if error_code
        else ""
    )
    missing = t("tool.call.missing", lang)
    return (
        f'<div class="tool-call-item {escape(status_class)}">'
        '<span class="tool-call-flow">'
        f'<span class="tool-call-name">{escape(state)} {arrow} {escape(tool_name)}</span>'
        f"<strong>{escape(status_flow)}</strong>"
        "</span>"
        '<span class="tool-call-meta">'
        f'<span>{escape(t("tool.call.purpose", lang))}: {escape(purpose or missing)}</span>'
        f'<span>{escape(t("tool.call.state", lang))}: {escape(state)}</span>'
        f"{error_html}"
        "</span>"
        "</div>"
    )


def _unique_in_order(values) -> list[str]:
    unique: list[str] = []
    for value in values:
        if value not in unique:
            unique.append(value)
    return unique
