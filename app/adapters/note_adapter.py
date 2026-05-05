from __future__ import annotations

from app.domain.errors import PequiFluxError


def sanitize_operator_note(note: str, *, max_length: int = 2000) -> str:
    normalized = " ".join(note.strip().split())
    if not normalized:
        raise PequiFluxError("EMPTY_OPERATOR_NOTE", "Operator note cannot be empty.")
    if len(normalized) > max_length:
        raise PequiFluxError("NOTE_TOO_LONG", "Operator note exceeds the supported limit.")
    return normalized
