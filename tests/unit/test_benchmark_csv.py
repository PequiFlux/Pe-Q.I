from __future__ import annotations

import csv

from bench.reporting import render_summary_csv


def test_summary_csv_escapes_commas_in_fields() -> None:
    csv_text = render_summary_csv(
        [
            {
                "scenario_id": "S01_BASELINE",
                "variant": "full",
                "passed": False,
                "decision_match_at_1": False,
                "constraint_violation": False,
                "ticket_field_accuracy": 1.0,
                "observed_primary_exception": "RAIN, OPEN_DESTINATION",
                "expected_primary_exception": "RAIN, OPEN_DESTINATION",
                "exception_match": True,
                "fifo_break_justified": False,
                "audit_complete": True,
                "decision_status": "REVIEW_REQUIRED",
                "recommended_truck": "TRK-001",
                "recommended_destination": "DST-COV-01",
                "fifo_break": False,
                "rejected_count": 1,
                "tool_call_count": 2,
                "tool_call_success": True,
                "tool_path": "validate_hard_constraints",
                "tool_error_count": 0,
                "planner_step_count": 1,
                "latency_ms_total": 12.5,
            }
        ]
    )

    rows = list(csv.DictReader(csv_text.splitlines()))

    assert rows[0]["observed_primary_exception"] == "RAIN, OPEN_DESTINATION"
    assert rows[0]["expected_primary_exception"] == "RAIN, OPEN_DESTINATION"
    assert rows[0]["tool_path"] == "validate_hard_constraints"
