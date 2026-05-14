from __future__ import annotations

from typing import Any

from app.domain.models import FieldEvidence, FieldExtractionResult, ParsedTicket


CRITICAL_FIELDS = ("truck_id", "document_status", "load_condition")


def field_extraction_from_parsed_ticket(
    ticket: ParsedTicket,
    *,
    source: str,
    confidence_threshold: float = 0.70,
) -> FieldExtractionResult:
    raw = ticket.model_dump(mode="json")
    fields = {
        field: FieldEvidence(
            value=raw.get(field),
            confidence=ticket.parse_confidence,
            evidence=list(ticket.evidence_refs),
            source=source,
        )
        for field in raw
        if field not in {"ambiguities", "evidence_refs"}
    }
    weak_fields = [
        field
        for field in CRITICAL_FIELDS
        if _is_missing(raw.get(field)) or ticket.parse_confidence < confidence_threshold
    ]
    needs_review = bool(weak_fields or ticket.ambiguities)
    reason = ""
    if weak_fields:
        reason = "Critical fields missing or below confidence threshold: " + ", ".join(weak_fields)
    elif ticket.ambiguities:
        reason = "Parsed ticket contains ambiguities."
    return FieldExtractionResult(fields=fields, needs_review=needs_review, reason=reason)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in {"", "unknown"}
    return False
