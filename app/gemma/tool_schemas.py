from __future__ import annotations

TOOL_SCHEMAS = {
    "validate_hard_constraints": {
        "type": "object",
        "required": ["request_id"],
        "additionalProperties": False,
        "properties": {
            "request_id": {"type": "string"},
        },
    },
    "rank_candidates": {
        "type": "object",
        "required": ["request_id"],
        "additionalProperties": False,
        "properties": {
            "request_id": {"type": "string"},
        },
    },
    "generate_audit_payload": {
        "type": "object",
        "required": ["request_id"],
        "additionalProperties": False,
        "properties": {
            "request_id": {"type": "string"},
        },
    },
}
