from __future__ import annotations

from app.domain.enums import SourceKind, VehicleType
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

TRUSTED_TICKET_CONFIDENCE = 0.75
LOCAL_AUTHORITATIVE_SOURCES = ["queue_snapshot", "weather_state", "resource_state"]


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
    waiting_truck_ids = {row.truck_id for row in queue_snapshot.waiting_rows}
    resource_by_id = {resource.resource_id: resource for resource in resource_state}
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

    if parsed_ticket is not None and parsed_ticket.parse_confidence < TRUSTED_TICKET_CONFIDENCE:
        review_reasons.append("Parsed ticket confidence is below the trusted threshold.")

    if parsed_ticket and parsed_ticket.truck_id and parsed_ticket.truck_id not in waiting_truck_ids:
        material_conflicts.append(
            "Truth hierarchy conflict: queue_snapshot prevails because parsed truck_id is not present in the queue."
        )

    if "chuva" in operator_note.lower() and weather_state.precipitation == "none":
        material_conflicts.append(
            "Truth hierarchy conflict: weather_state prevails because operator note mentions rain but local weather is none."
        )

    if parsed_ticket and parsed_ticket.truck_id:
        row = next((item for item in queue_snapshot.waiting_rows if item.truck_id == parsed_ticket.truck_id), None)
        if row and row.vehicle_type != parsed_ticket.vehicle_type and parsed_ticket.vehicle_type != VehicleType.UNKNOWN:
            material_conflicts.append(
                "Truth hierarchy conflict: queue_snapshot vehicle_type prevails over parsed ticket vehicle_type."
            )
        if row and row.contract_priority_flag != parsed_ticket.contract_priority_flag:
            material_conflicts.append(
                "Truth hierarchy conflict: queue_snapshot contract_priority_flag prevails over parsed ticket flag."
            )

    if parsed_ticket:
        for destination_id in parsed_ticket.destination_constraints:
            resource = resource_by_id.get(destination_id)
            if resource is None:
                material_conflicts.append(
                    "Truth hierarchy conflict: resource_state prevails because parsed destination constraint is unknown."
                )
            elif resource.status in {"down", "blocked"}:
                material_conflicts.append(
                    "Truth hierarchy conflict: resource_state prevails because parsed destination constraint is unavailable."
                )

    if material_conflicts:
        review_reasons.extend(material_conflicts)

    needs_review = exception_assessment.needs_human_review or bool(review_reasons)
    return InterpretedContext(
        parsed_ticket=effective_ticket,
        exception_assessment=exception_assessment,
        truth_resolution=TruthResolution(
            authoritative_sources=[
                *LOCAL_AUTHORITATIVE_SOURCES,
                *(
                    []
                    if parsed_ticket is None or parsed_ticket.parse_confidence < TRUSTED_TICKET_CONFIDENCE
                    else ["ticket_document"]
                ),
                "operator_note",
            ],
            material_conflicts=material_conflicts,
        ),
        provenance=provenance,
        needs_human_review=needs_review,
        review_reasons=review_reasons,
    )
