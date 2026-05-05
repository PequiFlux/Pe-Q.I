from __future__ import annotations

from app.domain.enums import DecisionStatus, OperatorAction, PolicyRule
from app.domain.models import (
    AuditRecord,
    DecisionPreview,
    FrontEndPayload,
    GemmaVisibleSummary,
    InterpretedContext,
    QueueDiffEntry,
    QueueSnapshot,
    RankedCandidates,
    RecommendedDestination,
    RecommendedTruck,
    ValidationResult,
)


def _decision_id(request_id: str) -> str:
    return request_id.replace("REQ-", "DEC-")


def _build_queue_diff(
    queue_snapshot: QueueSnapshot,
    top_candidate_truck_id: str | None,
    reason_summary: str,
    blocked_truck_ids: set[str] | None = None,
) -> list[QueueDiffEntry]:
    blocked_truck_ids = blocked_truck_ids or set()
    diff: list[QueueDiffEntry] = []
    selected = next(
        (row for row in queue_snapshot.waiting_rows if row.truck_id == top_candidate_truck_id),
        None,
    )
    selected_position = selected.queue_position if selected else None

    for row in queue_snapshot.waiting_rows:
        is_selected = row.truck_id == top_candidate_truck_id
        if is_selected:
            diff.append(
                QueueDiffEntry(
                    truck_id=row.truck_id,
                    position_before=row.queue_position,
                    position_after=None,
                    decision="called",
                    reason=reason_summary,
                )
            )
        elif selected_position is not None and row.queue_position < selected_position:
            is_blocked = row.truck_id in blocked_truck_ids
            diff.append(
                QueueDiffEntry(
                    truck_id=row.truck_id,
                    position_before=row.queue_position,
                    position_after=row.queue_position,
                    decision="blocked" if is_blocked else "unchanged",
                    reason=(
                        "blocked_by_hard_constraint"
                        if is_blocked
                        else "fifo_break_kept_waiting_ahead_of_called_truck"
                    ),
                )
            )
        else:
            new_position = row.queue_position - (1 if selected_position is not None else 0)
            diff.append(
                QueueDiffEntry(
                    truck_id=row.truck_id,
                    position_before=row.queue_position,
                    position_after=new_position,
                    decision="shifted" if selected_position is not None else "unchanged",
                    reason=(
                        "shifted_after_called_truck_left_queue"
                        if selected_position is not None
                        else "no_dispatch_kept_queue_position"
                    ),
                )
            )
    return diff


def _blocked_truck_ids(validation: ValidationResult, selected_truck_id: str) -> set[str]:
    eligible_by_truck: dict[str, bool] = {}
    for entry in validation.validation_matrix:
        eligible_by_truck[entry.truck_id] = eligible_by_truck.get(entry.truck_id, False) or entry.eligible
    return {
        truck_id
        for truck_id, has_eligible_destination in eligible_by_truck.items()
        if truck_id != selected_truck_id and not has_eligible_destination
    }


def build_decision_preview(
    *,
    interpreted_context: InterpretedContext,
    validation: ValidationResult,
    ranking: RankedCandidates,
    queue_snapshot: QueueSnapshot,
    request_id: str,
    scenario_id: str,
    variant: str,
) -> DecisionPreview:
    top = ranking.top_candidate
    if top is None:
        return build_blocked_preview(
            request_id=request_id,
            scenario_id=scenario_id,
            variant=variant,
            reason_summary="No eligible pair after deterministic validation.",
            fired_rules=[PolicyRule.NO_VALID_PAIR_BLOCKS_AUTODISPATCH],
        )

    constraints = [
        failure
        for entry in validation.validation_matrix
        for failure in entry.failed_constraints
        if entry.truck_id == top.truck_id
    ]
    if top.fifo_break:
        break_reasons = [
            detail
            for detail in top.reason_details
            if "FIFO" not in detail
        ]
        reason_summary = (
            "FIFO break justified by " + "; ".join(break_reasons)
            if break_reasons
            else "FIFO break justified by deterministic ranking among eligible pairs."
        )
    else:
        reason_summary = (
            top.reason_details[0]
            if top.reason_details
            else "Deterministic ranking selected the top eligible pair."
        )
    return DecisionPreview(
        decision_id=_decision_id(request_id),
        request_id=request_id,
        scenario_id=scenario_id,
        variant=variant,
        decision_status=DecisionStatus.PREVIEW_READY,
        recommended_truck=RecommendedTruck(
            truck_id=top.truck_id,
            queue_position_before=top.queue_position,
            queue_position_after=1,
        ),
        recommended_destination=RecommendedDestination(
            destination_id=top.destination_id,
            destination_type="resource",
        ),
        considered_constraints=constraints,
        reason_summary=reason_summary,
        reason_details=top.reason_details,
        operator_actions=[
            OperatorAction.APPROVE,
            OperatorAction.BLOCK,
            OperatorAction.OVERRIDE,
        ],
        queue_diff=_build_queue_diff(
            queue_snapshot,
            top.truck_id,
            reason_summary,
            _blocked_truck_ids(validation, top.truck_id),
        ),
        fired_rules=top.fired_rules,
    )


def build_review_required_preview(
    *,
    request_id: str,
    scenario_id: str,
    variant: str,
    review_reasons: list[str],
    queue_snapshot: QueueSnapshot,
) -> DecisionPreview:
    summary = "Manual review is required before any dispatch decision."
    return DecisionPreview(
        decision_id=_decision_id(request_id),
        request_id=request_id,
        scenario_id=scenario_id,
        variant=variant,
        decision_status=DecisionStatus.REVIEW_REQUIRED,
        reason_summary=summary,
        reason_details=review_reasons,
        operator_actions=[OperatorAction.BLOCK],
        queue_diff=_build_queue_diff(queue_snapshot, None, summary),
    )


def build_blocked_preview(
    *,
    request_id: str,
    scenario_id: str,
    variant: str,
    reason_summary: str,
    fired_rules: list[str] | None = None,
) -> DecisionPreview:
    return DecisionPreview(
        decision_id=_decision_id(request_id),
        request_id=request_id,
        scenario_id=scenario_id,
        variant=variant,
        decision_status=DecisionStatus.BLOCKED,
        reason_summary=reason_summary,
        reason_details=[reason_summary],
        operator_actions=[OperatorAction.BLOCK],
        queue_diff=[],
        fired_rules=fired_rules or [],
    )


def build_frontend_payload(
    *,
    preview: DecisionPreview,
    audit: AuditRecord | None,
    driver_message,
    interpreted_context: InterpretedContext,
) -> FrontEndPayload:
    parsed_ticket = interpreted_context.parsed_ticket
    confidence_notes = [
        f"parse_confidence={parsed_ticket.parse_confidence:.2f}",
        f"document_status={parsed_ticket.document_status}",
        f"load_condition={parsed_ticket.load_condition}",
    ]
    if interpreted_context.needs_human_review:
        confidence_notes.extend(interpreted_context.review_reasons)

    return FrontEndPayload(
        request_id=preview.request_id,
        scenario_id=preview.scenario_id,
        variant=preview.variant,
        decision_status=preview.decision_status,
        recommended_truck=preview.recommended_truck,
        recommended_destination=preview.recommended_destination,
        considered_constraints=preview.considered_constraints,
        reason_summary=preview.reason_summary,
        reason_details=preview.reason_details,
        driver_message=driver_message,
        operator_actions=preview.operator_actions,
        queue_diff=preview.queue_diff,
        gemma_visible_summary=GemmaVisibleSummary(
            parsed_fields=[
                "ticket_id",
                "truck_id",
                "vehicle_type",
                "document_status",
                "load_condition",
            ],
            exception_label=interpreted_context.exception_assessment.primary_exception,
            notes=interpreted_context.review_reasons,
        ),
        latency_ms=audit.latencies_ms if audit else {},
        benchmark_tags=[
            f"scenario:{preview.scenario_id}",
            f"variant:{preview.variant}",
            f"status:{preview.decision_status}",
        ],
        benchmark_observed={
            "parsed_ticket": parsed_ticket.model_dump(mode="json"),
            "primary_exception": interpreted_context.exception_assessment.primary_exception,
            "needs_human_review": interpreted_context.needs_human_review,
        },
        confidence_notes=confidence_notes,
        audit_record=audit,
    )
