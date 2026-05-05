from __future__ import annotations

from app.adapters.document_adapter import build_document_bundle
from app.domain.errors import PequiFluxError
from app.domain.models import ParsedTicket, TicketContentType


def parse_structured_ticket_document(
    *,
    request_id: str,
    document_ref: str,
    content_type: TicketContentType,
    candidate_truck_ids: list[str],
) -> ParsedTicket:
    bundle = build_document_bundle(
        request_id=request_id,
        document_ref=document_ref,
        content_type=content_type,
        candidate_truck_ids=candidate_truck_ids,
    )
    if not bundle.extracted_text:
        raise PequiFluxError(
            "STRUCTURED_TICKET_TEXT_REQUIRED",
            "Heuristic benchmark variant requires extractable ticket text.",
        )

    return parse_structured_ticket_text(bundle.extracted_text)


def parse_structured_ticket_text(text: str) -> ParsedTicket:
    if not text.strip():
        raise PequiFluxError(
            "STRUCTURED_TICKET_TEXT_REQUIRED",
            "Structured ticket fixture requires extractable ticket text.",
        )

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
            refs.append(stripped[1:].strip().strip('"'))
        elif in_section and stripped and not stripped.startswith("-"):
            break
    return refs
