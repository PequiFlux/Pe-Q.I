from __future__ import annotations

import csv
import json
from pathlib import Path

from app.ui.pages.benchmark_dashboard import dashboard_model_from_artifacts


def test_dashboard_model_summarizes_metrics_gates_and_errors(tmp_path: Path) -> None:
    (tmp_path / "metrics.json").write_text(
        json.dumps(
            {
                "benchmark_id": "B1_clean_public_test_frozen",
                "runtime": "text",
                "scenario_count": 2,
                "metrics": {
                    "constraint_violation_rate": 0.0,
                    "audit_completeness": 1.0,
                    "decision_match_at_1": 0.92,
                    "ticket_field_accuracy": 0.95,
                    "exception_macro_f1": 0.9,
                    "latency_p95_ms": 12000,
                },
                "gates": {
                    "submission_ready": False,
                    "failed_gates": [
                        {
                            "metric": "tool_call_success_rate",
                            "actual": 0.95,
                            "target": ">= 0.98",
                            "recommended_action": "fix tools",
                        }
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "summary.csv").write_text(
        "scenario_id,variant,decision_match_at_1,ticket_field_accuracy,"
        "exception_match,latency_ms_total\n"
        "S1,full,True,1.0,True,10\n"
        "S1,heuristic,False,0.5,False,12\n"
        "S1,fifo_safe,True,0.0,True,1\n",
        encoding="utf-8",
    )
    with (tmp_path / "error_analysis.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "scenario_id",
                "scenario_family",
                "modality",
                "primary_failure_type",
                "decision_correct",
                "notes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "scenario_id": "S1",
                "scenario_family": "rain",
                "modality": "png",
                "primary_failure_type": "perception_failure",
                "decision_correct": "False",
                "notes": "ticket_field_accuracy=0.5",
            }
        )

    model = dashboard_model_from_artifacts(tmp_path)

    assert model["benchmark_id"] == "B1_clean_public_test_frozen"
    assert model["headline_metrics"] == [
        {"metric": "constraint_violation_rate", "value": 0.0},
        {"metric": "audit_completeness", "value": 1.0},
        {"metric": "decision_match_at_1", "value": 0.92},
        {"metric": "ticket_field_accuracy", "value": 0.95},
        {"metric": "exception_macro_f1", "value": 0.9},
        {"metric": "latency_p95_ms", "value": 12000},
    ]
    assert model["baseline_rows"] == [
        {
            "variant": "fifo_safe",
            "decision_match_at_1": 1.0,
            "ticket_field_accuracy": 0.0,
            "exception_match": 1.0,
            "latency_ms_total": 1.0,
        },
        {
            "variant": "full",
            "decision_match_at_1": 1.0,
            "ticket_field_accuracy": 1.0,
            "exception_match": 1.0,
            "latency_ms_total": 10.0,
        },
        {
            "variant": "heuristic",
            "decision_match_at_1": 0.0,
            "ticket_field_accuracy": 0.5,
            "exception_match": 0.0,
            "latency_ms_total": 12.0,
        },
    ]
    assert model["failed_gates"][0]["metric"] == "tool_call_success_rate"
    assert model["failure_examples"][0]["primary_failure_type"] == "perception_failure"
