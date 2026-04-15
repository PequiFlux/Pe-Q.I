from __future__ import annotations

from enum import StrEnum


class DecisionStatus(StrEnum):
    PREVIEW_READY = "PREVIEW_READY"
    BLOCKED = "BLOCKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    APPROVED = "APPROVED"
    OVERRIDDEN = "OVERRIDDEN"


class OperatorAction(StrEnum):
    APPROVE = "approve"
    BLOCK = "block"
    OVERRIDE = "override"


class DocumentStatus(StrEnum):
    CLEAR = "clear"
    BLOCKED = "blocked"
    INCOMPLETE = "incomplete"
    UNKNOWN = "unknown"


class LoadCondition(StrEnum):
    DRY = "dry"
    WET = "wet"
    UNKNOWN = "unknown"


class VehicleType(StrEnum):
    BITREM = "bitrem"
    RODOTREM = "rodotrem"
    TRUCK = "truck"
    UNKNOWN = "unknown"


class Severity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class FlowState(StrEnum):
    RECEIVED = "RECEIVED"
    NORMALIZED = "NORMALIZED"
    PARSED = "PARSED"
    INTERPRETED = "INTERPRETED"
    VALIDATED = "VALIDATED"
    RANKED = "RANKED"
    PREVIEW_READY = "PREVIEW_READY"
    HUMAN_FINALIZED = "HUMAN_FINALIZED"
    BLOCKED = "BLOCKED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ERROR_TERMINAL = "ERROR_TERMINAL"


class SourceKind(StrEnum):
    QUEUE_SNAPSHOT = "queue_snapshot"
    TICKET_DOCUMENT = "ticket_document"
    OPERATOR_NOTE = "operator_note"
    WEATHER_STATE = "weather_state"
    RESOURCE_STATE = "resource_state"

