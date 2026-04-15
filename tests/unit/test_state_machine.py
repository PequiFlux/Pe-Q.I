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

