from __future__ import annotations

from typing import Any

from app.domain.models import FrontEndPayload


FULL_PREVIEW_READY_TOOLS = {
    "validate_hard_constraints",
    "rank_candidates",
    "generate_audit_payload",
}


def validate_payload(payload: FrontEndPayload, expected: dict[str, Any]) -> None:
    errors: list[str] = []
    if payload.decision_status != expected["expected_status"]:
        errors.append(f"status={payload.decision_status!s}, expected={expected['expected_status']}")

    truck_id = payload.recommended_truck.truck_id if payload.recommended_truck else None
    if truck_id not in expected["acceptable_trucks"]:
        errors.append(f"truck={truck_id}, acceptable={expected['acceptable_trucks']}")

    destination_id = (
        payload.recommended_destination.destination_id if payload.recommended_destination else None
    )
    if destination_id not in expected["acceptable_destinations"]:
        errors.append(
            f"destination={destination_id}, acceptable={expected['acceptable_destinations']}"
        )

    fifo_break = bool(
        payload.recommended_truck and payload.recommended_truck.queue_position_before != 1
    )
    if fifo_break != expected["fifo_break_expected"]:
        errors.append(f"fifo_break={fifo_break}, expected={expected['fifo_break_expected']}")

    rejected_constraints = {
        failure["constraint_id"]
        for rejected in (payload.audit_record.rejected_candidates if payload.audit_record else [])
        for failure in rejected.get("failed_constraints", [])
    }
    missing_constraints = set(expected["required_constraints"]) - rejected_constraints
    if missing_constraints:
        errors.append(f"missing rejected constraints={sorted(missing_constraints)}")

    fired_rules = set(payload.audit_record.fired_rules if payload.audit_record else [])
    missing_policy_rules = set(expected.get("required_policy_rules", [])) - fired_rules
    if missing_policy_rules:
        errors.append(f"missing policy rules={sorted(missing_policy_rules)}")

    try:
        validate_full_tool_contract(payload)
    except SystemExit as exc:
        errors.append(str(exc))

    if errors:
        raise SystemExit("Scenario validation failed: " + "; ".join(errors))


def validate_full_tool_contract(payload: FrontEndPayload) -> None:
    missing_tool_calls = _missing_required_tool_calls(payload)
    if missing_tool_calls:
        raise SystemExit(f"missing full tool calls={missing_tool_calls}")


def _missing_required_tool_calls(payload: FrontEndPayload) -> list[str]:
    if payload.variant != "full":
        return []
    executed_tools = {
        record.tool_name
        for record in (payload.audit_record.tool_calls if payload.audit_record else [])
        if record.status == "executed"
    }
    if payload.decision_status == "PREVIEW_READY":
        return sorted(FULL_PREVIEW_READY_TOOLS - executed_tools)
    if payload.decision_status == "REVIEW_REQUIRED":
        if "generate_audit_payload" not in executed_tools:
            return ["generate_audit_payload"]
    return []
