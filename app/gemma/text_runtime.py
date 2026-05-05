from __future__ import annotations

from typing import Any

from app.domain.errors import PequiFluxError
from app.domain.models import ExceptionAssessment, ParsedTicket
from app.services.structured_ticket_parser import (
    load_expected_ticket_fixture,
    parse_structured_ticket_text,
)


class TextTicketRuntime:
    """Deterministic runtime for CI fixtures, including multimodal sidecars."""

    def generate_structured(
        self,
        *,
        prompt: str,
        response_model: type,
        metadata: dict[str, Any],
    ) -> ParsedTicket | ExceptionAssessment:
        if response_model is ExceptionAssessment:
            return ExceptionAssessment(
                primary_exception="MANUAL_REVIEW_HINT",
                severity="medium",
                ambiguities=["Text runtime classified ambiguous exception fixture."],
                needs_human_review=True,
            )
        if response_model is not ParsedTicket:
            raise PequiFluxError("UNSUPPORTED_SCHEMA", "TextTicketRuntime only emits ParsedTicket.")
        return _fixture_ticket_from_metadata(metadata)

    def summarize(self, *, prompt: str, metadata: dict[str, Any]) -> str:
        return prompt[:220].strip()


def _fixture_text_from_metadata(metadata: dict[str, Any]) -> str:
    text = metadata.get("extracted_text")
    if not isinstance(text, str) or not text.strip():
        raise PequiFluxError(
            "UNREADABLE_DOCUMENT",
            "Text ticket fixture has no extracted_text metadata.",
        )
    return text


def _fixture_ticket_from_metadata(metadata: dict[str, Any]) -> ParsedTicket:
    if metadata.get("content_type") == "text/plain":
        return parse_structured_ticket_text(_fixture_text_from_metadata(metadata))

    document_ref = metadata.get("document_ref")
    if not isinstance(document_ref, str) or not document_ref.strip():
        raise PequiFluxError(
            "TEXT_RUNTIME_REQUIRES_EXPECTED_TICKET",
            "TextTicketRuntime requires document_ref metadata for non-text fixtures.",
        )

    ticket = load_expected_ticket_fixture(document_ref)
    if ticket is None:
        raise PequiFluxError(
            "TEXT_RUNTIME_REQUIRES_EXPECTED_TICKET",
            "TextTicketRuntime requires expected_ticket.json for non-text CI fixtures.",
        )
    return ticket
