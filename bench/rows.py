from __future__ import annotations

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
        "latency_ms_total": sum(payload.latency_ms.values()),
    }


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
    for rejected in payload.audit_record.rejected_candidates:
        if rejected["truck_id"] == truck_id and rejected["destination_id"] == destination_id:
            return True
    return False


def ticket_field_accuracy(observed: dict[str, Any], expected: dict[str, Any]) -> float:
    matches = sum(
        1 for field in TICKET_ACCURACY_FIELDS if observed.get(field) == expected.get(field)
    )
    return round(matches / len(TICKET_ACCURACY_FIELDS), 3)


def audit_complete(payload: FrontEndPayload) -> bool:
    audit = payload.audit_record
    if audit is None:
        return False
    has_recommendation = payload.recommended_truck is None or audit.recommended_pair is not None
    return all(
        [
            bool(audit.hard_constraints_checked),
            bool(audit.provenance),
            bool(audit.latencies_ms),
            {"queue_csv_ref", "ticket_ref"}.issubset(audit.source_hashes),
            has_recommendation,
        ]
    )
