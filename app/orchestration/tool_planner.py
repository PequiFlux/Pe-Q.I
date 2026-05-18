from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from app.domain.enums import FlowState
from app.domain.errors import PequiFluxError
from app.domain.models import AuditRecord, RankedCandidates, ValidationResult
from app.gemma.adapter import GemmaAdapter
from app.gemma.tool_gateway import ToolGateway, ToolLocalIds, available_tools_for_state
from app.gemma.tool_schemas import TOOL_SCHEMAS
from app.orchestration.state_machine import WorkflowStateMachine
from app.storage.jsonl_logger import JsonlLogger


MAX_TOOL_STEPS = 4


@dataclass(frozen=True)
class ToolExecutionStep:
    tool_name: str
    result: Any


@dataclass
class ToolPlanSession:
    request_id: str
    gemma_adapter: GemmaAdapter
    state_machine: WorkflowStateMachine
    local_ids: ToolLocalIds
    tool_records: list[dict[str, Any]]
    timers: dict[str, int]
    logger: JsonlLogger | None = None
    step_counter: list[int] = field(default_factory=lambda: [0])
    executed_tools: set[str] = field(default_factory=set)


def execute_planned_tool(
    *,
    session: ToolPlanSession,
    tools: dict[str, Callable[..., Any]],
    context_summary: str,
) -> ToolExecutionStep:
    if session.step_counter[0] >= MAX_TOOL_STEPS:
        raise PequiFluxError(
            "MODEL_TOOL_STEP_LIMIT_EXCEEDED",
            f"Gemma tool planner exceeded {MAX_TOOL_STEPS} steps.",
        )

    allowed_tools = available_tools_for_state(session.state_machine.current_state)
    if not allowed_tools:
        raise PequiFluxError(
            "NO_AVAILABLE_TOOLS",
            f"No tools are available in state {session.state_machine.current_state.value}.",
        )

    error_tool_name = allowed_tools[0]
    choose_t0 = perf_counter()
    try:
        intent = session.gemma_adapter.choose_tool(
            request_id=session.request_id,
            current_state=session.state_machine.current_state.value,
            allowed_tools=allowed_tools,
            context_summary=context_summary,
        )
    except PequiFluxError as exc:
        session.timers[f"choose_tool_{error_tool_name}"] = int((perf_counter() - choose_t0) * 1000)
        session.tool_records.append(
            {
                "tool_name": error_tool_name,
                "request_id": session.request_id,
                "state": session.state_machine.current_state.value,
                "status": "error",
                "purpose": "",
                "error_code": exc.code,
            }
        )
        raise

    session.timers[f"choose_tool_{intent.tool_name}"] = int((perf_counter() - choose_t0) * 1000)
    session.tool_records.append(
        {
            "tool_name": intent.tool_name,
            "request_id": intent.request_id,
            "state": session.state_machine.current_state.value,
            "status": "requested",
            "purpose": intent.purpose,
        }
    )

    if intent.tool_name in session.executed_tools:
        session.tool_records.append(
            {
                "tool_name": intent.tool_name,
                "request_id": intent.request_id,
                "state": session.state_machine.current_state.value,
                "status": "error",
                "purpose": intent.purpose,
                "error_code": "MODEL_TOOL_REPEATED",
            }
        )
        raise PequiFluxError(
            "MODEL_TOOL_REPEATED",
            f"Gemma requested repeated tool {intent.tool_name}.",
        )

    session.step_counter[0] += 1
    gateway = ToolGateway(
        tools,
        tool_schemas=TOOL_SCHEMAS,
        current_state=session.state_machine.current_state,
        local_ids=session.local_ids,
        logger=session.logger,
    )

    tool_t0 = perf_counter()
    try:
        result = gateway.execute(
            intent.tool_name,
            {"request_id": intent.request_id},
        )
    except PequiFluxError as exc:
        session.timers[f"tool_{intent.tool_name}"] = int((perf_counter() - tool_t0) * 1000)
        session.tool_records.append(
            {
                "tool_name": intent.tool_name,
                "request_id": intent.request_id,
                "state": session.state_machine.current_state.value,
                "status": "error",
                "purpose": intent.purpose,
                "error_code": exc.code,
            }
        )
        raise

    session.timers[f"tool_{intent.tool_name}"] = int((perf_counter() - tool_t0) * 1000)
    session.tool_records.append(
        {
            "tool_name": intent.tool_name,
            "request_id": intent.request_id,
            "state": session.state_machine.current_state.value,
            "status": "executed",
            "purpose": intent.purpose,
        }
    )
    session.executed_tools.add(intent.tool_name)
    return ToolExecutionStep(tool_name=intent.tool_name, result=result)


def run_validation_and_ranking_plan(
    *,
    session: ToolPlanSession,
    run_validation: Callable[[str], ValidationResult],
    run_ranking: Callable[[str], RankedCandidates],
) -> tuple[ValidationResult, RankedCandidates]:
    validation: ValidationResult | None = None
    ranking: RankedCandidates | None = None
    tools = {
        "validate_hard_constraints": run_validation,
        "rank_candidates": run_ranking,
    }

    while session.state_machine.current_state != FlowState.RANKED:
        if session.state_machine.current_state == FlowState.INTERPRETED:
            timer_key = "validate_hard_constraints"
            context_summary = (
                "Ticket interpreted and truth resolved; hard constraints must be checked "
                "before ranking."
            )
        elif session.state_machine.current_state == FlowState.VALIDATED:
            timer_key = "rank_candidates"
            context_summary = (
                "Hard constraints were validated; ranking may only order eligible pairs."
            )
        else:
            raise PequiFluxError(
                "NO_AVAILABLE_TOOL_STATE",
                f"No decision tool is available in state {session.state_machine.current_state.value}.",
            )

        step_t0 = perf_counter()
        step = execute_planned_tool(
            session=session,
            tools=tools,
            context_summary=context_summary,
        )
        if step.tool_name == "validate_hard_constraints":
            validation = step.result
            session.state_machine.transition_to(FlowState.VALIDATED)
        elif step.tool_name == "rank_candidates":
            ranking = step.result
            session.state_machine.transition_to(FlowState.RANKED)
        else:
            raise PequiFluxError(
                "UNEXPECTED_TOOL_RESULT",
                f"Unexpected tool {step.tool_name} in decision planning.",
            )
        session.timers[timer_key] = int((perf_counter() - step_t0) * 1000)

    if validation is None or ranking is None:
        raise PequiFluxError(
            "INCOMPLETE_TOOL_PLAN",
            "Gemma tool planner did not complete validation and ranking.",
        )
    return validation, ranking


def run_audit_plan(
    *,
    session: ToolPlanSession,
    run_audit: Callable[[str], AuditRecord],
    ranked_present: bool,
) -> AuditRecord:
    context_summary = (
        "Ranking is complete; audit payload must be generated from formal decision artifacts."
        if ranked_present
        else "Human review is required; audit payload must be generated from interpreted context "
        "and formal review artifacts."
    )

    step_t0 = perf_counter()
    step = execute_planned_tool(
        session=session,
        tools={"generate_audit_payload": run_audit},
        context_summary=context_summary,
    )
    if step.tool_name != "generate_audit_payload":
        raise PequiFluxError(
            "UNEXPECTED_TOOL_RESULT",
            f"Unexpected tool {step.tool_name} while generating audit payload.",
        )
    session.timers["generate_audit_payload"] = int((perf_counter() - step_t0) * 1000)
    if session.state_machine.current_state == FlowState.RANKED:
        session.state_machine.transition_to(FlowState.PREVIEW_READY)
    return step.result
