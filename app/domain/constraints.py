from __future__ import annotations

from app.domain.enums import DocumentStatus, LoadCondition, OperatorAction
from app.domain.errors import PequiFluxError
from app.domain.models import (
    ConstraintFailure,
    OperatorDecision,
    ParsedTicket,
    PolicyProfile,
    QueueSnapshot,
    ResourceState,
    ValidationEntry,
    ValidationResult,
    WeatherState,
)


def _fail(constraint_id: str, source: str, detail: str) -> ConstraintFailure:
    return ConstraintFailure(
        constraint_id=constraint_id,
        severity="hard",
        source=source,
        detail=detail,
    )


def _ticket_applies_to_row(parsed_ticket: ParsedTicket | None, truck_id: str) -> bool:
    if parsed_ticket is None:
        return False
    if parsed_ticket.truck_id is None:
        return True
    return parsed_ticket.truck_id == truck_id


def validate_override_action(
    *,
    validation: ValidationResult,
    operator_action: OperatorDecision,
) -> None:
    if operator_action.action_type != OperatorAction.OVERRIDE:
        return
    if not operator_action.reason.strip():
        raise PequiFluxError("OVERRIDE_REASON_REQUIRED", "Override requires an explicit reason.")
    if not operator_action.requested_truck_id or not operator_action.requested_destination_id:
        raise PequiFluxError(
            "OVERRIDE_TARGET_REQUIRED",
            "Override requires requested truck and destination ids.",
        )

    entry = next(
        (
            item
            for item in validation.validation_matrix
            if item.truck_id == operator_action.requested_truck_id
            and item.destination_id == operator_action.requested_destination_id
        ),
        None,
    )
    if entry is None:
        raise PequiFluxError("UNKNOWN_OVERRIDE_PAIR", "Override pair is not in the validation matrix.")
    if not entry.eligible:
        failed = ", ".join(failure.constraint_id for failure in entry.failed_constraints)
        raise PequiFluxError(
            "HC_07_OVERRIDE_CANNOT_BYPASS_HARD_CONSTRAINTS",
            f"Override pair is ineligible under hard constraints: {failed}",
        )


def validate_hard_constraints(
    *,
    request_id: str,
    normalized_queue: QueueSnapshot,
    parsed_ticket: ParsedTicket | None,
    weather_state: WeatherState,
    resource_state: list[ResourceState],
    candidate_destinations: list[str],
    policy_profile: PolicyProfile,
) -> ValidationResult:
    resources = {resource.resource_id: resource for resource in resource_state}
    missing_destinations = [
        destination_id for destination_id in candidate_destinations if destination_id not in resources
    ]
    if missing_destinations:
        raise PequiFluxError(
            "UNKNOWN_DESTINATION",
            f"Unknown destinations: {', '.join(sorted(missing_destinations))}",
        )

    matrix: list[ValidationEntry] = []
    global_blocks: list[str] = []
    for row in normalized_queue.waiting_rows:
        for destination_id in candidate_destinations:
            resource = resources[destination_id]
            failures: list[ConstraintFailure] = []

            if weather_state.precipitation != "none" and resource.exposure == "open":
                failures.append(
                    _fail("HC-01", "weather_state", "Open destination blocked by precipitation.")
                )

            if (
                parsed_ticket
                and _ticket_applies_to_row(parsed_ticket, row.truck_id)
                and parsed_ticket.load_condition == LoadCondition.WET
                and (
                    LoadCondition.WET not in resource.supported_load_conditions
                    or (
                        parsed_ticket.destination_constraints
                        and destination_id not in parsed_ticket.destination_constraints
                    )
                )
            ):
                failures.append(
                    _fail(
                        "HC-02",
                        "resource_state",
                        "Wet load requires a compatible destination.",
                    )
                )

            if resource.status in {"down", "blocked"}:
                failures.append(
                    _fail("HC-03", "resource_state", "Destination is down or blocked.")
                )

            if _ticket_applies_to_row(parsed_ticket, row.truck_id) and (
                parsed_ticket.document_status != DocumentStatus.CLEAR
                or parsed_ticket.document_block_flags
            ):
                failures.append(
                    _fail(
                        "HC-04",
                        "ticket_document",
                        "Document status prevents automatic dispatch.",
                    )
                )

            if resource.allowed_vehicle_types and row.vehicle_type not in resource.allowed_vehicle_types:
                failures.append(
                    _fail(
                        "HC-05",
                        "resource_state",
                        "Vehicle type is not allowed for the destination.",
                    )
                )

            if resource.capacity_pct < policy_profile.min_operational_capacity_pct:
                failures.append(
                    _fail(
                        "HC-06",
                        "resource_state",
                        "Destination capacity is below the operational threshold.",
                    )
                )

            matrix.append(
                ValidationEntry(
                    truck_id=row.truck_id,
                    destination_id=destination_id,
                    eligible=not failures,
                    failed_constraints=failures,
                )
            )

    if not matrix:
        global_blocks.append("EMPTY_QUEUE")

    return ValidationResult(
        validation_matrix=matrix,
        global_blocks=global_blocks,
        policy_profile_version=policy_profile.version,
    )
