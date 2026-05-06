from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.domain.constraints import validate_hard_constraints, validate_override_action
from app.domain.enums import DocumentStatus, LoadCondition, OperatorAction, VehicleType
from app.domain.errors import PequiFluxError
from app.domain.models import (
    ConstraintFailure,
    OperatorDecision,
    ParsedTicket,
    PolicyProfile,
    QueueRow,
    QueueSnapshot,
    ResourceState,
    ValidationEntry,
    ValidationResult,
    WeatherState,
)


def _policy() -> PolicyProfile:
    return PolicyProfile(
        version="v1-demo",
        min_operational_capacity_pct=20,
        comfort_capacity_pct=50,
        weights={
            "fifo_position": 40,
            "contract_priority": 30,
            "resource_fit": 15,
            "capacity_headroom": 10,
            "wait_sla_pressure": 5,
        },
        tie_breakers=["higher_score"],
    )


def test_open_destination_is_ineligible_under_rain() -> None:
    snapshot = QueueSnapshot(
        request_id="REQ-1",
        rows=[
            QueueRow(
                truck_id="TRK-001",
                arrival_ts=datetime(2026, 4, 15, tzinfo=timezone.utc),
                status="waiting",
                vehicle_type=VehicleType.TRUCK,
                contract_priority_flag=False,
                queue_position=1,
                wait_minutes=10,
            )
        ],
    )
    parsed_ticket = ParsedTicket(
        truck_id="TRK-001",
        vehicle_type=VehicleType.TRUCK,
        document_status=DocumentStatus.CLEAR,
        load_condition=LoadCondition.DRY,
        parse_confidence=0.95,
    )
    result = validate_hard_constraints(
        request_id="REQ-1",
        normalized_queue=snapshot,
        parsed_ticket=parsed_ticket,
        weather_state=WeatherState(precipitation="rain", severity="medium"),
        resource_state=[
            ResourceState(
                resource_id="DST-OPEN-01",
                status="available",
                capacity_pct=70,
                resource_type="hopper",
                exposure="open",
                allowed_vehicle_types=[VehicleType.TRUCK],
            )
        ],
        candidate_destinations=["DST-OPEN-01"],
        policy_profile=_policy(),
    )

    assert result.validation_matrix[0].eligible is False
    assert result.validation_matrix[0].failed_constraints[0].constraint_id == "HC-01"


def test_document_block_applies_only_to_ticket_truck() -> None:
    snapshot = QueueSnapshot(
        request_id="REQ-2",
        rows=[
            QueueRow(
                truck_id="TRK-001",
                arrival_ts=datetime(2026, 4, 15, tzinfo=timezone.utc),
                status="waiting",
                vehicle_type=VehicleType.TRUCK,
                queue_position=1,
                wait_minutes=10,
            ),
            QueueRow(
                truck_id="TRK-002",
                arrival_ts=datetime(2026, 4, 15, 0, 5, tzinfo=timezone.utc),
                status="waiting",
                vehicle_type=VehicleType.TRUCK,
                queue_position=2,
                wait_minutes=5,
            ),
        ],
    )
    parsed_ticket = ParsedTicket(
        truck_id="TRK-001",
        vehicle_type=VehicleType.TRUCK,
        document_status=DocumentStatus.BLOCKED,
        document_block_flags=["missing_weight_stamp"],
        load_condition=LoadCondition.DRY,
        parse_confidence=0.95,
    )

    result = validate_hard_constraints(
        request_id="REQ-2",
        normalized_queue=snapshot,
        parsed_ticket=parsed_ticket,
        weather_state=WeatherState(precipitation="none", severity="none"),
        resource_state=[
            ResourceState(
                resource_id="DST-COV-01",
                status="available",
                capacity_pct=70,
                resource_type="hopper",
                exposure="covered",
                allowed_vehicle_types=[VehicleType.TRUCK],
            )
        ],
        candidate_destinations=["DST-COV-01"],
        policy_profile=_policy(),
    )

    by_truck = {entry.truck_id: entry for entry in result.validation_matrix}
    assert by_truck["TRK-001"].eligible is False
    assert by_truck["TRK-001"].failed_constraints[0].constraint_id == "HC-04"
    assert by_truck["TRK-002"].eligible is True


def test_wet_load_requires_resource_supported_load_condition_without_ticket_destination_hint() -> (
    None
):
    snapshot = QueueSnapshot(
        request_id="REQ-WET",
        rows=[
            QueueRow(
                truck_id="TRK-001",
                arrival_ts=datetime(2026, 4, 15, tzinfo=timezone.utc),
                status="waiting",
                vehicle_type=VehicleType.TRUCK,
                queue_position=1,
                wait_minutes=10,
            )
        ],
    )
    parsed_ticket = ParsedTicket(
        truck_id="TRK-001",
        vehicle_type=VehicleType.TRUCK,
        document_status=DocumentStatus.CLEAR,
        load_condition=LoadCondition.WET,
        destination_constraints=[],
        parse_confidence=0.95,
    )

    result = validate_hard_constraints(
        request_id="REQ-WET",
        normalized_queue=snapshot,
        parsed_ticket=parsed_ticket,
        weather_state=WeatherState(precipitation="none", severity="none"),
        resource_state=[
            ResourceState(
                resource_id="DST-DRY-01",
                status="available",
                capacity_pct=70,
                resource_type="dry_load_hopper",
                exposure="covered",
                allowed_vehicle_types=[VehicleType.TRUCK],
                supported_load_conditions=[LoadCondition.DRY],
            ),
            ResourceState(
                resource_id="DST-WET-01",
                status="available",
                capacity_pct=70,
                resource_type="wet_load_hopper",
                exposure="covered",
                allowed_vehicle_types=[VehicleType.TRUCK],
                supported_load_conditions=[LoadCondition.DRY, LoadCondition.WET],
            ),
        ],
        candidate_destinations=["DST-DRY-01", "DST-WET-01"],
        policy_profile=_policy(),
    )

    by_destination = {entry.destination_id: entry for entry in result.validation_matrix}
    assert by_destination["DST-DRY-01"].eligible is False
    assert by_destination["DST-DRY-01"].failed_constraints[0].constraint_id == "HC-02"
    assert by_destination["DST-WET-01"].eligible is True


def test_wet_load_with_unknown_destination_fails_before_ticket_hint_is_trusted() -> None:
    snapshot = QueueSnapshot(
        request_id="REQ-WET-UNKNOWN",
        rows=[
            QueueRow(
                truck_id="TRK-001",
                arrival_ts=datetime(2026, 4, 15, tzinfo=timezone.utc),
                status="waiting",
                vehicle_type=VehicleType.TRUCK,
                queue_position=1,
                wait_minutes=10,
            )
        ],
    )
    parsed_ticket = ParsedTicket(
        truck_id="TRK-001",
        vehicle_type=VehicleType.TRUCK,
        document_status=DocumentStatus.CLEAR,
        load_condition=LoadCondition.WET,
        destination_constraints=["DST-GHOST-01"],
        parse_confidence=0.95,
    )

    with pytest.raises(PequiFluxError) as exc_info:
        validate_hard_constraints(
            request_id="REQ-WET-UNKNOWN",
            normalized_queue=snapshot,
            parsed_ticket=parsed_ticket,
            weather_state=WeatherState(precipitation="none", severity="none"),
            resource_state=[],
            candidate_destinations=["DST-GHOST-01"],
            policy_profile=_policy(),
        )

    assert exc_info.value.code == "UNKNOWN_DESTINATION"


def test_empty_candidate_destinations_has_specific_error() -> None:
    snapshot = QueueSnapshot(
        request_id="REQ-NO-DESTINATIONS",
        rows=[
            QueueRow(
                truck_id="TRK-001",
                arrival_ts=datetime(2026, 4, 15, tzinfo=timezone.utc),
                status="waiting",
                vehicle_type=VehicleType.TRUCK,
                queue_position=1,
                wait_minutes=10,
            )
        ],
    )

    with pytest.raises(PequiFluxError) as exc_info:
        validate_hard_constraints(
            request_id="REQ-NO-DESTINATIONS",
            normalized_queue=snapshot,
            parsed_ticket=None,
            weather_state=WeatherState(precipitation="none", severity="none"),
            resource_state=[],
            candidate_destinations=[],
            policy_profile=_policy(),
        )

    assert exc_info.value.code == "NO_CANDIDATE_DESTINATIONS"


def test_override_cannot_bypass_hard_constraints() -> None:
    validation = ValidationResult(
        validation_matrix=[
            ValidationEntry(
                truck_id="TRK-001",
                destination_id="DST-OPEN-01",
                eligible=False,
                failed_constraints=[
                    ConstraintFailure(
                        constraint_id="HC-01",
                        severity="hard",
                        source="weather_state",
                        detail="Open destination blocked by precipitation.",
                    )
                ],
            )
        ],
        policy_profile_version="v1-demo",
    )

    with pytest.raises(PequiFluxError, match="HC_07_OVERRIDE"):
        validate_override_action(
            validation=validation,
            operator_action=OperatorDecision(
                action_type=OperatorAction.OVERRIDE,
                actor_id="OP-DEMO-01",
                reason="Force blocked open destination.",
                requested_truck_id="TRK-001",
                requested_destination_id="DST-OPEN-01",
            ),
        )


def test_blocked_resource_remains_ineligible_under_operator_override() -> None:
    snapshot = QueueSnapshot(
        request_id="REQ-BLOCKED-OVERRIDE",
        rows=[
            QueueRow(
                truck_id="TRK-001",
                arrival_ts=datetime(2026, 4, 15, tzinfo=timezone.utc),
                status="waiting",
                vehicle_type=VehicleType.TRUCK,
                queue_position=1,
                wait_minutes=10,
            )
        ],
    )

    validation = validate_hard_constraints(
        request_id="REQ-BLOCKED-OVERRIDE",
        normalized_queue=snapshot,
        parsed_ticket=ParsedTicket(
            truck_id="TRK-001",
            vehicle_type=VehicleType.TRUCK,
            document_status=DocumentStatus.CLEAR,
            load_condition=LoadCondition.DRY,
            parse_confidence=0.95,
        ),
        weather_state=WeatherState(precipitation="none", severity="none"),
        resource_state=[
            ResourceState(
                resource_id="DST-BLOCKED-01",
                status="blocked",
                capacity_pct=80,
                resource_type="hopper",
                exposure="covered",
                allowed_vehicle_types=[VehicleType.TRUCK],
            )
        ],
        candidate_destinations=["DST-BLOCKED-01"],
        policy_profile=_policy(),
    )

    assert validation.validation_matrix[0].failed_constraints[0].constraint_id == "HC-03"
    with pytest.raises(PequiFluxError) as exc_info:
        validate_override_action(
            validation=validation,
            operator_action=OperatorDecision(
                action_type=OperatorAction.OVERRIDE,
                actor_id="OP-DEMO-01",
                reason="Supervisor tentou liberar recurso bloqueado.",
                requested_truck_id="TRK-001",
                requested_destination_id="DST-BLOCKED-01",
            ),
        )

    assert exc_info.value.code == "HC_07_OVERRIDE_CANNOT_BYPASS_HARD_CONSTRAINTS"


def test_override_allows_eligible_pair_with_reason() -> None:
    validation = ValidationResult(
        validation_matrix=[
            ValidationEntry(
                truck_id="TRK-002",
                destination_id="DST-COV-01",
                eligible=True,
            )
        ],
        policy_profile_version="v1-demo",
    )

    validate_override_action(
        validation=validation,
        operator_action=OperatorDecision(
            action_type=OperatorAction.OVERRIDE,
            actor_id="OP-DEMO-01",
            reason="Supervisor selected next eligible pair.",
            requested_truck_id="TRK-002",
            requested_destination_id="DST-COV-01",
        ),
    )
