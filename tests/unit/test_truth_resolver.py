from __future__ import annotations

from datetime import datetime, timezone

from app.domain.enums import DocumentStatus, LoadCondition, Severity, VehicleType
from app.domain.models import (
    ExceptionAssessment,
    ParsedTicket,
    QueueRow,
    QueueSnapshot,
    ResourceState,
    WeatherState,
)
from app.orchestration.truth_resolver import resolve_truth


def _snapshot(*, priority: bool = False) -> QueueSnapshot:
    return QueueSnapshot(
        request_id="REQ-TRUTH",
        rows=[
            QueueRow(
                truck_id="TRK-001",
                arrival_ts=datetime(2026, 4, 15, tzinfo=timezone.utc),
                status="waiting",
                vehicle_type=VehicleType.TRUCK,
                contract_priority_flag=priority,
                queue_position=1,
                wait_minutes=10,
            )
        ],
    )


def _exception() -> ExceptionAssessment:
    return ExceptionAssessment(primary_exception="NO_EXCEPTION", severity=Severity.LOW)


def test_resource_state_prevails_over_parsed_destination_constraint() -> None:
    context = resolve_truth(
        queue_snapshot=_snapshot(),
        parsed_ticket=ParsedTicket(
            truck_id="TRK-001",
            vehicle_type=VehicleType.TRUCK,
            document_status=DocumentStatus.CLEAR,
            load_condition=LoadCondition.DRY,
            destination_constraints=["DST-BLOCKED-01"],
            parse_confidence=0.95,
        ),
        exception_assessment=_exception(),
        operator_note="Destino informado no documento.",
        weather_state=WeatherState(precipitation="none", severity="none"),
        resource_state=[
            ResourceState(
                resource_id="DST-BLOCKED-01",
                status="blocked",
                capacity_pct=0,
                resource_type="hopper",
                exposure="covered",
                allowed_vehicle_types=[VehicleType.TRUCK],
            )
        ],
    )

    assert context.needs_human_review is True
    assert any("resource_state prevails" in item for item in context.truth_resolution.material_conflicts)
    assert context.truth_resolution.authoritative_sources[:3] == [
        "queue_snapshot",
        "weather_state",
        "resource_state",
    ]


def test_weather_state_prevails_over_free_text_rain_note() -> None:
    context = resolve_truth(
        queue_snapshot=_snapshot(),
        parsed_ticket=ParsedTicket(
            truck_id="TRK-001",
            vehicle_type=VehicleType.TRUCK,
            document_status=DocumentStatus.CLEAR,
            load_condition=LoadCondition.DRY,
            parse_confidence=0.95,
        ),
        exception_assessment=_exception(),
        operator_note="Operador relatou chuva no radio.",
        weather_state=WeatherState(precipitation="none", severity="none"),
        resource_state=[],
    )

    assert context.needs_human_review is True
    assert any("weather_state prevails" in item for item in context.truth_resolution.material_conflicts)


def test_queue_snapshot_contract_priority_prevails_over_ticket_flag() -> None:
    context = resolve_truth(
        queue_snapshot=_snapshot(priority=True),
        parsed_ticket=ParsedTicket(
            truck_id="TRK-001",
            vehicle_type=VehicleType.TRUCK,
            document_status=DocumentStatus.CLEAR,
            load_condition=LoadCondition.DRY,
            contract_priority_flag=False,
            parse_confidence=0.95,
        ),
        exception_assessment=_exception(),
        operator_note="Documento sem prioridade.",
        weather_state=WeatherState(precipitation="none", severity="none"),
        resource_state=[],
    )

    assert context.needs_human_review is True
    assert any("queue_snapshot contract_priority_flag prevails" in item for item in context.review_reasons)
