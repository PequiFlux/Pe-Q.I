from __future__ import annotations

from app.domain.models import (
    ExceptionAssessment,
    InterpretedContext,
    ParsedTicket,
    ProvenanceRecord,
    QueueSnapshot,
    ResourceState,
    TruthResolution,
    WeatherState,
)
from app.domain.enums import SourceKind, VehicleType


def resolve_truth(
    *,
    queue_snapshot: QueueSnapshot,
    parsed_ticket: ParsedTicket | None,
    exception_assessment: ExceptionAssessment,
    operator_note: str,
    weather_state: WeatherState,
    resource_state: list[ResourceState],
) -> InterpretedContext:
    material_conflicts: list[str] = []
    review_reasons: list[str] = []
    provenance = [
        ProvenanceRecord(field="queue_snapshot", source=SourceKind.QUEUE_SNAPSHOT),
        ProvenanceRecord(field="weather_state", source=SourceKind.WEATHER_STATE),
        ProvenanceRecord(field="resource_state", source=SourceKind.RESOURCE_STATE),
        ProvenanceRecord(field="operator_note", source=SourceKind.OPERATOR_NOTE),
    ]
    effective_ticket = parsed_ticket or ParsedTicket(parse_confidence=1.0)

    if parsed_ticket is not None:
        provenance.append(
            ProvenanceRecord(
                field="document_status",
                source=SourceKind.TICKET_DOCUMENT,
                confidence=parsed_ticket.parse_confidence,
            )
        )

    if parsed_ticket is not None and parsed_ticket.parse_confidence < 0.75:
        review_reasons.append("Parsed ticket confidence is below the trusted threshold.")

    if parsed_ticket and parsed_ticket.truck_id and parsed_ticket.truck_id not in {
        row.truck_id for row in queue_snapshot.waiting_rows
    }:
        material_conflicts.append("Parsed truck_id is not present in the queue snapshot.")

    if "chuva" in operator_note.lower() and weather_state.precipitation == "none":
        material_conflicts.append("Operator note mentions rain but weather state does not.")

    if parsed_ticket and parsed_ticket.truck_id:
        row = next((item for item in queue_snapshot.waiting_rows if item.truck_id == parsed_ticket.truck_id), None)
        if row and row.vehicle_type != parsed_ticket.vehicle_type and parsed_ticket.vehicle_type != VehicleType.UNKNOWN:
            material_conflicts.append("Vehicle type differs between queue snapshot and parsed ticket.")

    if material_conflicts:
        review_reasons.extend(material_conflicts)

    needs_review = exception_assessment.needs_human_review or bool(review_reasons)
    return InterpretedContext(
        parsed_ticket=effective_ticket,
        exception_assessment=exception_assessment,
        truth_resolution=TruthResolution(
            authoritative_sources=[
                "queue_snapshot",
                "weather_state",
                "resource_state",
                *([] if parsed_ticket is None else ["ticket_document"]),
            ],
            material_conflicts=material_conflicts,
        ),
        provenance=provenance,
        needs_human_review=needs_review,
        review_reasons=review_reasons,
    )
