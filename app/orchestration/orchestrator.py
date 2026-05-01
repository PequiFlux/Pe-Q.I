from __future__ import annotations

import hashlib
import json
from pathlib import Path
from time import perf_counter
from typing import Any

from app.adapters.csv_adapter import load_queue_rows, normalize_queue_snapshot
from app.adapters.note_adapter import sanitize_operator_note
from app.audit.service import AuditService
from app.domain.constraints import validate_hard_constraints
from app.domain.enums import FlowState, Severity
from app.domain.errors import PequiFluxError
from app.domain.models import (
    DecisionRequest,
    ExceptionAssessment,
    FrontEndPayload,
    InterpretedContext,
    ParsedTicket,
    TruthResolution,
)
from app.domain.policy import DEFAULT_POLICY
from app.domain.ranking import rank_candidates
from app.gemma.adapter import GemmaAdapter
from app.orchestration.state_machine import WorkflowStateMachine
from app.orchestration.truth_resolver import resolve_truth
from app.services.decision_builder import (
    build_blocked_preview,
    build_decision_preview,
    build_frontend_payload,
    build_review_required_preview,
)
from app.services.driver_message import compose_driver_message
from app.services.exception_classifier import classify_exception
from app.services.parser import parse_ticket_document
from app.services.structured_ticket_parser import parse_structured_ticket_document
from app.storage.jsonl_logger import JsonlLogger
from app.storage.sqlite_store import SQLiteStore


class DecisionOrchestrator:
    def __init__(
        self,
        *,
        gemma_adapter: GemmaAdapter,
        audit_service: AuditService | None = None,
        sqlite_store: SQLiteStore | None = None,
        jsonl_logger: JsonlLogger | None = None,
    ) -> None:
        self.gemma_adapter = gemma_adapter
        self.audit_service = audit_service or AuditService()
        self.sqlite_store = sqlite_store
        self.jsonl_logger = jsonl_logger

    def run_decision(self, request: DecisionRequest) -> FrontEndPayload:
        state_machine = WorkflowStateMachine()
        timers: dict[str, int] = {}
        try:
            queue_t0 = perf_counter()
            queue_rows = load_queue_rows(request.queue_csv_ref)
            normalized_queue = normalize_queue_snapshot(
                request_id=request.request_id,
                rows=queue_rows,
                reference_time=request.received_at,
            )
            state_machine.transition_to(FlowState.NORMALIZED)
            timers["normalize_queue_snapshot"] = int((perf_counter() - queue_t0) * 1000)

            source_hashes = _build_source_hashes(request)

            candidate_truck_ids = [row.truck_id for row in normalized_queue.waiting_rows]
            parsed_ticket: ParsedTicket | None = None
            parsed_ticket_for_constraints: ParsedTicket | None = None
            if request.variant == "fifo":
                state_machine.transition_to(FlowState.PARSED)
            elif request.variant == "heuristic":
                parse_t0 = perf_counter()
                parsed_ticket = parse_structured_ticket_document(
                    request_id=request.request_id,
                    document_ref=request.ticket_ref,
                    content_type=request.ticket_content_type,
                    candidate_truck_ids=candidate_truck_ids,
                )
                parsed_ticket_for_constraints = parsed_ticket
                state_machine.transition_to(FlowState.PARSED)
                timers["parse_structured_ticket_document"] = int((perf_counter() - parse_t0) * 1000)
            else:
                parse_t0 = perf_counter()
                parsed_ticket = parse_ticket_document(
                    request_id=request.request_id,
                    document_ref=request.ticket_ref,
                    content_type=request.ticket_content_type,
                    candidate_truck_ids=candidate_truck_ids,
                    gemma_adapter=self.gemma_adapter,
                )
                parsed_ticket_for_constraints = parsed_ticket
                state_machine.transition_to(FlowState.PARSED)
                timers["parse_ticket_document"] = int((perf_counter() - parse_t0) * 1000)

            interpreted_t0 = perf_counter()
            operator_note = sanitize_operator_note(request.operator_note)
            exception = classify_exception(
                request_id=request.request_id,
                parsed_ticket=parsed_ticket,
                operator_note=operator_note,
                weather_state=request.weather_state,
                resource_state=request.resource_state,
                queue_snapshot=normalized_queue,
            )
            interpreted_context = resolve_truth(
                queue_snapshot=normalized_queue,
                parsed_ticket=parsed_ticket,
                exception_assessment=exception,
                operator_note=operator_note,
                weather_state=request.weather_state,
                resource_state=request.resource_state,
            )
            state_machine.transition_to(FlowState.INTERPRETED)
            timers["resolve_truth"] = int((perf_counter() - interpreted_t0) * 1000)

            if interpreted_context.needs_human_review:
                preview = build_review_required_preview(
                    request_id=request.request_id,
                    scenario_id=request.scenario_id,
                    variant=request.variant,
                    review_reasons=interpreted_context.review_reasons,
                    queue_snapshot=normalized_queue,
                )
                driver_message = compose_driver_message(
                    request_id=request.request_id,
                    decision_status=preview.decision_status,
                    recommended_truck=None,
                    recommended_destination=None,
                    reason_summary=preview.reason_summary,
                )
                audit = self.audit_service.generate_audit_payload(
                    interpreted_context=interpreted_context,
                    validation=None,
                    preview=preview,
                    latencies_ms=timers,
                    source_hashes=source_hashes,
                )
                state_machine.transition_to(FlowState.REVIEW_REQUIRED)
                return build_frontend_payload(
                    preview=preview,
                    audit=audit,
                    driver_message=driver_message,
                    interpreted_context=interpreted_context,
                )

            validation_t0 = perf_counter()
            validation = validate_hard_constraints(
                request_id=request.request_id,
                normalized_queue=normalized_queue,
                parsed_ticket=parsed_ticket_for_constraints,
                weather_state=request.weather_state,
                resource_state=request.resource_state,
                candidate_destinations=request.candidate_destinations,
                policy_profile=DEFAULT_POLICY,
            )
            state_machine.transition_to(FlowState.VALIDATED)
            timers["validate_hard_constraints"] = int((perf_counter() - validation_t0) * 1000)

            ranking_t0 = perf_counter()
            ranking = rank_candidates(
                request_id=request.request_id,
                validation_matrix=validation,
                policy_profile=DEFAULT_POLICY,
                queue_snapshot=normalized_queue,
                exception_assessment=interpreted_context.exception_assessment,
                resource_state=request.resource_state,
                variant=request.variant,
            )
            state_machine.transition_to(FlowState.RANKED)
            timers["rank_candidates"] = int((perf_counter() - ranking_t0) * 1000)

            preview = build_decision_preview(
                interpreted_context=interpreted_context,
                validation=validation,
                ranking=ranking,
                queue_snapshot=normalized_queue,
                request_id=request.request_id,
                scenario_id=request.scenario_id,
                variant=request.variant,
            )
            state_machine.transition_to(FlowState.PREVIEW_READY)

            audit = self.audit_service.generate_audit_payload(
                interpreted_context=interpreted_context,
                validation=validation,
                preview=preview,
                latencies_ms=timers,
                source_hashes=source_hashes,
            )
            driver_message = compose_driver_message(
                request_id=request.request_id,
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
            self._persist(preview, audit)
            self._log(state_machine.current_state, request, payload.reason_summary)
            return payload

        except PequiFluxError as exc:
            state_machine.current_state = FlowState.BLOCKED
            preview = build_blocked_preview(
                request_id=request.request_id,
                scenario_id=request.scenario_id,
                variant=request.variant,
                reason_summary=exc.message,
            )
            driver_message = compose_driver_message(
                request_id=request.request_id,
                decision_status=preview.decision_status,
                recommended_truck=None,
                recommended_destination=None,
                reason_summary=preview.reason_summary,
            )
            blocked_context = InterpretedContext(
                parsed_ticket=ParsedTicket(),
                exception_assessment=ExceptionAssessment(
                    primary_exception="SYSTEM_BLOCK",
                    severity=Severity.HIGH,
                    needs_human_review=True,
                    ambiguities=[exc.message],
                ),
                truth_resolution=TruthResolution(
                    authoritative_sources=[],
                    material_conflicts=[exc.message],
                ),
                provenance=[],
                needs_human_review=True,
                review_reasons=[exc.message],
            )
            self._log(state_machine.current_state, request, exc.message)
            return build_frontend_payload(
                preview=preview,
                audit=None,
                driver_message=driver_message,
                interpreted_context=blocked_context,
            )

    def _persist(self, preview, audit) -> None:
        if self.sqlite_store is None:
            return
        self.sqlite_store.initialize()
        self.sqlite_store.save_decision(preview)
        self.sqlite_store.save_audit_record(audit)

    def _log(self, state: FlowState, request: DecisionRequest, summary: str) -> None:
        if self.jsonl_logger is None:
            return
        self.jsonl_logger.write(
            {
                "request_id": request.request_id,
                "scenario_id": request.scenario_id,
                "module": "orchestrator",
                "state": state,
                "event_type": "decision_computed",
                "decision_summary": summary,
            }
        )


def _build_source_hashes(request: DecisionRequest) -> dict[str, str]:
    return {
        "queue_csv_ref": _hash_file(request.queue_csv_ref),
        "ticket_ref": _hash_file(request.ticket_ref),
        "operator_note": _hash_text(request.operator_note),
        "weather_state": _hash_json(request.weather_state.model_dump(mode="json")),
        "resource_state": _hash_json([item.model_dump(mode="json") for item in request.resource_state]),
    }


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
