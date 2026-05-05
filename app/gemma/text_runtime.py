from __future__ import annotations

from typing import Any

from app.domain.errors import PequiFluxError
from app.domain.models import ExceptionAssessment, ParsedTicket
from app.services.structured_ticket_parser import parse_structured_ticket_text


class TextTicketRuntime:
    """Deterministic structured runtime for text/plain scenario tickets."""

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
        if metadata.get("content_type") != "text/plain":
            raise PequiFluxError(
                "TEXT_RUNTIME_REQUIRES_TEXT_TICKET",
                "TextTicketRuntime is only valid for text/plain CI fixtures.",
            )

        text = _fixture_text_from_metadata(metadata)
        return parse_structured_ticket_text(text)

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
