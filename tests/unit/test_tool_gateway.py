from __future__ import annotations

import pytest

from app.domain.enums import FlowState
from app.domain.errors import PequiFluxError
from app.gemma.tool_gateway import ToolGateway, ToolLocalIds


class MemoryLogger:
    def __init__(self) -> None:
        self.events: list[dict] = []

    def write(self, payload: dict) -> None:
        self.events.append(payload)


def _schema() -> dict:
    return {
        "type": "object",
        "required": ["request_id", "truck_id", "destination_id"],
        "additionalProperties": False,
        "properties": {
            "request_id": {"type": "string"},
            "truck_id": {"type": "string"},
            "destination_id": {"type": "string"},
            "dry_run": {"type": "boolean"},
        },
    }


def test_tool_gateway_validates_schema_and_executes_allowed_tool() -> None:
    gateway = ToolGateway(
        {"validate_hard_constraints": lambda **kwargs: kwargs},
        tool_schemas={"validate_hard_constraints": _schema()},
        current_state=FlowState.INTERPRETED,
        local_ids=ToolLocalIds.from_iterables(
            request_ids={"REQ-001"},
            truck_ids={"TRK-001"},
            destination_ids={"DST-001"},
        ),
    )

    result = gateway.execute(
        "validate_hard_constraints",
        {
            "request_id": "REQ-001",
            "truck_id": "TRK-001",
            "destination_id": "DST-001",
            "dry_run": True,
        },
    )

    assert result["truck_id"] == "TRK-001"


def test_tool_gateway_rejects_schema_errors() -> None:
    gateway = ToolGateway(
        {"validate_hard_constraints": lambda **kwargs: kwargs},
        tool_schemas={"validate_hard_constraints": _schema()},
        current_state=FlowState.INTERPRETED,
    )

    with pytest.raises(PequiFluxError, match="SCHEMA_ERROR"):
        gateway.execute(
            "validate_hard_constraints",
            {"request_id": "REQ-001", "truck_id": "TRK-001", "extra": "nope"},
        )


def test_tool_gateway_rejects_tool_order_errors() -> None:
    gateway = ToolGateway(
        {"rank_candidates": lambda **kwargs: kwargs},
        current_state=FlowState.INTERPRETED,
    )

    with pytest.raises(PequiFluxError, match="TOOL_ORDER_ERROR"):
        gateway.execute("rank_candidates", {})


def test_tool_gateway_rejects_unknown_local_ids() -> None:
    gateway = ToolGateway(
        {"validate_hard_constraints": lambda **kwargs: kwargs},
        current_state=FlowState.INTERPRETED,
        local_ids=ToolLocalIds.from_iterables(truck_ids={"TRK-001"}),
    )

    with pytest.raises(PequiFluxError, match="DOMAIN_VALIDATION_ERROR"):
        gateway.execute("validate_hard_constraints", {"truck_id": "TRK-404"})


def test_tool_gateway_logs_attempts_success_and_errors() -> None:
    logger = MemoryLogger()
    gateway = ToolGateway(
        {"validate_hard_constraints": lambda **kwargs: "ok"},
        current_state=FlowState.INTERPRETED,
        logger=logger,
    )

    assert gateway.execute("validate_hard_constraints", {"request_id": "REQ-001"}) == "ok"

    with pytest.raises(PequiFluxError, match="UNKNOWN_TOOL"):
        gateway.execute("not_allowed", {"request_id": "REQ-002"})

    assert [event["status"] for event in logger.events] == [
        "attempted",
        "executed",
        "attempted",
        "error",
    ]
    assert [event["request_id"] for event in logger.events] == [
        "REQ-001",
        "REQ-001",
        "REQ-002",
        "REQ-002",
    ]
    assert logger.events[-1]["error_code"] == "UNKNOWN_TOOL"
