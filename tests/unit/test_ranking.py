from __future__ import annotations

from datetime import datetime, timezone

from app.domain.enums import PolicyRule, Severity, VehicleType
from app.domain.models import (
    ExceptionAssessment,
    PolicyProfile,
    QueueRow,
    QueueSnapshot,
    ResourceState,
    ValidationEntry,
    ValidationResult,
)
from app.domain.ranking import rank_candidates


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


def test_capacity_between_minimum_and_comfort_penalizes_ranking() -> None:
    snapshot = QueueSnapshot(
        request_id="REQ-CAP",
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
    validation = ValidationResult(
        validation_matrix=[
            ValidationEntry(truck_id="TRK-001", destination_id="DST-LOWCAP-01", eligible=True),
            ValidationEntry(truck_id="TRK-001", destination_id="DST-COMFORT-01", eligible=True),
        ],
        policy_profile_version="v1-demo",
    )

    ranking = rank_candidates(
        request_id="REQ-CAP",
        validation_matrix=validation,
        policy_profile=_policy(),
        queue_snapshot=snapshot,
        exception_assessment=ExceptionAssessment(
            primary_exception="NO_EXCEPTION",
            severity=Severity.LOW,
        ),
        resource_state=[
            ResourceState(
                resource_id="DST-LOWCAP-01",
                status="available",
                capacity_pct=30,
                resource_type="covered_hopper",
                exposure="covered",
                allowed_vehicle_types=[VehicleType.TRUCK],
            ),
            ResourceState(
                resource_id="DST-COMFORT-01",
                status="available",
                capacity_pct=80,
                resource_type="covered_hopper",
                exposure="covered",
                allowed_vehicle_types=[VehicleType.TRUCK],
            ),
        ],
        variant="full",
    )

    assert ranking.candidates[0].destination_id == "DST-COMFORT-01"
    low_capacity = next(
        item for item in ranking.candidates if item.destination_id == "DST-LOWCAP-01"
    )
    assert PolicyRule.REDUCED_CAPACITY_PENALTY in low_capacity.fired_rules
    assert any("Reduced capacity" in detail for detail in low_capacity.reason_details)


def test_full_variant_resource_fit_bonus_is_auditable_policy_rule() -> None:
    snapshot = QueueSnapshot(
        request_id="REQ-FIT",
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
    validation = ValidationResult(
        validation_matrix=[
            ValidationEntry(truck_id="TRK-001", destination_id="DST-COV-01", eligible=True),
        ],
        policy_profile_version="v1-demo",
    )

    ranking = rank_candidates(
        request_id="REQ-FIT",
        validation_matrix=validation,
        policy_profile=_policy(),
        queue_snapshot=snapshot,
        exception_assessment=ExceptionAssessment(
            primary_exception="WET_LOAD",
            severity=Severity.MEDIUM,
            affected_resources=["DST-COV-01"],
        ),
        variant="full",
    )

    candidate = ranking.candidates[0]
    assert PolicyRule.RESOURCE_FIT in candidate.fired_rules
    assert any("active exception context" in detail for detail in candidate.reason_details)
