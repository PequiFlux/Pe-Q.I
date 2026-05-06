from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

from app.domain.enums import DocumentStatus, LoadCondition, Severity
from app.domain.models import (
    ExceptionAssessment,
    ParsedTicket,
    QueueSnapshot,
    ResourceState,
    WeatherState,
)
from app.gemma.adapter import GemmaAdapter

_HIGH_PRIORITY_STATUSES = {"down", "blocked"}
_Item = TypeVar("_Item")


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
    findings: list[tuple[str, Severity, list[str]]] = []
    affected_resources: list[str] = []
    ambiguities = list(parsed_ticket.ambiguities) if parsed_ticket else []
    needs_human_review = False

    unavailable_resources = [
        resource.resource_id
        for resource in resource_state
        if resource.status in _HIGH_PRIORITY_STATUSES
    ]
    if unavailable_resources:
        findings.append(("RESOURCE_UNAVAILABLE", Severity.HIGH, unavailable_resources))
        affected_resources.extend(unavailable_resources)

    open_resources_under_rain = [
        resource.resource_id
        for resource in resource_state
        if weather_state.precipitation != "none" and resource.exposure == "open"
    ]
    if open_resources_under_rain:
        findings.append(("RAIN_ON_OPEN_DESTINATION", Severity.HIGH, open_resources_under_rain))
        affected_resources.extend(open_resources_under_rain)

    if parsed_ticket and parsed_ticket.document_status != DocumentStatus.CLEAR:
        findings.append(("DOCUMENT_BLOCK", Severity.HIGH, []))
        needs_human_review = needs_human_review or parsed_ticket.parse_confidence < 0.75

    if "revis" in note or "confer" in note:
        findings.append(("MANUAL_REVIEW_HINT", Severity.MEDIUM, []))

    if parsed_ticket and parsed_ticket.load_condition == LoadCondition.WET:
        constrained_resources = list(parsed_ticket.destination_constraints)
        findings.append(("WET_LOAD", Severity.MEDIUM, constrained_resources))
        affected_resources.extend(constrained_resources)

    has_high_priority_finding = any(severity == Severity.HIGH for _, severity, _ in findings)
    if (
        _requires_contextual_classification(note, parsed_ticket)
        and gemma_adapter is not None
        and not has_high_priority_finding
    ):
        assessment = gemma_adapter.classify_exception(
            request_id=request_id,
            parsed_ticket=parsed_ticket,
            operator_note=operator_note,
            weather_state=weather_state,
            resource_state=resource_state,
            queue_snapshot=queue_snapshot,
        )
        return _merge_assessment(
            assessment, findings, affected_resources, ambiguities, needs_human_review
        )

    if findings:
        primary_exception, severity, _ = findings[0]
        return ExceptionAssessment(
            primary_exception=primary_exception,
            secondary_exceptions=_unique(name for name, _, _ in findings[1:]),
            severity=severity,
            affected_resources=_unique(affected_resources),
            ambiguities=_unique(ambiguities),
            needs_human_review=needs_human_review or _has_manual_review_hint(findings),
        )

    return ExceptionAssessment(
        primary_exception="NO_EXCEPTION",
        severity=Severity.LOW,
        secondary_exceptions=[],
        affected_resources=[],
        ambiguities=[],
        needs_human_review=False,
    )


def _merge_assessment(
    assessment: ExceptionAssessment,
    findings: list[tuple[str, Severity, list[str]]],
    affected_resources: list[str],
    ambiguities: list[str],
    needs_human_review: bool,
) -> ExceptionAssessment:
    return assessment.model_copy(
        update={
            "secondary_exceptions": _unique(
                [
                    *assessment.secondary_exceptions,
                    *(name for name, _, _ in findings if name != assessment.primary_exception),
                ]
            ),
            "affected_resources": _unique([*assessment.affected_resources, *affected_resources]),
            "ambiguities": _unique([*assessment.ambiguities, *ambiguities]),
            "needs_human_review": (
                assessment.needs_human_review
                or needs_human_review
                or _has_manual_review_hint(findings)
            ),
        }
    )


def _has_manual_review_hint(findings: list[tuple[str, Severity, list[str]]]) -> bool:
    return any(name == "MANUAL_REVIEW_HINT" for name, _, _ in findings)


def _unique(items: Iterable[_Item]) -> list[_Item]:
    return list(dict.fromkeys(items))


def _requires_contextual_classification(note: str, parsed_ticket: ParsedTicket | None) -> bool:
    ambiguous_terms = {"ambig", "duvid", "incert", "verificar", "avaliar", "anomalia"}
    return bool(
        any(term in note for term in ambiguous_terms)
        or (parsed_ticket and parsed_ticket.ambiguities)
    )
