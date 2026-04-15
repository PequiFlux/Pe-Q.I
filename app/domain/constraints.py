from __future__ import annotations

from app.domain.enums import DocumentStatus, LoadCondition
from app.domain.errors import PequiFluxError
from app.domain.models import (
    ConstraintFailure,
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
                and parsed_ticket.load_condition == LoadCondition.WET
                and parsed_ticket.destination_constraints
                and destination_id not in parsed_ticket.destination_constraints
            ):
                failures.append(
                    _fail(
                        "HC-02",
                        "ticket_document",
                        "Wet load requires a compatible destination.",
                    )
                )

            if resource.status in {"down", "blocked"}:
                failures.append(
                    _fail("HC-03", "resource_state", "Destination is down or blocked.")
                )

            if parsed_ticket and (
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

