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


class WorkflowStateMachine:
    def __init__(self) -> None:
        self.current_state = FlowState.RECEIVED

    def transition_to(self, next_state: FlowState) -> FlowState:
        allowed = ALLOWED_TRANSITIONS.get(self.current_state, set())
        if next_state not in allowed:
            raise PequiFluxError(
                "INVALID_STATE_TRANSITION",
                f"Cannot transition from {self.current_state} to {next_state}.",
            )
        self.current_state = next_state
        return self.current_state

