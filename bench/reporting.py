from __future__ import annotations

import csv
import io
from typing import Any

SUMMARY_CSV_FIELDS = [
    "scenario_id",
    "variant",
    "passed",
    "decision_match_at_1",
    "constraint_violation",
    "ticket_field_accuracy",
    "observed_primary_exception",
    "expected_primary_exception",
    "exception_match",
    "fifo_break_justified",
    "audit_complete",
    "decision_status",
    "recommended_truck",
    "recommended_destination",
    "fifo_break",
    "rejected_count",
    "tool_call_count",
    "tool_call_success",
    "tool_path",
    "tool_error_count",
    "planner_step_count",
    "latency_ms_total",
]


def render_summary_csv(rows: list[dict[str, Any]]) -> str:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=SUMMARY_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()
