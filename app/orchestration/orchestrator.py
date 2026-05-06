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
from app.domain.enums import FlowState, PolicyRule, Severity
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
from app.gemma.tool_gateway import ToolGateway, ToolLocalIds, available_tools_for_state
from app.gemma.tool_schemas import TOOL_SCHEMAS
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


@dataclass(frozen=True)
class ToolExecutionStep:
    tool_name: str
    result: Any


MAX_TOOL_STEPS = 4


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
        tool_records: list[dict[str, Any]] = []
        tool_step_counter = [0]
        interpreted_context_for_error: InterpretedContext | None = None
        try:
            loaded = self.load_inputs(request, state_machine, timers)
            source_hashes = loaded.source_hashes
            interpreted = self.interpret_context(
                request=request,
                loaded=loaded,
                state_machine=state_machine,
                timers=timers,
            )
            interpreted_context_for_error = interpreted.interpreted_context

            if interpreted.interpreted_context.needs_human_review:
                state_machine.transition_to(FlowState.REVIEW_REQUIRED)
                preview, audit = self.build_payload(
                    request=request,
                    loaded=loaded,
                    interpreted=interpreted,
                    ranked=None,
                    timers=timers,
                    state_machine=state_machine,
                    tool_records=tool_records,
                    tool_step_counter=tool_step_counter,
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
                tool_records=tool_records,
                tool_step_counter=tool_step_counter,
            )
            preview, audit = self.build_payload(
                request=request,
                loaded=loaded,
                interpreted=interpreted,
                ranked=ranked,
                timers=timers,
                state_machine=state_machine,
                tool_records=tool_records,
                tool_step_counter=tool_step_counter,
            )
            if state_machine.current_state == FlowState.RANKED:
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
            return self._build_blocked_payload(
                request,
                exc,
                state_machine,
                timers,
                source_hashes,
                interpreted_context_for_error,
                tool_records,
            )

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
        tool_records: list[dict[str, Any]],
        tool_step_counter: list[int],
    ) -> RankedStep:
        local_ids = ToolLocalIds.from_iterables(
            request_ids={request.request_id},
            truck_ids={row.truck_id for row in loaded.normalized_queue.waiting_rows},
            destination_ids={resource.resource_id for resource in request.resource_state},
        )
        validation: ValidationResult | None = None
        ranking: RankedCandidates | None = None

        def run_validation(request_id: str) -> ValidationResult:
            return validate_hard_constraints(
                request_id=request_id,
                normalized_queue=loaded.normalized_queue,
                parsed_ticket=interpreted.parsed_ticket_for_constraints,
                weather_state=request.weather_state,
                resource_state=request.resource_state,
                candidate_destinations=request.candidate_destinations,
                policy_profile=loaded.policy_profile,
            )

        def run_ranking(request_id: str) -> RankedCandidates:
            if validation is None:
                raise PequiFluxError(
                    "TOOL_PREREQUISITE_MISSING",
                    "Ranking requires validation results.",
                )
            return rank_candidates(
                request_id=request_id,
                validation_matrix=validation,
                policy_profile=loaded.policy_profile,
                queue_snapshot=loaded.normalized_queue,
                exception_assessment=interpreted.interpreted_context.exception_assessment,
                resource_state=request.resource_state,
                variant=request.variant,
            )

        if request.variant != "full":
            validation_t0 = perf_counter()
            validation = run_validation(request.request_id)
            state_machine.transition_to(FlowState.VALIDATED)
            timers["validate_hard_constraints"] = int((perf_counter() - validation_t0) * 1000)
            ranking_t0 = perf_counter()
            ranking = run_ranking(request.request_id)
            state_machine.transition_to(FlowState.RANKED)
            timers["rank_candidates"] = int((perf_counter() - ranking_t0) * 1000)
            return RankedStep(validation=validation, ranking=ranking)

        executed_tools: set[str] = set()
        tools = {
            "validate_hard_constraints": run_validation,
            "rank_candidates": run_ranking,
        }
        while state_machine.current_state != FlowState.RANKED:
            if state_machine.current_state == FlowState.INTERPRETED:
                timer_key = "validate_hard_constraints"
                context_summary = (
                    "Ticket interpreted and truth resolved; hard constraints must be checked "
                    "before ranking."
                )
            elif state_machine.current_state == FlowState.VALIDATED:
                timer_key = "rank_candidates"
                context_summary = (
                    "Hard constraints were validated; ranking may only order eligible pairs."
                )
            else:
                raise PequiFluxError(
                    "NO_AVAILABLE_TOOL_STATE",
                    f"No decision tool is available in state {state_machine.current_state.value}.",
                )

            step_t0 = perf_counter()
            step = self._execute_gemma_tool(
                request_id=request.request_id,
                state_machine=state_machine,
                allowed_tools=available_tools_for_state(state_machine.current_state),
                tools=tools,
                context_summary=context_summary,
                local_ids=local_ids,
                tool_records=tool_records,
                timers=timers,
                tool_step_counter=tool_step_counter,
                executed_tools=executed_tools,
            )
            executed_tools.add(step.tool_name)
            if step.tool_name == "validate_hard_constraints":
                validation = step.result
                state_machine.transition_to(FlowState.VALIDATED)
            elif step.tool_name == "rank_candidates":
                ranking = step.result
                state_machine.transition_to(FlowState.RANKED)
            else:
                raise PequiFluxError(
                    "UNEXPECTED_TOOL_RESULT",
                    f"Unexpected tool {step.tool_name} in decision planning.",
                )
            timers[timer_key] = int((perf_counter() - step_t0) * 1000)

        if validation is None or ranking is None:
            raise PequiFluxError(
                "INCOMPLETE_TOOL_PLAN",
                "Gemma tool planner did not complete validation and ranking.",
            )
        return RankedStep(validation=validation, ranking=ranking)

    def build_payload(
        self,
        *,
        request: DecisionRequest,
        loaded: LoadedInputs,
        interpreted: InterpretedStep,
        ranked: RankedStep | None,
        timers: dict[str, int],
        state_machine: WorkflowStateMachine,
        tool_records: list[dict[str, Any]],
        tool_step_counter: list[int],
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

        local_ids = ToolLocalIds.from_iterables(
            request_ids={request.request_id},
            truck_ids={row.truck_id for row in loaded.normalized_queue.waiting_rows},
            destination_ids={resource.resource_id for resource in request.resource_state},
        )

        def run_audit(request_id: str) -> AuditRecord:
            if request_id != request.request_id:
                raise PequiFluxError(
                    "REQUEST_ID_MISMATCH",
                    "Audit tool request_id mismatch.",
                )
            return self.audit_service.generate_audit_payload(
                interpreted_context=interpreted.interpreted_context,
                validation=validation,
                preview=preview,
                latencies_ms=timers,
                source_hashes=loaded.source_hashes,
            )

        if request.variant == "full":
            context_summary = (
                "Ranking is complete; audit payload must be generated from formal "
                "decision artifacts."
                if ranked is not None
                else "Human review is required; audit payload must be generated from "
                "interpreted context and formal review artifacts."
            )
            step_t0 = perf_counter()
            step = self._execute_gemma_tool(
                request_id=request.request_id,
                state_machine=state_machine,
                allowed_tools=available_tools_for_state(state_machine.current_state),
                tools={"generate_audit_payload": run_audit},
                context_summary=context_summary,
                local_ids=local_ids,
                tool_records=tool_records,
                timers=timers,
                tool_step_counter=tool_step_counter,
                executed_tools={record["tool_name"] for record in tool_records},
            )
            if step.tool_name != "generate_audit_payload":
                raise PequiFluxError(
                    "UNEXPECTED_TOOL_RESULT",
                    f"Unexpected tool {step.tool_name} while generating audit payload.",
                )
            audit = step.result
            timers["generate_audit_payload"] = int((perf_counter() - step_t0) * 1000)
            if state_machine.current_state == FlowState.RANKED:
                state_machine.transition_to(FlowState.PREVIEW_READY)
        else:
            audit = run_audit(request.request_id)
        return preview, _attach_tool_records(audit, tool_records, timers)

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
        interpreted_context: InterpretedContext | None = None,
        tool_records: list[dict[str, Any]] | None = None,
    ) -> FrontEndPayload:
        tool_records = tool_records or []
        state_machine.force_terminal(FlowState.BLOCKED, reason=exc.message)
        preview = build_blocked_preview(
            request_id=request.request_id,
            scenario_id=request.scenario_id,
            variant=request.variant,
            reason_summary=exc.message,
            fired_rules=_blocked_policy_rules(exc),
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
                authoritative_sources=(
                    interpreted_context.truth_resolution.authoritative_sources
                    if interpreted_context is not None
                    else []
                ),
                material_conflicts=[
                    *(
                        interpreted_context.truth_resolution.material_conflicts
                        if interpreted_context is not None
                        else []
                    ),
                    exc.message,
                ],
            ),
            provenance=interpreted_context.provenance if interpreted_context is not None else [],
            needs_human_review=True,
            review_reasons=[
                *(interpreted_context.review_reasons if interpreted_context is not None else []),
                exc.message,
            ],
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
            audit=_attach_tool_records(audit, tool_records, timers),
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
            recommended_truck=(
                preview.recommended_truck.truck_id if preview.recommended_truck else None
            ),
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

    def _execute_gemma_tool(
        self,
        *,
        request_id: str,
        state_machine: WorkflowStateMachine,
        allowed_tools: list[str],
        tools: dict[str, Any],
        context_summary: str,
        local_ids: ToolLocalIds,
        tool_records: list[dict[str, Any]],
        timers: dict[str, int],
        tool_step_counter: list[int],
        executed_tools: set[str],
    ) -> ToolExecutionStep:
        if tool_step_counter[0] >= MAX_TOOL_STEPS:
            raise PequiFluxError(
                "MODEL_TOOL_STEP_LIMIT_EXCEEDED",
                f"Gemma tool planner exceeded {MAX_TOOL_STEPS} steps.",
            )
        if not allowed_tools:
            raise PequiFluxError(
                "NO_AVAILABLE_TOOLS",
                f"No tools are available in state {state_machine.current_state.value}.",
            )
        allowed_label = allowed_tools[0] if len(allowed_tools) == 1 else "planner"
        choose_t0 = perf_counter()
        try:
            intent = self.gemma_adapter.choose_tool(
                request_id=request_id,
                current_state=state_machine.current_state.value,
                allowed_tools=allowed_tools,
                context_summary=context_summary,
            )
        except PequiFluxError as exc:
            timers[f"choose_tool_{allowed_label}"] = int((perf_counter() - choose_t0) * 1000)
            tool_records.append(
                {
                    "tool_name": allowed_label,
                    "request_id": request_id,
                    "state": state_machine.current_state.value,
                    "status": "error",
                    "purpose": "",
                    "error_code": exc.code,
                }
            )
            raise
        timers[f"choose_tool_{intent.tool_name}"] = int((perf_counter() - choose_t0) * 1000)
        tool_records.append(
            {
                "tool_name": intent.tool_name,
                "request_id": intent.request_id,
                "state": state_machine.current_state.value,
                "status": "requested",
                "purpose": intent.purpose,
            }
        )
        if intent.tool_name in executed_tools:
            tool_records.append(
                {
                    "tool_name": intent.tool_name,
                    "request_id": intent.request_id,
                    "state": state_machine.current_state.value,
                    "status": "error",
                    "purpose": intent.purpose,
                    "error_code": "MODEL_TOOL_REPEATED",
                }
            )
            raise PequiFluxError(
                "MODEL_TOOL_REPEATED",
                f"Gemma requested repeated tool {intent.tool_name}.",
            )
        tool_step_counter[0] += 1

        gateway = ToolGateway(
            tools,
            tool_schemas=TOOL_SCHEMAS,
            current_state=state_machine.current_state,
            local_ids=local_ids,
            logger=self.jsonl_logger,
        )
        tool_t0 = perf_counter()
        try:
            result = gateway.execute(
                intent.tool_name,
                {"request_id": intent.request_id},
            )
        except PequiFluxError as exc:
            timers[f"tool_{intent.tool_name}"] = int((perf_counter() - tool_t0) * 1000)
            tool_records.append(
                {
                    "tool_name": intent.tool_name,
                    "request_id": intent.request_id,
                    "state": state_machine.current_state.value,
                    "status": "error",
                    "purpose": intent.purpose,
                    "error_code": exc.code,
                }
            )
            raise
        timers[f"tool_{intent.tool_name}"] = int((perf_counter() - tool_t0) * 1000)

        tool_records.append(
            {
                "tool_name": intent.tool_name,
                "request_id": intent.request_id,
                "state": state_machine.current_state.value,
                "status": "executed",
                "purpose": intent.purpose,
            }
        )
        return ToolExecutionStep(tool_name=intent.tool_name, result=result)


def _build_source_hashes(request: DecisionRequest) -> dict[str, str]:
    return {
        "queue_csv_ref": _hash_file(request.queue_csv_ref),
        "ticket_ref": _hash_file(request.ticket_ref),
        "operator_note": _hash_text(request.operator_note),
        "weather_state": _hash_json(request.weather_state.model_dump(mode="json")),
        "resource_state": _hash_json(
            [item.model_dump(mode="json") for item in request.resource_state]
        ),
    }


def _blocked_policy_rules(exc: PequiFluxError) -> list[str]:
    if exc.code in {"NO_ELIGIBLE_CANDIDATE", "EMPTY_VALIDATION_MATRIX"}:
        return [PolicyRule.NO_VALID_PAIR_BLOCKS_AUTODISPATCH]
    return []


def _attach_tool_records(
    audit: AuditRecord,
    tool_records: list[dict[str, Any]],
    timers: dict[str, int] | None = None,
) -> AuditRecord:
    payload = audit.model_dump(mode="python")
    payload["tool_calls"] = list(tool_records)
    if timers is not None:
        payload["latencies_ms"] = dict(timers)
    return AuditRecord.model_validate(payload)


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
