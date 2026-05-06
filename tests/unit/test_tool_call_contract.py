from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.domain.models import AuditRecord, ToolCallIntent, ToolCallRecord


def test_tool_call_intent_validates_tool_name_and_purpose_length() -> None:
    intent = ToolCallIntent(
        tool_name="validate_hard_constraints",
        request_id="REQ-001",
        purpose="Validar destinos candidatos.",
    )

    assert intent.tool_name == "validate_hard_constraints"

    with pytest.raises(ValidationError):
        ToolCallIntent(
            tool_name="compose_driver_message",
            request_id="REQ-001",
            purpose="x" * 241,
        )


def test_audit_record_accepts_typed_tool_call_records() -> None:
    audit = AuditRecord(
        decision_id="DEC-001",
        request_id="REQ-001",
        scenario_id="S01_BASELINE",
        variant="full",
        tool_calls=[
            ToolCallRecord(
                tool_name="rank_candidates",
                request_id="REQ-001",
                state="VALIDATED",
                status="executed",
            )
        ],
    )

    assert audit.tool_calls[0].tool_name == "rank_candidates"
