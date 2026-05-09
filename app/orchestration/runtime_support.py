from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from app.domain.enums import FlowState, PolicyRule
from app.domain.errors import PequiFluxError
from app.domain.models import (
    AuditRecord,
    DecisionPreview,
    DecisionRequest,
    FrontEndPayload,
    InterpretedContext,
)
from app.services.decision_builder import build_frontend_payload
from app.services.driver_message import compose_driver_message
from app.storage.jsonl_logger import JsonlLogger
from app.storage.sqlite_store import SQLiteStore


def blocked_policy_rules(exc: PequiFluxError) -> list[str]:
    if exc.code in {"NO_ELIGIBLE_CANDIDATE", "EMPTY_VALIDATION_MATRIX"}:
        return [PolicyRule.NO_VALID_PAIR_BLOCKS_AUTODISPATCH]
    return []


def attach_tool_records(
    audit: AuditRecord,
    tool_records: list[dict[str, Any]],
    timers: dict[str, int] | None = None,
) -> AuditRecord:
    payload = audit.model_dump(mode="python")
    payload["tool_calls"] = list(tool_records)
    if timers is not None:
        payload["latencies_ms"] = dict(timers)
    return AuditRecord.model_validate(payload)


def build_source_hashes(request: DecisionRequest) -> dict[str, str]:
    return {
        "queue_csv_ref": _hash_file(request.queue_csv_ref),
        "ticket_ref": _hash_file(request.ticket_ref),
        "operator_note": _hash_text(request.operator_note),
        "weather_state": _hash_json(request.weather_state.model_dump(mode="json")),
        "resource_state": _hash_json(
            [item.model_dump(mode="json") for item in request.resource_state]
        ),
    }


def build_source_hashes_if_available(request: DecisionRequest) -> dict[str, str]:
    try:
        return build_source_hashes(request)
    except PequiFluxError:
        return {}


def finalize_payload(
    *,
    preview: DecisionPreview,
    audit: AuditRecord,
    interpreted_context: InterpretedContext,
    state: FlowState,
    sqlite_store: SQLiteStore | None,
    jsonl_logger: JsonlLogger | None,
) -> FrontEndPayload:
    driver_message = compose_driver_message(
        request_id=preview.request_id,
        decision_status=preview.decision_status,
        recommended_truck=preview.recommended_truck.truck_id if preview.recommended_truck else None,
        recommended_destination=(
            preview.recommended_destination.destination_id
            if preview.recommended_destination
            else None
        ),
        reason_summary=preview.reason_summary,
    )
    payload = build_frontend_payload(
        preview=preview,
        audit=audit,
        driver_message=driver_message,
        interpreted_context=interpreted_context,
    )
    persist_records(sqlite_store, preview, audit)
    log_decision(
        jsonl_logger,
        state=state,
        request_id=preview.request_id,
        scenario_id=preview.scenario_id,
        summary=preview.reason_summary,
    )
    return payload


def persist_records(
    sqlite_store: SQLiteStore | None,
    preview: DecisionPreview,
    audit: AuditRecord,
) -> None:
    if sqlite_store is None:
        return
    sqlite_store.initialize()
    sqlite_store.save_decision(preview)
    sqlite_store.save_audit_record(audit)


def log_decision(
    jsonl_logger: JsonlLogger | None,
    *,
    state: FlowState,
    request_id: str,
    scenario_id: str,
    summary: str,
) -> None:
    if jsonl_logger is None:
        return
    jsonl_logger.write(
        {
            "request_id": request_id,
            "scenario_id": scenario_id,
            "module": "orchestrator",
            "state": state,
            "event_type": "decision_computed",
            "decision_summary": summary,
        }
    )


def _hash_file(path_ref: str) -> str:
    path = Path(path_ref)
    if not path.exists():
        raise PequiFluxError("SOURCE_FILE_NOT_FOUND", f"Source file not found: {path_ref}")
    return _sha256(path.read_bytes())


def _hash_text(value: str) -> str:
    return _sha256(value.encode("utf-8"))


def _hash_json(value: Any) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return _sha256(canonical.encode("utf-8"))


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
