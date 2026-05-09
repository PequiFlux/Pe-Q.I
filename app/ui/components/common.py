from __future__ import annotations

import html
import os
from typing import Any

from app.domain.models import FrontEndPayload


def step_status(payload: FrontEndPayload, latency_key: str) -> str:
    if latency_key in payload.latency_ms:
        return "ok"
    if payload.decision_status.endswith("BLOCKED") or str(payload.decision_status).endswith(
        "REVIEW_REQUIRED"
    ):
        return "review"
    return "pending"


def tool_status(payload: FrontEndPayload, latency_key: str) -> str:
    if latency_key in payload.latency_ms:
        return "ok"
    if payload.audit_record is None:
        return "blocked"
    return "skipped"


def runtime_label() -> str:
    runtime = runtime_mode()
    if runtime == "ollama":
        return f"Ollama · {os.getenv('GEMMA_MODEL', 'gemma4:e2b')}"
    return runtime


def runtime_mode() -> str:
    return os.getenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama").strip().lower()


def document_interpreter_title() -> str:
    if runtime_mode() == "ollama":
        return "Documento interpretado pelo Gemma 4"
    return "Documento interpretado pelo runtime de teste"


def document_interpreter_badge() -> str:
    if runtime_mode() == "ollama":
        return "Gemma 4"
    return "modo teste"


def document_interpreter_detail() -> str:
    if runtime_mode() == "ollama":
        return "Resultado avançado da leitura estruturada, sem chat nem chain-of-thought."
    return "Leitura determinística de fixture para validação reproduzível, sem Ollama ou Gemma."


def audit_status_label(status: str) -> str:
    if status == "ok":
        return "OK"
    return status.upper()


def constraints_summary(payload: FrontEndPayload) -> str:
    if payload.audit_record is None:
        return "Auditoria indisponível porque o fluxo fechou antes da validação."
    checked = len(payload.audit_record.hard_constraints_checked)
    rejected = len(payload.audit_record.rejected_candidates)
    return f"{checked} pares avaliados; {rejected} rejeitados por restrição dura."


def constraint_failure_summary(payload: FrontEndPayload) -> list[tuple[str, str]]:
    if payload.audit_record is None:
        return [("auditoria", "Fluxo fechou antes da matriz de restrições.")]
    failures: dict[str, str] = {}
    for rejected in payload.audit_record.rejected_candidates:
        for failure in rejected.get("failed_constraints", []):
            failures.setdefault(
                failure.get("constraint_id", "restrição"),
                failure.get("detail", "Par bloqueado por regra operacional."),
            )
    if not failures:
        return [("nenhuma", "Nenhuma alternativa foi bloqueada por restrição dura.")]
    return list(failures.items())


def truck_failure_rules(payload: FrontEndPayload, truck_id: str) -> list[str]:
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


def primary_rule(payload: FrontEndPayload) -> str:
    failures = constraint_failure_summary(payload)
    if failures and failures[0][0] != "nenhuma":
        return failures[0][0]
    if payload.audit_record and payload.audit_record.fired_rules:
        return payload.audit_record.fired_rules[0]
    return str(payload.decision_status)


def gemma_short_summary(payload: FrontEndPayload) -> str:
    parsed = payload.benchmark_observed.get("parsed_ticket", {})
    parts = [
        parsed.get("load_condition"),
        parsed.get("truck_id"),
        _exception_label_short(payload.gemma_visible_summary.exception_label),
    ]
    visible = [str(part) for part in parts if part]
    if visible:
        return ", ".join(visible[:3])
    return ", ".join(payload.gemma_visible_summary.parsed_fields[:3]) or "campos indisponíveis"


def _exception_label_short(label: str) -> str:
    labels = {
        "RAIN_ON_OPEN_DESTINATION": "chuva em moega aberta",
        "WET_LOAD": "carga úmida",
        "DOCUMENT_BLOCK": "documento bloqueado",
        "MANUAL_REVIEW_HINT": "revisão humana",
        "NO_EXCEPTION": "sem exceção",
    }
    return labels.get(label, label.lower().replace("_", " "))


def ranking_summary(payload: FrontEndPayload) -> str:
    if payload.recommended_truck and payload.recommended_destination:
        return (
            f"{payload.recommended_truck.truck_id} -> "
            f"{payload.recommended_destination.destination_id}; "
            f"{len(payload.queue_diff)} itens no diff da fila."
        )
    return "Sem par recomendado; decisão exige bloqueio ou revisão."


def operator_actions_label(actions: list[Any]) -> str:
    return ", ".join(operator_action_label(str(action)) for action in actions)


def operator_action_label(action: str) -> str:
    labels = {
        "approve": "aprovar",
        "block": "bloquear",
        "override": "sobrescrever",
    }
    return labels.get(action, action)


def reason_detail_label(text: str) -> str:
    translations = {
        "FIFO ordering preserved when possible.": "Ordem de chegada preservada quando possível.",
        "Long wait time increased ranking priority.": "Tempo de espera elevou a prioridade na fila.",
        "FIFO break justified by Long wait time increased ranking priority.": (
            "Quebra de FIFO justificada por tempo de espera e critério verificável."
        ),
    }
    if text in translations:
        return translations[text]
    return text


def story_tile(label: str, value: str, detail: str, kind: str = "muted") -> str:
    return f"""
    <div class="story-tile {kind}">
      <span>{escape(label)}</span>
      <strong>{escape(value)}</strong>
      <p>{escape(detail)}</p>
    </div>
    """


def timeline_item(label: str, status: str, detail: str) -> str:
    return f"""
    <div class="timeline-item {status}">
      <div class="timeline-dot"></div>
      <div>
        <strong>{escape(label)}</strong>
        <p>{escape(detail)}</p>
      </div>
      {chip(status, _status_color(status))}
    </div>
    """


def mini_metric(label: str, value: str) -> str:
    return f"<div><span>{escape(label)}</span><strong>{escape(value)}</strong></div>"


def confidence_value(payload: FrontEndPayload) -> str:
    for note in payload.confidence_notes:
        if note.startswith("parse_confidence="):
            return note.split("=", 1)[1]
    return "n/a"


def percent_label(value: float | int) -> str:
    return f"{round(float(value) * 100):.0f}%"


def _status_color(status: str) -> str:
    if status in {"ok", "ready"}:
        return "green"
    if status in {"blocked", "review"}:
        return "red"
    return "blue"


def display_status(status: str) -> str:
    return status.replace("_", " ")


def status_card(label: str, value: str, note: str) -> str:
    return f"""
    <div class="status-card">
      <span>{escape(label)}</span>
      <strong>{escape(value)}</strong>
      <p>{escape(note)}</p>
    </div>
    """


def chip(text: str, color: str = "") -> str:
    suffix = f" {color}" if color else ""
    return f'<span class="chip{suffix}">{escape(text)}</span>'


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)
