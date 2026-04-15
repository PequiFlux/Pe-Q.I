from __future__ import annotations

from typing import TypeAlias

from app.domain.models import ParsedTicket

SchemaName: TypeAlias = str

PARSED_TICKET_SCHEMA: SchemaName = "ParsedTicket"
EXPLANATION_SCHEMA: SchemaName = "DecisionExplanation"


def supported_schema_names() -> list[SchemaName]:
    return [PARSED_TICKET_SCHEMA, EXPLANATION_SCHEMA]


__all__ = ["ParsedTicket", "PARSED_TICKET_SCHEMA", "EXPLANATION_SCHEMA", "supported_schema_names"]

