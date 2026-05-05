from __future__ import annotations

from app.domain.enums import FlowState
from app.domain.errors import PequiFluxError

ALLOWED_TRANSITIONS: dict[FlowState, set[FlowState]] = {
    FlowState.RECEIVED: {
        FlowState.NORMALIZED,
        FlowState.BLOCKED,
        FlowState.ERROR_TERMINAL,
    },
    FlowState.NORMALIZED: {
        FlowState.PARSED,
        FlowState.REVIEW_REQUIRED,
        FlowState.BLOCKED,
        FlowState.ERROR_TERMINAL,
    },
    FlowState.PARSED: {
        FlowState.INTERPRETED,
        FlowState.REVIEW_REQUIRED,
        FlowState.ERROR_TERMINAL,
    },
    FlowState.INTERPRETED: {
        FlowState.VALIDATED,
        FlowState.REVIEW_REQUIRED,
        FlowState.BLOCKED,
        FlowState.ERROR_TERMINAL,
    },
    FlowState.VALIDATED: {
        FlowState.RANKED,
        FlowState.BLOCKED,
        FlowState.ERROR_TERMINAL,
    },
    FlowState.RANKED: {
        FlowState.PREVIEW_READY,
        FlowState.BLOCKED,
        FlowState.ERROR_TERMINAL,
    },
    FlowState.PREVIEW_READY: {FlowState.HUMAN_FINALIZED},
}

FORCEABLE_TERMINAL_STATES = {
    FlowState.BLOCKED,
    FlowState.ERROR_TERMINAL,
    FlowState.REVIEW_REQUIRED,
}


class WorkflowStateMachine:
    def __init__(self) -> None:
        self.current_state = FlowState.RECEIVED
        self.terminal_reason: str | None = None

    def transition_to(self, next_state: FlowState) -> FlowState:
        allowed = ALLOWED_TRANSITIONS.get(self.current_state, set())
        if next_state not in allowed:
            raise PequiFluxError(
                "INVALID_STATE_TRANSITION",
                f"Cannot transition from {self.current_state} to {next_state}.",
            )
        self.current_state = next_state
        return self.current_state

    def force_terminal(self, terminal_state: FlowState, *, reason: str) -> FlowState:
        if terminal_state not in FORCEABLE_TERMINAL_STATES:
            raise PequiFluxError(
                "INVALID_FORCED_TERMINAL_STATE",
                f"Cannot force non-terminal state: {terminal_state}.",
            )
        if self.current_state in {FlowState.HUMAN_FINALIZED, FlowState.ERROR_TERMINAL}:
            raise PequiFluxError(
                "INVALID_STATE_TRANSITION",
                f"Cannot force terminal state from {self.current_state}.",
            )
        self.current_state = terminal_state
        self.terminal_reason = reason
        return self.current_state
