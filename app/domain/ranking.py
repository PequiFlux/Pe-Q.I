from __future__ import annotations

from math import isclose

from app.domain.enums import PolicyRule
from app.domain.errors import PequiFluxError
from app.domain.models import (
    DecisionVariant,
    ExceptionAssessment,
    PolicyProfile,
    QueueSnapshot,
    RankedCandidate,
    RankedCandidates,
    ResourceState,
    ValidationResult,
)


def rank_candidates(
    *,
    request_id: str,
    validation_matrix: ValidationResult,
    policy_profile: PolicyProfile,
    queue_snapshot: QueueSnapshot,
    exception_assessment: ExceptionAssessment,
    resource_state: list[ResourceState] | None = None,
    variant: DecisionVariant = "full",
) -> RankedCandidates:
    if not validation_matrix.validation_matrix:
        raise PequiFluxError("EMPTY_VALIDATION_MATRIX", "No validation entries were generated.")

    queue_index = {row.truck_id: row for row in queue_snapshot.waiting_rows}
    resource_index = {resource.resource_id: resource for resource in resource_state or []}
    max_position = max((row.queue_position for row in queue_snapshot.waiting_rows), default=1)
    candidates: list[RankedCandidate] = []

    for entry in validation_matrix.validation_matrix:
        if not entry.eligible:
            continue
        row = queue_index[entry.truck_id]
        score = 0.0
        fired_rules: list[str] = []
        reason_details: list[str] = []

        fifo_component = (max_position - row.queue_position + 1) / max_position
        score += fifo_component * policy_profile.weights.fifo_position
        fired_rules.append(PolicyRule.FIFO_DEFAULT)
        reason_details.append("FIFO ordering preserved when possible.")

        if variant in {"heuristic", "full"} and row.contract_priority_flag:
            score += policy_profile.weights.contract_priority
            fired_rules.append(PolicyRule.CONTRACT_PRIORITY_MAY_BREAK_FIFO)
            reason_details.append("Contract priority published in the queue snapshot.")

        if variant == "full" and entry.destination_id in exception_assessment.affected_resources:
            score += policy_profile.weights.resource_fit
            fired_rules.append(PolicyRule.RESOURCE_FIT)
            reason_details.append("Destination matches the active exception context.")

        wait_pressure = 0.0
        if variant in {"heuristic", "full"}:
            wait_pressure = (
                min(row.wait_minutes / 120, 1.0) * policy_profile.weights.wait_sla_pressure
            )
        if not isclose(wait_pressure, 0.0):
            score += wait_pressure
            fired_rules.append(PolicyRule.WAIT_SLA_PRESSURE)
            reason_details.append("Long wait time increased ranking priority.")

        capacity_penalty = 0.0
        resource = resource_index.get(entry.destination_id)
        if (
            variant in {"heuristic", "full"}
            and resource is not None
            and policy_profile.min_operational_capacity_pct
            <= resource.capacity_pct
            < policy_profile.comfort_capacity_pct
        ):
            capacity_gap = policy_profile.comfort_capacity_pct - resource.capacity_pct
            comfort_band = (
                policy_profile.comfort_capacity_pct - policy_profile.min_operational_capacity_pct
            )
            capacity_penalty = (
                capacity_gap / comfort_band
            ) * policy_profile.weights.capacity_headroom
        if not isclose(capacity_penalty, 0.0):
            score -= capacity_penalty
            fired_rules.append(PolicyRule.REDUCED_CAPACITY_PENALTY)
            reason_details.append("Reduced capacity lowered ranking priority.")

        fifo_break = row.queue_position != 1
        candidates.append(
            RankedCandidate(
                truck_id=entry.truck_id,
                destination_id=entry.destination_id,
                score=round(score, 3),
                queue_position=row.queue_position,
                arrival_ts=row.arrival_ts,
                fired_rules=fired_rules,
                fifo_break=fifo_break,
                reason_details=reason_details,
            )
        )

    if not candidates:
        raise PequiFluxError("NO_ELIGIBLE_CANDIDATE", "No eligible candidate was produced.")

    candidates.sort(
        key=lambda item: (
            -item.score,
            item.queue_position,
            item.arrival_ts,
            item.truck_id,
            item.destination_id,
        )
    )
    return RankedCandidates(candidates=candidates)
