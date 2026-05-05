from __future__ import annotations

import csv
import html
from pathlib import Path
from typing import Any

from app.domain.models import DecisionRequest, FrontEndPayload


def _step_status(payload: FrontEndPayload, latency_key: str) -> str:
    if latency_key in payload.latency_ms:
        return "ok"
    if payload.decision_status.endswith("BLOCKED") or str(payload.decision_status).endswith("REVIEW_REQUIRED"):
        return "review"
    return "pending"


def _tool_status(payload: FrontEndPayload, latency_key: str) -> str:
    if latency_key in payload.latency_ms:
        return "ok"
    if payload.audit_record is None:
        return "blocked"
    return "skipped"


def _constraints_summary(payload: FrontEndPayload) -> str:
    if payload.audit_record is None:
        return "Auditoria indisponivel porque o fluxo fechou antes da validacao."
    checked = len(payload.audit_record.hard_constraints_checked)
    rejected = len(payload.audit_record.rejected_candidates)
    return f"{checked} pares avaliados; {rejected} rejeitados por restricao dura."


def _constraint_failure_summary(payload: FrontEndPayload) -> list[tuple[str, str]]:
    if payload.audit_record is None:
        return [("auditoria", "Fluxo fechou antes da matriz de restricoes.")]
    failures: dict[str, str] = {}
    for rejected in payload.audit_record.rejected_candidates:
        for failure in rejected.get("failed_constraints", []):
            failures.setdefault(
                failure.get("constraint_id", "restricao"),
                failure.get("detail", "Par bloqueado por regra operacional."),
            )
    if not failures:
        return [("nenhuma", "Nenhuma alternativa foi bloqueada por restricao dura.")]
    return list(failures.items())


def _raw_fifo_call(request: DecisionRequest) -> tuple[str, str]:
    rows = _raw_queue_rows(request)
    waiting = [
        row
        for row in rows
        if (row.get("status") or "waiting").lower() == "waiting" and row.get("truck_id")
    ]
    if not waiting:
        return "sem chamada", "sem destino"
    first = min(waiting, key=lambda row: row.get("arrival_ts") or "")
    return first["truck_id"], first.get("declared_destination") or "sem destino"


def _raw_queue_rows(request: DecisionRequest) -> list[dict[str, str]]:
    try:
        rows = list(csv.DictReader(Path(request.queue_csv_ref).read_text(encoding="utf-8").splitlines()))
    except (OSError, csv.Error):
        return []
    rows = sorted(rows, key=lambda row: row.get("arrival_ts") or "")
    for position, row in enumerate(rows, start=1):
        row["position"] = str(position)
    return rows


def _truck_failure_rules(payload: FrontEndPayload, truck_id: str) -> list[str]:
    if payload.audit_record is None:
        return []
    rules: list[str] = []
    for rejected in payload.audit_record.rejected_candidates:
        if rejected.get("truck_id") != truck_id:
            continue
        for failure in rejected.get("failed_constraints", []):
            constraint_id = failure.get("constraint_id")
            if constraint_id and constraint_id not in rules:
                rules.append(constraint_id)
    return rules


def _primary_rule(payload: FrontEndPayload) -> str:
    failures = _constraint_failure_summary(payload)
    if failures and failures[0][0] != "nenhuma":
        return failures[0][0]
    if payload.audit_record and payload.audit_record.fired_rules:
        return payload.audit_record.fired_rules[0]
    return str(payload.decision_status)


def _gemma_short_summary(payload: FrontEndPayload) -> str:
    parsed = payload.benchmark_observed.get("parsed_ticket", {})
    parts = [
        parsed.get("load_condition"),
        parsed.get("truck_id"),
        _exception_label_short(payload.gemma_visible_summary.exception_label),
    ]
    visible = [str(part) for part in parts if part]
    if visible:
        return ", ".join(visible[:3])
    return ", ".join(payload.gemma_visible_summary.parsed_fields[:3]) or "campos indisponiveis"


def _exception_label_short(label: str) -> str:
    labels = {
        "RAIN_ON_OPEN_DESTINATION": "chuva em moega aberta",
        "WET_LOAD": "carga umida",
        "DOCUMENT_BLOCK": "documento bloqueado",
        "MANUAL_REVIEW_HINT": "revisao humana",
        "NO_EXCEPTION": "sem excecao",
    }
    return labels.get(label, label.lower().replace("_", " "))


def _ranking_summary(payload: FrontEndPayload) -> str:
    if payload.recommended_truck and payload.recommended_destination:
        return (
            f"{payload.recommended_truck.truck_id} -> "
            f"{payload.recommended_destination.destination_id}; "
            f"{len(payload.queue_diff)} itens no diff da fila."
        )
    return "Sem par recomendado; decisao exige bloqueio ou revisao."


def _operator_actions_label(actions: list[Any]) -> str:
    return ", ".join(_operator_action_label(str(action)) for action in actions)


def _operator_action_label(action: str) -> str:
    labels = {
        "approve": "aprovar",
        "block": "bloquear",
        "override": "sobrescrever",
    }
    return labels.get(action, action)


def _reason_detail_label(text: str) -> str:
    translations = {
        "FIFO ordering preserved when possible.": "Ordem de chegada preservada quando possivel.",
        "Long wait time increased ranking priority.": "Tempo de espera elevou a prioridade na fila.",
        "FIFO break justified by Long wait time increased ranking priority.": (
            "Quebra de FIFO justificada por tempo de espera e criterio verificavel."
        ),
    }
    if text in translations:
        return translations[text]
    return text


def _first_skipped_truck(payload: FrontEndPayload) -> str | None:
    skipped = [entry for entry in payload.queue_diff if entry.decision == "skipped"]
    if not skipped:
        return None
    return min(skipped, key=lambda entry: entry.position_before).truck_id


def _story_tile(label: str, value: str, detail: str, kind: str = "muted") -> str:
    return f"""
    <div class="story-tile {kind}">
      <span>{_escape(label)}</span>
      <strong>{_escape(value)}</strong>
      <p>{_escape(detail)}</p>
    </div>
    """


def _timeline_item(label: str, status: str, detail: str) -> str:
    return f"""
    <div class="timeline-item {status}">
      <div class="timeline-dot"></div>
      <div>
        <strong>{_escape(label)}</strong>
        <p>{_escape(detail)}</p>
      </div>
      {_chip(status, _status_color(status))}
    </div>
    """


def _mini_metric(label: str, value: str) -> str:
    return f"<div><span>{_escape(label)}</span><strong>{_escape(value)}</strong></div>"


def _confidence_value(payload: FrontEndPayload) -> str:
    for note in payload.confidence_notes:
        if note.startswith("parse_confidence="):
            return note.split("=", 1)[1]
    return "n/a"


def _percent_label(value: float | int) -> str:
    return f"{round(float(value) * 100):.0f}%"


def _status_color(status: str) -> str:
    if status in {"ok", "ready"}:
        return "green"
    if status in {"blocked", "review"}:
        return "red"
    return "blue"


def _display_status(status: str) -> str:
    return status.replace("_", " ")


def _status_card(label: str, value: str, note: str) -> str:
    return f"""
    <div class="status-card">
      <span>{_escape(label)}</span>
      <strong>{_escape(value)}</strong>
      <p>{_escape(note)}</p>
    </div>
    """


def _chip(text: str, color: str = "") -> str:
    suffix = f" {color}" if color else ""
    return f'<span class="chip{suffix}">{_escape(text)}</span>'


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)
