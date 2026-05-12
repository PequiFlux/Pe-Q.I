from __future__ import annotations

from pathlib import Path
from typing import Any

from app.domain.models import DecisionRequest, FrontEndPayload
from app.services.raw_fifo import raw_queue_rows

from app.ui.components.common import (
    chip,
    copy_text,
    confidence_value,
    constraint_failure_summary,
    escape,
    is_english,
    reason_detail_label,
    story_tile,
    truck_failure_rules,
)


def recommended_decision_card(payload: FrontEndPayload) -> str:
    status = str(payload.decision_status)
    recommended_truck = payload.recommended_truck.truck_id if payload.recommended_truck else "-"
    destination = (
        payload.recommended_destination.destination_id if payload.recommended_destination else "-"
    )
    if status.endswith("REVIEW_REQUIRED"):
        title = copy_text("Decision requires human review", "Decisão exige revisão humana")
        summary = copy_text(
            "The system found insufficient truth or material conflict for safe automation.",
            "O sistema encontrou verdade insuficiente ou conflito material para automatizar com segurança.",
        )
    elif status.endswith("BLOCKED"):
        title = copy_text("No safe automatic dispatch", "Sem despacho automático seguro")
        summary = copy_text(
            "No truck-destination pair can be released automatically under the current constraints.",
            "Nenhum par caminhão-destino pode ser liberado automaticamente com as restrições atuais.",
        )
    else:
        title = (
            f"{recommended_truck} should go to {destination}"
            if is_english()
            else f"{recommended_truck} deve ir para {destination}"
        )
        summary = copy_text(
            "Operational recommendation based on the interpreted ticket, yard state, and critical constraints checked.",
            "Recomendação operacional baseada no ticket interpretado, no estado do pátio e nas restrições críticas avaliadas.",
        )
    reason_items = "".join(
        f"<li>{escape(reason_detail_label(item))}</li>" for item in payload.reason_details[:3]
    )
    return f"""
    <section class="decision-story single">
      <div class="story-main">
        <span class="eyebrow dark">{escape(copy_text("Analysis result", "Resultado da análise"))}</span>
        <h2>{escape(title)}</h2>
        <p>{escape(summary)}</p>
        <ul>{reason_items}</ul>
      </div>
      <div class="story-grid compact">
        {story_tile("Status", status, copy_text("Current result before human action.", "Resultado atual antes da ação humana."))}
        {story_tile(copy_text("Truck", "Caminhão"), recommended_truck, copy_text(f"Destination: {destination}", f"Destino: {destination}"), "action")}
        {story_tile(copy_text("Operational reason", "Motivo operacional"), copy_text("verifiable", "verificável"), reason_detail_label(payload.reason_summary), "proof")}
      </div>
    </section>
    """


def queue_stack_card(payload: FrontEndPayload, request: DecisionRequest) -> str:
    queue_rows = raw_queue_rows(request)[:5]
    diff_by_truck = {entry.truck_id: entry for entry in payload.queue_diff}
    recommended_id = payload.recommended_truck.truck_id if payload.recommended_truck else None
    first_id = queue_rows[0]["truck_id"] if queue_rows else None
    cards = "".join(
        _queue_stack_item(
            row, diff_by_truck.get(row["truck_id"]), payload, first_id, recommended_id
        )
        for row in queue_rows
    )
    return f"""
    <section class="queue-focus">
      <div class="card-head">
        <div><h3>{escape(copy_text("Queue under decision", "Fila em decisão"))}</h3><p>{escape(copy_text("The first 5 trucks as the operator sees them: who moved up, who kept waiting, and which constraint explains it.", "Os 5 primeiros caminhões como o operador vê: quem subiu, quem ficou aguardando e por qual restrição."))}</p></div>
        {chip(copy_text("operational queue", "fila operacional"), "green")}
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
) -> str:
    truck_id = row["truck_id"]
    card_class, label, detail = _queue_stack_state(
        truck_id,
        diff_entry,
        payload,
        first_id,
        recommended_id,
    )
    after = (
        "-"
        if diff_entry is None or diff_entry.position_after is None
        else str(diff_entry.position_after)
    )
    destination = row.get("declared_destination") or copy_text("no destination", "sem destino")
    vehicle_type = row.get("vehicle_type") or copy_text("vehicle", "veículo")
    destination_label = copy_text("destination", "destino")
    position_label = copy_text("pos.", "pos.")
    return f"""
    <article class="queue-card {card_class}">
      <div class="queue-rank">#{escape(row["position"])}</div>
      <div>
        <strong>{escape(truck_id)}</strong>
        <span>{escape(vehicle_type)} · {escape(destination_label)} {escape(destination)}</span>
      </div>
      <div class="queue-state">
        <em>{escape(label)}</em>
        <small>{escape(detail)}</small>
      </div>
      <div class="queue-after">{escape(position_label)} {escape(after)}</div>
    </article>
    """


def _queue_stack_state(
    truck_id: str,
    diff_entry: Any,
    payload: FrontEndPayload,
    first_id: str | None,
    recommended_id: str | None,
) -> tuple[str, str, str]:
    if diff_entry and diff_entry.decision == "called":
        before = diff_entry.position_before if diff_entry else "-"
        return (
            "promoted",
            copy_text("called now", "chamado agora"),
            copy_text(f"before #{before}; left the queue", f"antes #{before}; saiu da fila"),
        )
    if diff_entry and diff_entry.decision == "blocked":
        rules = truck_failure_rules(payload, truck_id)
        detail = ", ".join(rules[:3]) if rules else diff_entry.reason
        return "blocked", copy_text("blocked by constraint", "bloqueado por restrição"), detail
    if truck_id == first_id and truck_id != recommended_id:
        rules = truck_failure_rules(payload, truck_id)
        if rules:
            return (
                "blocked",
                copy_text("blocked by constraint", "bloqueado por restrição"),
                ", ".join(rules[:3]),
            )
        return (
            "waiting",
            copy_text("kept waiting", "mantido aguardando"),
            copy_text(
                "no sufficient criterion for automatic call",
                "sem critério suficiente para chamada automática",
            ),
        )
    if diff_entry and diff_entry.decision == "unchanged":
        return "waiting", copy_text("kept waiting", "mantido aguardando"), diff_entry.reason
    if diff_entry and diff_entry.decision == "shifted":
        return "neutral", copy_text("moved up in queue", "avancou na fila"), diff_entry.reason
    return (
        "neutral",
        copy_text("no change", "sem mudança"),
        copy_text(
            "order preserved until a new evaluation",
            "ordem preservada até nova avaliação",
        ),
    )


def gemma_extraction_card(payload: FrontEndPayload, request: DecisionRequest) -> str:
    parsed = payload.benchmark_observed.get("parsed_ticket", {})
    not_informed = copy_text("not informed", "não informado")
    parsed_fields = ", ".join(payload.gemma_visible_summary.parsed_fields) or not_informed
    fields = [
        ("Ticket", parsed.get("ticket_id") or Path(request.ticket_ref).name),
        (copy_text("Read truck", "Caminhão lido"), parsed.get("truck_id") or not_informed),
        (copy_text("Load type", "Tipo de carga"), parsed.get("load_condition") or "unknown"),
        (
            copy_text("Extracted destination", "Destino extraído"),
            ", ".join(parsed.get("destination_constraints") or []) or not_informed,
        ),
        (copy_text("Confidence", "Confiança"), confidence_value(payload)),
        (copy_text("Fields used in the decision", "Campos usados na decisão"), parsed_fields),
    ]
    items = "".join(
        f"<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"
        for label, value in fields
    )
    return f"""
    <article class="card narrative-card">
      <div class="card-head">
        <div><h3>{escape(copy_text("Document interpreted by Gemma 4", "Documento interpretado pelo Gemma 4"))}</h3><p>{escape(copy_text("Ticket fields that enter the decision, without exposing prompt or JSON.", "Campos do ticket que entram na decisão, sem expor prompt ou JSON."))}</p></div>
        {chip("Gemma 4", "purple")}
      </div>
      <div class="package-grid">{items}</div>
    </article>
    """


def blocked_constraints_card(payload: FrontEndPayload) -> str:
    failures = constraint_failure_summary(payload)
    items = "".join(
        f"<li><strong>{escape(constraint)}</strong><span>{escape(detail)}</span></li>"
        for constraint, detail in failures[:4]
    )
    rejected = len(payload.audit_record.rejected_candidates) if payload.audit_record else 0
    return f"""
    <article class="card narrative-card">
      <div class="card-head">
        <div><h3>{escape(copy_text("4. Which constraints blocked alternatives", "4. Quais restrições bloquearam alternativas"))}</h3><p>{escape(copy_text(f"{rejected} pairs were rejected before any recommendation.", f"{rejected} pares foram rejeitados antes de qualquer recomendação."))}</p></div>
        {chip(copy_text("hard rules", "regras duras"), "green")}
      </div>
      <ul class="constraint-list">{items}</ul>
    </article>
    """
