from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
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
    AuditRecord,
    DecisionPreview,
    ExceptionAssessment,
    FrontEndPayload,
    InterpretedContext,
    ParsedTicket,
    PolicyProfile,
    QueueSnapshot,
    RankedCandidates,
    TruthResolution,
    ValidationResult,
)
from app.domain.policy import load_policy_profiles
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


@dataclass(frozen=True)
class LoadedInputs:
    normalized_queue: QueueSnapshot
    source_hashes: dict[str, str]
    policy_profile: PolicyProfile


@dataclass(frozen=True)
class InterpretedStep:
    interpreted_context: InterpretedContext
    parsed_ticket_for_constraints: ParsedTicket | None


@dataclass(frozen=True)
class RankedStep:
    validation: ValidationResult
    ranking: RankedCandidates


class DecisionOrchestrator:
    def __init__(
        self,
        *,
        gemma_adapter: GemmaAdapter,
        audit_service: AuditService | None = None,
        sqlite_store: SQLiteStore | None = None,
        jsonl_logger: JsonlLogger | None = None,
        policy_profiles: dict[str, PolicyProfile] | None = None,
    ) -> None:
        self.gemma_adapter = gemma_adapter
        self.audit_service = audit_service or AuditService()
        self.sqlite_store = sqlite_store
        self.jsonl_logger = jsonl_logger
        self.policy_profiles = policy_profiles or load_policy_profiles(
            [Path("scenarios/common/policy_profile.json")]
        )

    def run_decision(self, request: DecisionRequest) -> FrontEndPayload:
        state_machine = WorkflowStateMachine()
        timers: dict[str, int] = {}
        source_hashes: dict[str, str] = {}
        try:
            loaded = self.load_inputs(request, state_machine, timers)
            source_hashes = loaded.source_hashes
            interpreted = self.interpret_context(
                request=request,
                loaded=loaded,
                state_machine=state_machine,
                timers=timers,
            )

            if interpreted.interpreted_context.needs_human_review:
                state_machine.transition_to(FlowState.REVIEW_REQUIRED)
                preview, audit = self.build_payload(
                    request=request,
                    loaded=loaded,
                    interpreted=interpreted,
                    ranked=None,
                    timers=timers,
                )
                return self.persist_and_log(
                    preview=preview,
                    audit=audit,
                    interpreted_context=interpreted.interpreted_context,
                    state=state_machine.current_state,
                )

            ranked = self.validate_and_rank(
                request=request,
                loaded=loaded,
                interpreted=interpreted,
                state_machine=state_machine,
                timers=timers,
            )
            preview, audit = self.build_payload(
                request=request,
                loaded=loaded,
                interpreted=interpreted,
                ranked=ranked,
                timers=timers,
            )
            state_machine.transition_to(FlowState.PREVIEW_READY)
            return self.persist_and_log(
                preview=preview,
                audit=audit,
                interpreted_context=interpreted.interpreted_context,
                state=state_machine.current_state,
            )

        except PequiFluxError as exc:
            if not source_hashes:
                source_hashes = _build_source_hashes_if_available(request)
            return self._build_blocked_payload(request, exc, state_machine, timers, source_hashes)

    def load_inputs(
        self,
        request: DecisionRequest,
        state_machine: WorkflowStateMachine,
        timers: dict[str, int],
    ) -> LoadedInputs:
        queue_t0 = perf_counter()
        queue_rows = load_queue_rows(request.queue_csv_ref)
        normalized_queue = normalize_queue_snapshot(
            request_id=request.request_id,
            rows=queue_rows,
            reference_time=request.received_at,
        )
        state_machine.transition_to(FlowState.NORMALIZED)
        timers["normalize_queue_snapshot"] = int((perf_counter() - queue_t0) * 1000)
        return LoadedInputs(
            normalized_queue=normalized_queue,
            source_hashes=_build_source_hashes(request),
            policy_profile=self._policy_profile(request.policy_profile_version),
        )

    def interpret_context(
        self,
        *,
        request: DecisionRequest,
        loaded: LoadedInputs,
        state_machine: WorkflowStateMachine,
        timers: dict[str, int],
    ) -> InterpretedStep:
        candidate_truck_ids = [row.truck_id for row in loaded.normalized_queue.waiting_rows]
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
            queue_snapshot=loaded.normalized_queue,
            gemma_adapter=self.gemma_adapter if request.variant == "full" else None,
        )
        interpreted_context = resolve_truth(
            queue_snapshot=loaded.normalized_queue,
            parsed_ticket=parsed_ticket,
            exception_assessment=exception,
            operator_note=operator_note,
            weather_state=request.weather_state,
            resource_state=request.resource_state,
        )
        state_machine.transition_to(FlowState.INTERPRETED)
        timers["resolve_truth"] = int((perf_counter() - interpreted_t0) * 1000)
        return InterpretedStep(
            interpreted_context=interpreted_context,
            parsed_ticket_for_constraints=parsed_ticket_for_constraints,
        )

    def validate_and_rank(
        self,
        *,
        request: DecisionRequest,
        loaded: LoadedInputs,
        interpreted: InterpretedStep,
        state_machine: WorkflowStateMachine,
        timers: dict[str, int],
    ) -> RankedStep:
        validation_t0 = perf_counter()
        validation = validate_hard_constraints(
            request_id=request.request_id,
            normalized_queue=loaded.normalized_queue,
            parsed_ticket=interpreted.parsed_ticket_for_constraints,
            weather_state=request.weather_state,
            resource_state=request.resource_state,
            candidate_destinations=request.candidate_destinations,
            policy_profile=loaded.policy_profile,
        )
        state_machine.transition_to(FlowState.VALIDATED)
        timers["validate_hard_constraints"] = int((perf_counter() - validation_t0) * 1000)

        ranking_t0 = perf_counter()
        ranking = rank_candidates(
            request_id=request.request_id,
            validation_matrix=validation,
            policy_profile=loaded.policy_profile,
            queue_snapshot=loaded.normalized_queue,
            exception_assessment=interpreted.interpreted_context.exception_assessment,
            resource_state=request.resource_state,
            variant=request.variant,
        )
        state_machine.transition_to(FlowState.RANKED)
        timers["rank_candidates"] = int((perf_counter() - ranking_t0) * 1000)
        return RankedStep(validation=validation, ranking=ranking)

    def build_payload(
        self,
        *,
        request: DecisionRequest,
        loaded: LoadedInputs,
        interpreted: InterpretedStep,
        ranked: RankedStep | None,
        timers: dict[str, int],
    ) -> tuple[DecisionPreview, AuditRecord]:
        if ranked is None:
            preview = build_review_required_preview(
                request_id=request.request_id,
                scenario_id=request.scenario_id,
                variant=request.variant,
                review_reasons=interpreted.interpreted_context.review_reasons,
                queue_snapshot=loaded.normalized_queue,
            )
            validation = None
        else:
            preview = build_decision_preview(
                interpreted_context=interpreted.interpreted_context,
                validation=ranked.validation,
                ranking=ranked.ranking,
                queue_snapshot=loaded.normalized_queue,
                request_id=request.request_id,
                scenario_id=request.scenario_id,
                variant=request.variant,
            )
            validation = ranked.validation

        audit = self.audit_service.generate_audit_payload(
            interpreted_context=interpreted.interpreted_context,
            validation=validation,
            preview=preview,
            latencies_ms=timers,
            source_hashes=loaded.source_hashes,
        )
        return preview, audit

    def persist_and_log(
        self,
        *,
        preview: DecisionPreview,
        audit: AuditRecord,
        interpreted_context: InterpretedContext,
        state: FlowState,
    ) -> FrontEndPayload:
        return self._finalize_payload(
            preview=preview,
            audit=audit,
            interpreted_context=interpreted_context,
            state=state,
        )

    def _build_blocked_payload(
        self,
        request: DecisionRequest,
        exc: PequiFluxError,
        state_machine: WorkflowStateMachine,
        timers: dict[str, int],
        source_hashes: dict[str, str],
    ) -> FrontEndPayload:
        state_machine.current_state = FlowState.BLOCKED
        preview = build_blocked_preview(
            request_id=request.request_id,
            scenario_id=request.scenario_id,
            variant=request.variant,
            reason_summary=exc.message,
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
        audit = self.audit_service.generate_audit_payload(
            interpreted_context=blocked_context,
            validation=None,
            preview=preview,
            latencies_ms=timers,
            source_hashes=source_hashes,
        )
        return self.persist_and_log(
            preview=preview,
            audit=audit,
            interpreted_context=blocked_context,
            state=state_machine.current_state,
        )

    def _policy_profile(self, version: str) -> PolicyProfile:
        profile = self.policy_profiles.get(version)
        if profile is None:
            raise PequiFluxError(
                "UNKNOWN_POLICY_PROFILE",
                f"Unknown policy profile version: {version}",
            )
        return profile

    def _finalize_payload(
        self,
        *,
        preview,
        audit,
        interpreted_context: InterpretedContext,
        state: FlowState,
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
        self._persist(preview, audit)
        self._log(state, preview.request_id, preview.scenario_id, preview.reason_summary)
        return payload

    def _persist(self, preview, audit) -> None:
        if self.sqlite_store is None:
            return
        self.sqlite_store.initialize()
        self.sqlite_store.save_decision(preview)
        self.sqlite_store.save_audit_record(audit)

    def _log(self, state: FlowState, request_id: str, scenario_id: str, summary: str) -> None:
        if self.jsonl_logger is None:
            return
        self.jsonl_logger.write(
            {
                "request_id": request_id,
                "scenario_id": scenario_id,
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


def _build_source_hashes_if_available(request: DecisionRequest) -> dict[str, str]:
    try:
        return _build_source_hashes(request)
    except PequiFluxError:
        return {}


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
