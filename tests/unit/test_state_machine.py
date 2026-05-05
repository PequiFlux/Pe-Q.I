from __future__ import annotations

import pytest

from app.domain.enums import FlowState
from app.domain.errors import PequiFluxError
from app.orchestration.state_machine import WorkflowStateMachine


def test_state_machine_requires_validation_before_preview() -> None:
    machine = WorkflowStateMachine()
    machine.transition_to(FlowState.NORMALIZED)
    machine.transition_to(FlowState.PARSED)
    machine.transition_to(FlowState.INTERPRETED)

    with pytest.raises(PequiFluxError):
        machine.transition_to(FlowState.PREVIEW_READY)


def test_state_machine_forces_blocked_terminal_with_reason() -> None:
    machine = WorkflowStateMachine()
    machine.transition_to(FlowState.NORMALIZED)

    state = machine.force_terminal(FlowState.BLOCKED, reason="policy profile missing")

    assert state == FlowState.BLOCKED
    assert machine.current_state == FlowState.BLOCKED
    assert machine.terminal_reason == "policy profile missing"


def test_state_machine_rejects_forcing_non_terminal_state() -> None:
    machine = WorkflowStateMachine()

    with pytest.raises(PequiFluxError, match="INVALID_FORCED_TERMINAL_STATE"):
        machine.force_terminal(FlowState.NORMALIZED, reason="not terminal")
