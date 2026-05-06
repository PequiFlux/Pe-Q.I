from __future__ import annotations

from bench.metrics import compute_variant_metrics


def test_variant_metrics_include_declared_submission_metrics() -> None:
    rows = [
        {
            "passed": True,
            "decision_match_at_1": True,
            "constraint_violation": False,
            "ticket_field_accuracy": 1.0,
            "expected_primary_exception": "WET_LOAD",
            "observed_primary_exception": "WET_LOAD",
            "fifo_break": True,
            "fifo_break_expected": True,
            "audit_complete": True,
            "tool_call_success": True,
            "tool_call_count": 6,
            "planner_step_count": 3,
            "tool_error_count": 0,
            "latency_ms_total": 10,
        },
        {
            "passed": False,
            "decision_match_at_1": False,
            "constraint_violation": True,
            "ticket_field_accuracy": 0.5,
            "expected_primary_exception": "DOCUMENT_BLOCK",
            "observed_primary_exception": "NO_EXCEPTION",
            "fifo_break": True,
            "fifo_break_expected": False,
            "audit_complete": False,
            "tool_call_success": False,
            "tool_call_count": 1,
            "planner_step_count": 1,
            "tool_error_count": 1,
            "latency_ms_total": 30,
        },
    ]

    metrics = compute_variant_metrics(rows)

    assert metrics["decision_match_at_1"] == 0.5
    assert metrics["constraint_violation_rate"] == 0.5
    assert metrics["ticket_field_accuracy"] == 0.75
    assert metrics["exception_f1"] < 1.0
    assert metrics["fifo_break_justified_precision"] == 0.5
    assert metrics["audit_completeness"] == 0.5
    assert metrics["tool_call_success_rate"] == 0.5
    assert metrics["avg_tool_call_count"] == 3.5
    assert metrics["avg_planner_step_count"] == 2.0
    assert metrics["tool_error_count"] == 1
    assert metrics["tool_error_rate"] == 0.5
    assert metrics["latency_p50"] == 10
    assert metrics["latency_p95"] == 30
