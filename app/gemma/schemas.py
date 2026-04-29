from __future__ import annotations

from typing import TypeAlias

from app.domain.models import ExceptionAssessment, InterpretedContext, ParsedTicket

SchemaName: TypeAlias = str

PARSED_TICKET_SCHEMA: SchemaName = "ParsedTicket"
EXCEPTION_ASSESSMENT_SCHEMA: SchemaName = "ExceptionAssessment"
INTERPRETED_CONTEXT_SCHEMA: SchemaName = "InterpretedContext"
EXPLANATION_SCHEMA: SchemaName = "DecisionExplanation"


def supported_schema_names() -> list[SchemaName]:
    return [
        PARSED_TICKET_SCHEMA,
        EXCEPTION_ASSESSMENT_SCHEMA,
        INTERPRETED_CONTEXT_SCHEMA,
        EXPLANATION_SCHEMA,
    ]


__all__ = [
    "ParsedTicket",
    "ExceptionAssessment",
    "InterpretedContext",
    "PARSED_TICKET_SCHEMA",
    "EXCEPTION_ASSESSMENT_SCHEMA",
    "INTERPRETED_CONTEXT_SCHEMA",
    "EXPLANATION_SCHEMA",
    "supported_schema_names",
]
