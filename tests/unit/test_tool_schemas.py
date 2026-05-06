from __future__ import annotations

from app.gemma.tool_schemas import TOOL_SCHEMAS
from app.gemma.tool_gateway import TOOL_STATE_ORDER


def test_tool_schemas_are_request_id_only_for_model_intents() -> None:
    assert set(TOOL_SCHEMAS) == {
        "validate_hard_constraints",
        "rank_candidates",
        "generate_audit_payload",
    }

    for schema in TOOL_SCHEMAS.values():
        assert schema == {
            "type": "object",
            "required": ["request_id"],
            "additionalProperties": False,
            "properties": {
                "request_id": {"type": "string"},
            },
        }

    assert "compose_driver_message" not in TOOL_SCHEMAS
    assert "compose_driver_message" not in TOOL_STATE_ORDER
