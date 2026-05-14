from __future__ import annotations

from pathlib import Path
from typing import Any

from app.domain.models import DecisionRequest, FrontEndPayload
from app.services.raw_fifo import raw_queue_rows

from app.ui.components.common import (
    chip,
    confidence_value,
    constraint_failure_summary,
    display_status,
    document_interpreter_badge,
    document_interpreter_title,
    escape,
    reason_detail_label,
    story_tile,
    truck_failure_rules,
)
from app.ui.i18n import Language, t


def recommended_decision_card(payload: FrontEndPayload, lang: Language = "pt") -> str:
    status = str(payload.decision_status)
    recommended_truck = payload.recommended_truck.truck_id if payload.recommended_truck else "-"
    destination = (
        payload.recommended_destination.destination_id if payload.recommended_destination else "-"
    )
    if status.endswith("REVIEW_REQUIRED"):
        title = t("decision.review.title", lang)
        summary = t("decision.review.summary", lang)
    elif status.endswith("BLOCKED"):
        title = t("decision.blocked.title", lang)
        summary = t("decision.blocked.summary", lang)
    else:
        title = t("decision.ready.title", lang, truck=recommended_truck, destination=destination)
        summary = t("decision.ready.summary", lang)
    reason_items = "".join(
        f"<li>{escape(reason_detail_label(item))}</li>" for item in payload.reason_details[:3]
    )
    return f"""
    <section class="decision-story single">
      <div class="story-main">
        <span class="eyebrow dark">{escape(t("decision.eyebrow", lang))}</span>
        <h2>{escape(title)}</h2>
        <p>{escape(summary)}</p>
        <ul>{reason_items}</ul>
      </div>
      <div class="story-grid compact">
        {story_tile(t("decision.tile.status", lang), display_status(status), t("decision.tile.status.detail", lang))}
        {story_tile(t("decision.tile.truck", lang), recommended_truck, t("decision.tile.destination", lang, destination=destination), "action")}
        {story_tile(t("decision.tile.reason", lang), t("decision.tile.reason.value", lang), reason_detail_label(payload.reason_summary), "proof")}
      </div>
    </section>
    """


def queue_stack_card(
    payload: FrontEndPayload,
    request: DecisionRequest,
    lang: Language = "pt",
) -> str:
    queue_rows = raw_queue_rows(request)[:5]
    diff_by_truck = {entry.truck_id: entry for entry in payload.queue_diff}
    recommended_id = payload.recommended_truck.truck_id if payload.recommended_truck else None
    first_id = queue_rows[0]["truck_id"] if queue_rows else None
    cards = "".join(
        _queue_stack_item(
            row, diff_by_truck.get(row["truck_id"]), payload, first_id, recommended_id, lang
        )
        for row in queue_rows
    )
    return f"""
    <section class="queue-focus">
      <div class="card-head">
        <div><h3>{escape(t("queue.card.title", lang))}</h3><p>{escape(t("queue.card.copy", lang))}</p></div>
        {chip(t("queue.card.badge", lang), "green")}
      </div>
      <div class="queue-stack">{cards}</div>
    </section>
    """


def _queue_stack_item(
    row: dict[str, str],
    diff_entry: Any,
    payload: FrontEndPayload,
    first_id: str | None,
    recommended_id: str | None,
    lang: Language,
) -> str:
    truck_id = row["truck_id"]
    card_class, label, detail = _queue_stack_state(
        truck_id,
        diff_entry,
        payload,
        first_id,
        recommended_id,
        lang,
    )
    after = (
        "-"
        if diff_entry is None or diff_entry.position_after is None
        else str(diff_entry.position_after)
    )
    destination = row.get("declared_destination") or t("queue.no_destination", lang)
    return f"""
    <article class="queue-card {card_class}">
      <div class="queue-rank">#{escape(row["position"])}</div>
      <div>
        <strong>{escape(truck_id)}</strong>
        <span>{escape(row.get("vehicle_type") or t("queue.vehicle", lang))} · {escape(t("queue.destination", lang, destination=destination))}</span>
      </div>
      <div class="queue-state">
        <em>{escape(label)}</em>
        <small>{escape(detail)}</small>
      </div>
      <div class="queue-after">{escape(t("queue.position", lang, position=after))}</div>
    </article>
    """


def _queue_stack_state(
    truck_id: str,
    diff_entry: Any,
    payload: FrontEndPayload,
    first_id: str | None,
    recommended_id: str | None,
    lang: Language,
) -> tuple[str, str, str]:
    if diff_entry and diff_entry.decision == "called":
        before = diff_entry.position_before if diff_entry else "-"
        return "promoted", t("queue.called", lang), t("queue.called.detail", lang, before=before)
    if diff_entry and diff_entry.decision == "blocked":
        rules = truck_failure_rules(payload, truck_id)
        detail = ", ".join(rules[:3]) if rules else reason_detail_label(diff_entry.reason)
        return "blocked", t("queue.blocked", lang), detail
    if truck_id == first_id and truck_id != recommended_id:
        rules = truck_failure_rules(payload, truck_id)
        if rules:
            return "blocked", t("queue.blocked", lang), ", ".join(rules[:3])
        return "waiting", t("queue.waiting", lang), t("queue.waiting.detail", lang)
    if diff_entry and diff_entry.decision == "unchanged":
        return "waiting", t("queue.waiting", lang), reason_detail_label(diff_entry.reason)
    if diff_entry and diff_entry.decision == "shifted":
        return "neutral", t("queue.shifted", lang), reason_detail_label(diff_entry.reason)
    return "neutral", t("queue.unchanged", lang), t("queue.unchanged.detail", lang)


def gemma_extraction_card(
    payload: FrontEndPayload,
    request: DecisionRequest,
    lang: Language = "pt",
) -> str:
    parsed = payload.benchmark_observed.get("parsed_ticket", {})
    parsed_fields = ", ".join(payload.gemma_visible_summary.parsed_fields) or t(
        "extract.unknown", lang
    )
    fields = [
        ("Ticket", parsed.get("ticket_id") or Path(request.ticket_ref).name),
        (t("extract.truck", lang), parsed.get("truck_id") or t("extract.unknown", lang)),
        (t("extract.load", lang), parsed.get("load_condition") or "unknown"),
        (
            t("extract.destination", lang),
            ", ".join(parsed.get("destination_constraints") or [])
            or t("extract.unknown", lang),
        ),
        (t("extract.confidence", lang), confidence_value(payload)),
        (t("extract.fields", lang), parsed_fields),
    ]
    items = "".join(
        f"<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in fields
    )
    return f"""
    <article class="card narrative-card">
      <div class="card-head">
        <div><h3>{escape(document_interpreter_title())}</h3><p>{escape(t("extract.copy", lang))}</p></div>
        {chip(document_interpreter_badge(), "purple")}
      </div>
      <div class="package-grid">{items}</div>
    </article>
    """


def blocked_constraints_card(payload: FrontEndPayload, lang: Language = "pt") -> str:
    failures = constraint_failure_summary(payload)
    items = "".join(
        f"<li><strong>{escape(constraint)}</strong><span>{escape(detail)}</span></li>"
        for constraint, detail in failures[:4]
    )
    rejected = len(payload.audit_record.rejected_candidates) if payload.audit_record else 0
    return f"""
    <article class="card narrative-card">
      <div class="card-head">
        <div><h3>{escape(t("constraints.title", lang))}</h3><p>{escape(t("constraints.copy", lang, rejected=rejected))}</p></div>
        {chip(t("constraints.badge", lang), "green")}
      </div>
      <ul class="constraint-list">{items}</ul>
    </article>
    """
