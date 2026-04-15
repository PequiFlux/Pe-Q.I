from __future__ import annotations

from datetime import datetime, timezone

from app.domain.constraints import validate_hard_constraints
from app.domain.enums import DocumentStatus, LoadCondition, VehicleType
from app.domain.models import ParsedTicket, PolicyProfile, QueueRow, QueueSnapshot, ResourceState, WeatherState


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

