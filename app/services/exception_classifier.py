from __future__ import annotations

from app.domain.enums import DocumentStatus, LoadCondition, Severity
from app.domain.models import ExceptionAssessment, ParsedTicket, QueueSnapshot, ResourceState, WeatherState
from app.gemma.adapter import GemmaAdapter


def classify_exception(
    *,
    request_id: str,
    parsed_ticket: ParsedTicket | None,
    operator_note: str,
    weather_state: WeatherState,
    resource_state: list[ResourceState],
    queue_snapshot: QueueSnapshot,
    gemma_adapter: GemmaAdapter | None = None,
) -> ExceptionAssessment:
    note = operator_note.lower()

    if any(resource.status in {"down", "blocked"} for resource in resource_state):
        return ExceptionAssessment(
            primary_exception="RESOURCE_UNAVAILABLE",
            severity=Severity.HIGH,
            affected_resources=[resource.resource_id for resource in resource_state if resource.status in {"down", "blocked"}],
        )

    if weather_state.precipitation != "none" and any(resource.exposure == "open" for resource in resource_state):
        return ExceptionAssessment(
            primary_exception="RAIN_ON_OPEN_DESTINATION",
            severity=Severity.HIGH,
            affected_resources=[resource.resource_id for resource in resource_state if resource.exposure == "open"],
        )

    if parsed_ticket and parsed_ticket.document_status != DocumentStatus.CLEAR:
        return ExceptionAssessment(
            primary_exception="DOCUMENT_BLOCK",
            severity=Severity.HIGH,
            ambiguities=list(parsed_ticket.ambiguities),
            needs_human_review=parsed_ticket.parse_confidence < 0.75,
        )

    if _requires_contextual_classification(note, parsed_ticket) and gemma_adapter is not None:
        return gemma_adapter.classify_exception(
            request_id=request_id,
            parsed_ticket=parsed_ticket,
            operator_note=operator_note,
            weather_state=weather_state,
            resource_state=resource_state,
            queue_snapshot=queue_snapshot,
        )

    if "revis" in note or "confer" in note:
        return ExceptionAssessment(
            primary_exception="MANUAL_REVIEW_HINT",
            severity=Severity.MEDIUM,
            needs_human_review=True,
        )

    if parsed_ticket and parsed_ticket.load_condition == LoadCondition.WET:
        return ExceptionAssessment(
            primary_exception="WET_LOAD",
            severity=Severity.MEDIUM,
            affected_resources=list(parsed_ticket.destination_constraints),
        )

    return ExceptionAssessment(
        primary_exception="NO_EXCEPTION",
        severity=Severity.LOW,
        secondary_exceptions=[],
        affected_resources=[],
        ambiguities=[],
        needs_human_review=False,
    )


def _requires_contextual_classification(note: str, parsed_ticket: ParsedTicket | None) -> bool:
    ambiguous_terms = {"ambig", "duvid", "incert", "verificar", "avaliar", "anomalia"}
    return bool(
        any(term in note for term in ambiguous_terms)
        or (parsed_ticket and parsed_ticket.ambiguities)
    )
