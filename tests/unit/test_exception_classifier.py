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
from app.services.exception_classifier import classify_exception


class ExceptionRuntime:
    def __init__(self) -> None:
        self.calls = 0

    def generate_structured(self, *, prompt, response_model, metadata):
        self.calls += 1
        return {
            "primary_exception": "AMBIGUOUS_FIELD_REPORT",
            "severity": "medium",
            "ambiguities": ["Operator note requires contextual interpretation."],
            "needs_human_review": True,
        }

    def summarize(self, **kwargs) -> str:
        return "summary"


class Adapter:
    def __init__(self) -> None:
        self.runtime = ExceptionRuntime()

    def classify_exception(self, **kwargs) -> ExceptionAssessment:
        result = self.runtime.generate_structured(
            prompt="classify",
            response_model=ExceptionAssessment,
            metadata={"request_id": kwargs["request_id"]},
        )
        return ExceptionAssessment.model_validate(result)


def _snapshot() -> QueueSnapshot:
    return QueueSnapshot(
        request_id="REQ-EXC",
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


def _ticket() -> ParsedTicket:
    return ParsedTicket(
        truck_id="TRK-001",
        vehicle_type=VehicleType.TRUCK,
        document_status=DocumentStatus.CLEAR,
        load_condition=LoadCondition.DRY,
        parse_confidence=0.95,
        ambiguities=["Unreadable handwritten field."],
    )


def test_exception_classifier_accumulates_combined_operational_exceptions() -> None:
    ticket = ParsedTicket(
        truck_id="TRK-001",
        vehicle_type=VehicleType.TRUCK,
        document_status=DocumentStatus.BLOCKED,
        document_block_flags=["missing_invoice"],
        load_condition=LoadCondition.WET,
        destination_constraints=["DST-COV-01"],
        parse_confidence=0.6,
        ambiguities=["Invoice stamp unreadable."],
    )

    assessment = classify_exception(
        request_id="REQ-EXC",
        parsed_ticket=ticket,
        operator_note="Conferir documento antes de liberar.",
        weather_state=WeatherState(precipitation="rain", severity="high"),
        resource_state=[
            ResourceState(
                resource_id="DST-DOWN-01",
                status="down",
                capacity_pct=0,
                exposure="covered",
                allowed_vehicle_types=[VehicleType.TRUCK],
                supported_load_conditions=[LoadCondition.DRY],
            ),
            ResourceState(
                resource_id="DST-OPEN-01",
                status="available",
                capacity_pct=80,
                exposure="open",
                allowed_vehicle_types=[VehicleType.TRUCK],
                supported_load_conditions=[LoadCondition.DRY],
            ),
            ResourceState(
                resource_id="DST-COV-01",
                status="available",
                capacity_pct=80,
                exposure="covered",
                allowed_vehicle_types=[VehicleType.TRUCK],
                supported_load_conditions=[LoadCondition.WET],
            ),
        ],
        queue_snapshot=_snapshot(),
        gemma_adapter=None,
    )

    assert assessment.primary_exception == "RESOURCE_UNAVAILABLE"
    assert assessment.secondary_exceptions == [
        "RAIN_ON_OPEN_DESTINATION",
        "DOCUMENT_BLOCK",
        "MANUAL_REVIEW_HINT",
        "WET_LOAD",
    ]
    assert assessment.severity == Severity.HIGH
    assert assessment.affected_resources == ["DST-DOWN-01", "DST-OPEN-01", "DST-COV-01"]
    assert assessment.ambiguities == ["Invoice stamp unreadable."]
    assert assessment.needs_human_review is True


def test_rain_on_open_destination_keeps_document_block_secondary() -> None:
    ticket = ParsedTicket(
        truck_id="TRK-001",
        vehicle_type=VehicleType.TRUCK,
        document_status=DocumentStatus.BLOCKED,
        document_block_flags=["missing_invoice"],
        load_condition=LoadCondition.DRY,
        parse_confidence=0.95,
    )

    assessment = classify_exception(
        request_id="REQ-RAIN-DOC",
        parsed_ticket=ticket,
        operator_note="Documento bloqueado; destino aberto esta sob chuva.",
        weather_state=WeatherState(precipitation="rain", severity="medium"),
        resource_state=[
            ResourceState(
                resource_id="DST-OPEN-01",
                status="available",
                capacity_pct=80,
                exposure="open",
                allowed_vehicle_types=[VehicleType.TRUCK],
                supported_load_conditions=[LoadCondition.DRY],
            )
        ],
        queue_snapshot=_snapshot(),
        gemma_adapter=None,
    )

    assert assessment.primary_exception == "RAIN_ON_OPEN_DESTINATION"
    assert assessment.secondary_exceptions == ["DOCUMENT_BLOCK"]
    assert assessment.affected_resources == ["DST-OPEN-01"]
    assert assessment.needs_human_review is False


def test_ambiguous_exception_uses_gemma_adapter_when_available() -> None:
    adapter = Adapter()

    assessment = classify_exception(
        request_id="REQ-EXC",
        parsed_ticket=_ticket(),
        operator_note="Relato ambíguo de campo; avaliar exceção.",
        weather_state=WeatherState(precipitation="none", severity="none"),
        resource_state=[],
        queue_snapshot=_snapshot(),
        gemma_adapter=adapter,  # type: ignore[arg-type]
    )

    assert adapter.runtime.calls == 1
    assert assessment.primary_exception == "AMBIGUOUS_FIELD_REPORT"
    assert assessment.needs_human_review is True


def test_contextual_adapter_result_keeps_primary_and_receives_deterministic_secondaries() -> None:
    adapter = Adapter()
    ticket = ParsedTicket(
        truck_id="TRK-001",
        vehicle_type=VehicleType.TRUCK,
        document_status=DocumentStatus.CLEAR,
        load_condition=LoadCondition.WET,
        destination_constraints=["DST-COV-01"],
        parse_confidence=0.95,
        ambiguities=["Unreadable handwritten field."],
    )

    assessment = classify_exception(
        request_id="REQ-EXC",
        parsed_ticket=ticket,
        operator_note="Relato ambíguo de campo; avaliar exceção.",
        weather_state=WeatherState(precipitation="none", severity="none"),
        resource_state=[],
        queue_snapshot=_snapshot(),
        gemma_adapter=adapter,  # type: ignore[arg-type]
    )

    assert assessment.primary_exception == "AMBIGUOUS_FIELD_REPORT"
    assert assessment.secondary_exceptions == ["WET_LOAD"]
    assert assessment.affected_resources == ["DST-COV-01"]
    assert assessment.ambiguities == [
        "Operator note requires contextual interpretation.",
        "Unreadable handwritten field.",
    ]


def test_ambiguous_exception_without_gemma_stays_deterministic_review_hint() -> None:
    assessment = classify_exception(
        request_id="REQ-EXC",
        parsed_ticket=_ticket(),
        operator_note="Relato ambíguo de campo; avaliar exceção.",
        weather_state=WeatherState(precipitation="none", severity="none"),
        resource_state=[],
        queue_snapshot=_snapshot(),
        gemma_adapter=None,
    )

    assert assessment.primary_exception == "NO_EXCEPTION"
    assert assessment.severity == Severity.LOW
