from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from app.domain.models import DecisionRequest, FrontEndPayload
from app.services.raw_fifo import raw_fifo_call
from bench.variants import RAW_FIFO_VARIANT

TICKET_ACCURACY_FIELDS = [
    "ticket_id",
    "truck_id",
    "vehicle_type",
    "document_status",
    "document_block_flags",
    "load_condition",
    "contract_priority_flag",
    "destination_constraints",
]
REQUIRED_SOURCE_HASHES = {
    "queue_csv_ref",
    "ticket_ref",
    "operator_note",
    "weather_state",
    "resource_state",
}
TERMINAL_AUDIT_STATUSES = {"BLOCKED", "REVIEW_REQUIRED"}
FULL_PREVIEW_READY_TOOL_PATH = (
    "validate_hard_constraints",
    "rank_candidates",
    "generate_audit_payload",
)
FULL_TERMINAL_TOOL_PATH = ("generate_audit_payload",)


def build_raw_fifo_row(
    *,
    request: DecisionRequest,
    expected: dict[str, Any],
    fifo_safe_payload: FrontEndPayload,
) -> dict[str, Any]:
    truck_id, destination_id = raw_fifo_call(request)
    decision_status = "PREVIEW_READY" if truck_id and destination_id else "REVIEW_REQUIRED"
    decision_match = (
        decision_status == expected["expected_status"]
        and truck_id in expected["acceptable_trucks"]
        and destination_id in expected["acceptable_destinations"]
        and expected["fifo_break_expected"] is False
    )
    constraint_violation = pair_rejected(fifo_safe_payload, truck_id, destination_id)
    return {
        "scenario_id": request.scenario_id,
        "variant": RAW_FIFO_VARIANT,
        "passed": True,
        "error": None,
        "decision_match_at_1": decision_match,
        "constraint_violation": constraint_violation,
        "ticket_field_accuracy": 0.0,
        "observed_primary_exception": "NO_CONTEXT",
        "expected_primary_exception": expected["expected_primary_exception"],
        "exception_match": expected["expected_primary_exception"] == "NO_CONTEXT",
        "audit_complete": False,
        "decision_status": decision_status,
        "recommended_truck": truck_id,
        "recommended_destination": destination_id,
        "fifo_break": False,
        "fifo_break_expected": expected["fifo_break_expected"],
        "fifo_break_justified": False,
        "rejected_count": 0,
        **_empty_tool_call_metrics(),
        "latency_ms_total": 0,
    }


def build_payload_row(
    *,
    scenario_id: str,
    variant: str,
    payload: FrontEndPayload,
    expected: dict[str, Any],
    ticket_field_accuracy: float,
) -> dict[str, Any]:
    fifo_break = bool(
        payload.recommended_truck and payload.recommended_truck.queue_position_before != 1
    )
    observed_primary_exception = str(payload.benchmark_observed.get("primary_exception", "UNKNOWN"))
    return {
        "scenario_id": scenario_id,
        "variant": variant,
        "passed": True,
        "error": None,
        "decision_match_at_1": matches_expected(payload, expected),
        "constraint_violation": has_constraint_violation(payload),
        "ticket_field_accuracy": ticket_field_accuracy,
        "observed_primary_exception": observed_primary_exception,
        "expected_primary_exception": expected["expected_primary_exception"],
        "exception_match": observed_primary_exception == expected["expected_primary_exception"],
        "audit_complete": audit_complete(payload),
        "decision_status": payload.decision_status,
        "recommended_truck": (
            payload.recommended_truck.truck_id if payload.recommended_truck else None
        ),
        "recommended_destination": (
            payload.recommended_destination.destination_id
            if payload.recommended_destination
            else None
        ),
        "fifo_break": fifo_break,
        "fifo_break_expected": expected["fifo_break_expected"],
        "fifo_break_justified": fifo_break and expected["fifo_break_expected"],
        "rejected_count": (
            len(payload.audit_record.rejected_candidates) if payload.audit_record else 0
        ),
        **tool_call_metrics(payload),
        "latency_ms_total": sum(payload.latency_ms.values()),
    }


def tool_call_metrics(payload: FrontEndPayload) -> dict[str, Any]:
    records = list(payload.audit_record.tool_calls if payload.audit_record else [])
    executed_tools = _unique_in_order(
        record.tool_name for record in records if record.status == "executed"
    )
    tool_error_count = sum(1 for record in records if record.status == "error")
    planner_step_count = sum(1 for record in records if record.status == "requested")
    required_tools = _required_tool_path(payload)
    return {
        "tool_call_count": len(records),
        "tool_call_success": bool(required_tools)
        and tool_error_count == 0
        and all(tool in executed_tools for tool in required_tools),
        "tool_path": ">".join(executed_tools),
        "tool_error_count": tool_error_count,
        "planner_step_count": planner_step_count,
    }


def _empty_tool_call_metrics() -> dict[str, Any]:
    return {
        "tool_call_count": 0,
        "tool_call_success": False,
        "tool_path": "",
        "tool_error_count": 0,
        "planner_step_count": 0,
    }


def _required_tool_path(payload: FrontEndPayload) -> tuple[str, ...]:
    if str(payload.variant) != "full":
        return ()
    status = str(payload.decision_status)
    if status == "PREVIEW_READY":
        return FULL_PREVIEW_READY_TOOL_PATH
    if status in TERMINAL_AUDIT_STATUSES:
        return FULL_TERMINAL_TOOL_PATH
    return ()


def _unique_in_order(values: Iterable[str]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        if value not in unique_values:
            unique_values.append(value)
    return unique_values


def matches_expected(payload: FrontEndPayload, expected: dict[str, Any]) -> bool:
    truck_id = payload.recommended_truck.truck_id if payload.recommended_truck else None
    destination_id = (
        payload.recommended_destination.destination_id if payload.recommended_destination else None
    )
    fifo_break = bool(
        payload.recommended_truck and payload.recommended_truck.queue_position_before != 1
    )
    return (
        payload.decision_status == expected["expected_status"]
        and truck_id in expected["acceptable_trucks"]
        and destination_id in expected["acceptable_destinations"]
        and fifo_break == expected["fifo_break_expected"]
    )


def has_constraint_violation(payload: FrontEndPayload) -> bool:
    if (
        not payload.recommended_truck
        or not payload.recommended_destination
        or not payload.audit_record
    ):
        return False
    return pair_rejected(
        payload,
        payload.recommended_truck.truck_id,
        payload.recommended_destination.destination_id,
    )


def pair_rejected(
    payload: FrontEndPayload,
    truck_id: str | None,
    destination_id: str | None,
) -> bool:
    if not truck_id or not destination_id or not payload.audit_record:
        return False
    pair_was_validated = False
    for checked in payload.audit_record.hard_constraints_checked:
        if checked["truck_id"] != truck_id or checked["destination_id"] != destination_id:
            continue
        pair_was_validated = True
        if not checked.get("eligible", False):
            return True
    for rejected in payload.audit_record.rejected_candidates:
        if rejected["truck_id"] == truck_id and rejected["destination_id"] == destination_id:
            return True
    return not pair_was_validated


def ticket_field_accuracy(observed: dict[str, Any], expected: dict[str, Any]) -> float:
    matches = sum(
        1 for field in TICKET_ACCURACY_FIELDS if observed.get(field) == expected.get(field)
    )
    return round(matches / len(TICKET_ACCURACY_FIELDS), 3)


def audit_complete(payload: FrontEndPayload) -> bool:
    audit = payload.audit_record
    if audit is None:
        return False
    status = str(payload.decision_status)
    has_base_audit = all(
        [
            bool(audit.latencies_ms),
            REQUIRED_SOURCE_HASHES.issubset(audit.source_hashes),
            audit.request_id == payload.request_id,
            audit.scenario_id == payload.scenario_id,
            audit.variant == payload.variant,
        ]
    )
    has_provenance_when_available = bool(audit.provenance)
    if status in TERMINAL_AUDIT_STATUSES:
        has_terminal_reason = bool(payload.reason_summary)
        has_terminal_context = bool(
            status
            and payload.benchmark_observed.get("primary_exception")
            and payload.gemma_visible_summary.exception_label
        )
        return all(
            [
                has_base_audit,
                has_provenance_when_available,
                has_terminal_reason,
                has_terminal_context,
            ]
        )

    has_recommendation = all(
        [
            payload.recommended_truck is not None,
            payload.recommended_destination is not None,
            audit.recommended_pair is not None,
        ]
    )
    return all(
        [
            status == "PREVIEW_READY",
            bool(audit.hard_constraints_checked),
            has_base_audit,
            has_provenance_when_available,
            has_recommendation,
        ]
    )
