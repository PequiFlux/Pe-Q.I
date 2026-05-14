from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    InterpretedContext,
    ParsedTicket,
    PolicyProfile,
    QueueSnapshot,
    RankedCandidates,
    ValidationResult,
)


@dataclass(frozen=True)
class LoadedInputs:
    normalized_queue: QueueSnapshot
    source_hashes: dict[str, str]
    policy_profile: PolicyProfile


@dataclass(frozen=True)
class InterpretedStep:
    interpreted_context: InterpretedContext
    parsed_ticket_for_constraints: ParsedTicket | None


@dataclass(frozen=True)
class RankedStep:
    validation: ValidationResult
    ranking: RankedCandidates
