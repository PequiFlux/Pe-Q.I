from __future__ import annotations

from typing import Any

from app.domain.errors import PequiFluxError
from app.domain.models import ExceptionAssessment, ParsedTicket

_TEXT_MARKER = "Extracted text, if available:"


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

        text = _extract_ticket_text(prompt)
        fields = _parse_fields(text)
        return ParsedTicket.model_validate(
            {
                "ticket_id": fields.get("ticket_id"),
                "truck_id": fields.get("truck_id"),
                "vehicle_type": fields.get("vehicle_type", "unknown"),
                "document_status": fields.get("document_status", "unknown"),
                "document_block_flags": _parse_list(fields.get("document_block_flags", "")),
                "load_condition": fields.get("load_condition", "unknown"),
                "contract_priority_flag": _parse_bool(fields.get("contract_priority_flag", "false")),
                "destination_constraints": _parse_list(fields.get("destination_constraints", "")),
                "parse_confidence": float(fields.get("parse_confidence", "0.0")),
                "ambiguities": _parse_list(fields.get("ambiguities", "")),
                "evidence_refs": _parse_bullets(text, "evidence_refs"),
            }
        )

    def summarize(self, *, prompt: str, metadata: dict[str, Any]) -> str:
        return prompt[:220].strip()


def _extract_ticket_text(prompt: str) -> str:
    if _TEXT_MARKER not in prompt:
        raise PequiFluxError("MISSING_EXTRACTED_TEXT", "Prompt does not contain extracted ticket text.")
    text = prompt.split(_TEXT_MARKER, 1)[1].strip()
    if text.endswith("."):
        text = text[:-1]
    if not text or text == "none":
        raise PequiFluxError("UNREADABLE_DOCUMENT", "Text ticket has no extracted content.")
    return text


def _parse_fields(text: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("-") or ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        fields[key.strip()] = value.strip()
    return fields


def _parse_list(value: str) -> list[str]:
    stripped = value.strip()
    if not stripped or stripped == "[]":
        return []
    if stripped.startswith("[") and stripped.endswith("]"):
        stripped = stripped[1:-1]
    return [item.strip().strip('"').strip("'") for item in stripped.split(",") if item.strip()]


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"true", "1", "yes", "sim"}


def _parse_bullets(text: str, section: str) -> list[str]:
    lines = text.splitlines()
    refs: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if stripped == f"{section}:":
            in_section = True
            continue
        if in_section and stripped.startswith("-"):
            refs.append(stripped[1:].strip().strip('"').strip("'"))
            continue
        if in_section and stripped and not stripped.startswith("-"):
            break
    return refs
