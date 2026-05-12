from __future__ import annotations

from bench.gates import evaluate_submission_gates


def test_submission_gates_report_failed_metrics_with_actions() -> None:
    metrics = {
        "constraint_violation_rate": 0.0,
        "audit_completeness": 1.0,
        "decision_match_at_1": 0.91,
        "ticket_field_accuracy": 0.95,
        "ticket_field_accuracy_pdf_or_image_degraded": 0.89,
        "exception_macro_f1": 0.90,
        "fifo_break_justified_precision": 0.95,
        "tool_call_success_rate": 0.98,
        "latency_p50_ms": 5000,
        "latency_p95_ms": 11000,
        "timeout_rate": 0.0,
        "manual_review_rate": 0.10,
        "no_expected_ticket_leakage": True,
    }

    gates = evaluate_submission_gates(metrics)

    assert gates["submission_ready"] is False
    assert gates["failed_gates"] == [
        {
            "metric": "decision_match_at_1",
            "actual": 0.91,
            "target": ">= 0.92",
            "recommended_action": "review perception, exception classification, ranking, and labels",
        },
        {
            "metric": "ticket_field_accuracy_pdf_or_image_degraded",
            "actual": 0.89,
            "target": ">= 0.9",
            "recommended_action": "improve preprocess, OCR hints, or field extraction evidence",
        },
    ]


def test_submission_gates_accept_null_fifo_precision_when_no_fifo_breaks() -> None:
    metrics = {
        "constraint_violation_rate": 0.0,
        "audit_completeness": 1.0,
        "decision_match_at_1": 0.92,
        "ticket_field_accuracy": 0.95,
        "ticket_field_accuracy_pdf_or_image_degraded": 0.90,
        "exception_macro_f1": 0.90,
        "fifo_break_justified_precision": None,
        "tool_call_success_rate": 0.98,
        "latency_p50_ms": 6000,
        "latency_p95_ms": 12000,
        "timeout_rate": 0.0,
        "manual_review_rate": 0.15,
        "no_expected_ticket_leakage": True,
    }

    gates = evaluate_submission_gates(metrics)

    assert gates == {"submission_ready": True, "failed_gates": []}
