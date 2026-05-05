from __future__ import annotations

from pathlib import Path
from typing import Any

from app.domain.models import DecisionRequest, FrontEndPayload

from app.ui.components.common import (
    _chip,
    _constraint_failure_summary,
    _escape,
    _first_skipped_truck,
    _gemma_short_summary,
    _operator_actions_label,
    _primary_rule,
    _raw_fifo_call,
    _raw_queue_rows,
    _reason_detail_label,
    _story_tile,
    _truck_failure_rules,
    _confidence_value,
)


def _judge_comparison_card(
    payload: FrontEndPayload,
    request: DecisionRequest,
    fifo_payload: FrontEndPayload | None,
) -> str:
    fifo_truck, fifo_destination = _raw_fifo_call(request)
    if fifo_truck == "sem chamada" and fifo_payload and fifo_payload.recommended_truck:
        fifo_truck = fifo_payload.recommended_truck.truck_id
    if fifo_destination == "sem destino" and fifo_payload and fifo_payload.recommended_destination:
        fifo_destination = fifo_payload.recommended_destination.destination_id
    recommended_truck = payload.recommended_truck.truck_id if payload.recommended_truck else "revisao humana"
    recommended_destination = (
        payload.recommended_destination.destination_id
        if payload.recommended_destination
        else "aguardar decisao humana"
    )
    applied_rule = _primary_rule(payload)
    gemma_fields = _gemma_short_summary(payload)
    return f"""
    <section class="judge-comparison">
      <div class="comparison-tile fifo">
        <span>FIFO chamaria</span>
        <strong>{_escape(fifo_truck)}</strong>
        <p>Destino provavel: {_escape(fifo_destination)}</p>
      </div>
      <div class="comparison-arrow">vs</div>
      <div class="comparison-tile peqi">
        <span>Pe-Q.I recomenda</span>
        <strong>{_escape(recommended_truck)}</strong>
        <p>Destino: {_escape(recommended_destination)}</p>
      </div>
      <div class="comparison-proof">
        <div><span>Documento interpretado</span><strong>{_escape(gemma_fields)}</strong></div>
        <div><span>Regra aplicada</span><strong>{_escape(applied_rule)}</strong></div>
        <div><span>Decisao humana</span><strong>{_escape(_operator_actions_label(payload.operator_actions))}</strong></div>
      </div>
    </section>
    """


def _recommended_decision_card(payload: FrontEndPayload) -> str:
    skipped_truck = _first_skipped_truck(payload)
    recommended_truck = payload.recommended_truck.truck_id if payload.recommended_truck else "sem chamada"
    destination = (
        payload.recommended_destination.destination_id
        if payload.recommended_destination
        else "revisao humana"
    )
    reason_items = "".join(
        f"<li>{_escape(_reason_detail_label(item))}</li>" for item in payload.reason_details[:3]
    )
    return f"""
    <section class="decision-story single">
      <div class="story-main">
        <span class="eyebrow dark">1. Decisao recomendada</span>
        <h2>{_escape(recommended_truck)} deve ir para { _escape(destination) }</h2>
        <p>O primeiro da fila nao e chamado automaticamente. A recomendacao preserva legitimidade porque mostra o criterio que sustenta a quebra.</p>
        <ul>{reason_items}</ul>
      </div>
      <div class="story-grid compact">
        {_story_tile("Nao chamar agora", skipped_truck or "nenhum", "Nao e fura-fila: ha evidencia operacional para nao chamar o primeiro.")}
        {_story_tile("Chamar agora", recommended_truck, f"Destino: {destination}", "action")}
        {_story_tile("Critério sustentado", "verificavel", _reason_detail_label(payload.reason_summary), "proof")}
      </div>
    </section>
    """


def _queue_stack_card(payload: FrontEndPayload, request: DecisionRequest) -> str:
    queue_rows = _raw_queue_rows(request)[:5]
    diff_by_truck = {entry.truck_id: entry for entry in payload.queue_diff}
    recommended_id = payload.recommended_truck.truck_id if payload.recommended_truck else None
    first_id = queue_rows[0]["truck_id"] if queue_rows else None
    cards = "".join(
        _queue_stack_item(row, diff_by_truck.get(row["truck_id"]), payload, first_id, recommended_id)
        for row in queue_rows
    )
    return f"""
    <section class="queue-focus">
      <div class="card-head">
        <div><h3>Fila em decisao</h3><p>Os 5 primeiros caminhoes como o operador ve: quem subiu, quem ficou aguardando e por qual restricao.</p></div>
        {_chip("FIFO visivel", "green")}
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
    after = "-" if diff_entry is None or diff_entry.position_after is None else str(diff_entry.position_after)
    destination = row.get("declared_destination") or "sem destino"
    return f"""
    <article class="queue-card {card_class}">
      <div class="queue-rank">#{_escape(row["position"])}</div>
      <div>
        <strong>{_escape(truck_id)}</strong>
        <span>{_escape(row.get("vehicle_type") or "veiculo")} · destino {_escape(destination)}</span>
      </div>
      <div class="queue-state">
        <em>{_escape(label)}</em>
        <small>{_escape(detail)}</small>
      </div>
      <div class="queue-after">pos. {_escape(after)}</div>
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
        return "promoted", "chamado agora", f"antes #{before}; saiu da fila"
    if diff_entry and diff_entry.decision == "blocked":
        rules = _truck_failure_rules(payload, truck_id)
        detail = ", ".join(rules[:3]) if rules else diff_entry.reason
        return "blocked", "bloqueado por restricao", detail
    if truck_id == first_id and truck_id != recommended_id:
        rules = _truck_failure_rules(payload, truck_id)
        if rules:
            return "blocked", "bloqueado por restricao", ", ".join(rules[:3])
        return "waiting", "mantido aguardando", "sem criterio suficiente para chamada automatica"
    if diff_entry and diff_entry.decision == "unchanged":
        return "waiting", "mantido aguardando", diff_entry.reason
    if diff_entry and diff_entry.decision == "shifted":
        return "neutral", "avancou na fila", diff_entry.reason
    return "neutral", "sem mudanca", "ordem preservada ate nova avaliacao"


def _why_not_fifo_card(payload: FrontEndPayload) -> str:
    skipped_truck = _first_skipped_truck(payload)
    if skipped_truck:
        title = f"Por que {skipped_truck} nao foi chamado?"
        body = "Porque a fila pura perdeu legitimidade neste contexto: a decisao precisa respeitar restricoes, risco operacional e criterio publicado."
    else:
        title = "FIFO preservado"
        body = "O primeiro da fila continua compativel com as restricoes avaliadas."
    details = "".join(
        f"<li>{_escape(_reason_detail_label(item))}</li>" for item in payload.reason_details[:3]
    )
    return f"""
    <article class="card narrative-card">
      <div class="card-head">
        <div><h3>2. Por que nao FIFO?</h3><p>{_escape(title)}</p></div>
        {_chip("anti-arbitragem", "green")}
      </div>
      <p>{_escape(body)}</p>
      <ul class="note-list">{details}</ul>
    </article>
    """


def _gemma_extraction_card(payload: FrontEndPayload, request: DecisionRequest) -> str:
    parsed = payload.benchmark_observed.get("parsed_ticket", {})
    fields = [
        ("ticket", parsed.get("ticket_id") or Path(request.ticket_ref).name),
        ("caminhao lido", parsed.get("truck_id") or "nao informado"),
        ("carga", parsed.get("load_condition") or "unknown"),
        ("destino no ticket", ", ".join(parsed.get("destination_constraints") or []) or "nao informado"),
        ("confianca", _confidence_value(payload)),
    ]
    items = "".join(
        f"<div><span>{_escape(label)}</span><strong>{_escape(value)}</strong></div>"
        for label, value in fields
    )
    return f"""
    <article class="card narrative-card">
      <div class="card-head">
        <div><h3>3. Documento interpretado</h3><p>Campos do ticket que entram na decisao, sem expor prompt ou JSON.</p></div>
        {_chip("leitura", "purple")}
      </div>
      <div class="package-grid">{items}</div>
    </article>
    """


def _blocked_constraints_card(payload: FrontEndPayload) -> str:
    failures = _constraint_failure_summary(payload)
    items = "".join(
        f"<li><strong>{_escape(constraint)}</strong><span>{_escape(detail)}</span></li>"
        for constraint, detail in failures[:4]
    )
    rejected = len(payload.audit_record.rejected_candidates) if payload.audit_record else 0
    return f"""
    <article class="card narrative-card">
      <div class="card-head">
        <div><h3>4. Quais restricoes bloquearam alternativas</h3><p>{rejected} pares foram rejeitados antes de qualquer recomendacao.</p></div>
        {_chip("regras duras", "green")}
      </div>
      <ul class="constraint-list">{items}</ul>
    </article>
    """
