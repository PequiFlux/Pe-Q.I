from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from bench.reporting import main
from bench.reporting import build_error_analysis_rows
from bench.reporting import normalize_benchmark_artifact
from bench.reporting import write_benchmark_report


def test_write_benchmark_report_creates_required_artifacts(tmp_path: Path) -> None:
    benchmark = {
        "benchmark_id": "B1_clean_public_test_frozen",
        "commit": "abc123",
        "timestamp_utc": "2026-05-12T00:00:00Z",
        "runtime": "text",
        "scenario_count": 1,
        "metrics": {
            "constraint_violation_rate": 0.0,
            "audit_completeness": 1.0,
            "decision_match_at_1": 0.92,
            "ticket_field_accuracy": 0.95,
            "ticket_field_accuracy_pdf_or_image_degraded": 0.90,
            "exception_macro_f1": 0.90,
            "fifo_break_justified_precision": 0.95,
            "tool_call_success_rate": 0.98,
            "latency_p50_ms": 6000,
            "latency_p95_ms": 12000,
            "timeout_rate": 0.0,
            "manual_review_rate": 0.15,
            "no_expected_ticket_leakage": True,
        },
    }
    stats = {"mcnemar": {"p_value": 0.03125}}
    rows = [
        {
            "scenario_id": "S1",
            "scenario_family": "rain",
            "modality": "png",
            "perturbation_recipe": "rotation",
            "expected_decision": "TRK-1->DST-COV-01",
            "predicted_decision": "TRK-1->DST-COV-01",
            "decision_correct": True,
            "primary_failure_type": "",
            "failed_field": "",
            "confidence": 0.94,
            "manual_review_flag": False,
            "latency_ms_total": 6000,
            "notes": "strong noisy-document extraction",
        }
    ]

    outputs = write_benchmark_report(
        benchmark=benchmark,
        stats=stats,
        error_rows=rows,
        output_dir=tmp_path,
    )

    metrics = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["gates"]["submission_ready"] is True
    assert metrics["submission_ready"] is True
    assert metrics["failed_gates"] == []
    assert outputs["metrics"] == tmp_path / "metrics.json"
    assert outputs["summary"] == tmp_path / "summary.csv"
    assert outputs["error_analysis"] == tmp_path / "error_analysis.csv"
    assert outputs["report"] == tmp_path / "report.md"
    assert "B1_clean_public_test_frozen" in (tmp_path / "report.md").read_text(encoding="utf-8")

    error_rows = list(csv.DictReader((tmp_path / "error_analysis.csv").open()))
    assert error_rows[0]["primary_failure_type"] == ""


def test_reporting_cli_writes_artifacts_from_input_files(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    metrics_path = tmp_path / "metrics-input.json"
    stats_path = tmp_path / "stats.json"
    errors_path = tmp_path / "errors.csv"
    output_dir = tmp_path / "latest"
    metrics_path.write_text(
        json.dumps(
            {
                "benchmark_id": "B1_clean_public_test_frozen",
                "runtime": "text",
                "scenario_count": 1,
                "metrics": {
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
                },
            }
        ),
        encoding="utf-8",
    )
    stats_path.write_text(json.dumps({"mcnemar": {"p_value": 1.0}}), encoding="utf-8")
    errors_path.write_text(
        "scenario_id,scenario_family,modality,perturbation_recipe,expected_decision,"
        "predicted_decision,decision_correct,primary_failure_type,failed_field,"
        "confidence,manual_review_flag,latency_ms_total,notes\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "reporting",
            "--metrics",
            str(metrics_path),
            "--stats",
            str(stats_path),
            "--errors",
            str(errors_path),
            "--output",
            str(output_dir),
        ],
    )

    main()

    assert (output_dir / "metrics.json").exists()
    assert (output_dir / "summary.csv").exists()
    assert (output_dir / "error_analysis.csv").exists()
    assert (output_dir / "report.md").exists()


def test_normalize_benchmark_artifact_accepts_run_benchmark_metrics() -> None:
    artifact = normalize_benchmark_artifact(
        {
            "commit": "abc123",
            "timestamp_utc": "2026-05-12T00:00:00Z",
            "scenario_count": 30,
            "run_metadata": {
                "runtime": "text",
                "model": "text-runtime",
                "branch": "main",
                "seed": 42,
                "command": "python -m bench.clean_eval --runtime text",
                "delegated_command": "python -m app.cli.run_benchmark",
                "hardware": {"platform": "Linux", "cpu_count": 8},
                "logs": {"run_log": "artifacts/latest/clean_public_test/run.log"},
                "github_actions": {
                    "available": True,
                    "artifact_name": "clean-gemma-eval",
                    "run_url": "https://github.com/PequiFlux/Pe-Q.I/actions/runs/1",
                },
                "generated_from_manifest": "scenarios/extended/public_test_frozen/manifest.json",
            },
            "variant_metrics": {
                "full": {
                    "constraint_violation_rate": 0.0,
                    "audit_completeness": 1.0,
                    "decision_match_at_1": 0.92,
                    "ticket_field_accuracy": 0.95,
                    "ticket_field_accuracy_pdf_or_image_degraded": 0.90,
                    "exception_macro_f1": 0.90,
                    "fifo_break_justified_precision": 0.95,
                    "tool_call_success_rate": 0.98,
                    "latency_p50_ms": 6000,
                    "latency_p95_ms": 12000,
                    "timeout_rate": 0.0,
                    "manual_review_rate": 0.15,
                }
            },
        },
        benchmark_id="B1_clean_public_test_frozen",
    )

    assert artifact["benchmark_id"] == "B1_clean_public_test_frozen"
    assert artifact["runtime"] == "text"
    assert artifact["model"] == "text-runtime"
    assert artifact["commit"] == "abc123"
    assert artifact["timestamp_utc"] == "2026-05-12T00:00:00Z"
    assert artifact["branch"] == "main"
    assert artifact["seed"] == 42
    assert artifact["command"] == "python -m bench.clean_eval --runtime text"
    assert artifact["logs"]["run_log"] == "artifacts/latest/clean_public_test/run.log"
    assert artifact["github_actions"]["artifact_name"] == "clean-gemma-eval"
    assert artifact["scenario_count"] == 30
    assert artifact["metrics"]["no_expected_ticket_leakage"] is True


def test_build_error_analysis_rows_classifies_incorrect_decisions() -> None:
    rows = build_error_analysis_rows(
        [
            {
                "scenario_id": "S1",
                "variant": "full",
                "scenario_family": "rain",
                "modality": "png",
                "perturbation_recipe": ["rotation"],
                "decision_match_at_1": False,
                "constraint_violation": False,
                "audit_complete": True,
                "tool_error_count": 0,
                "ticket_field_accuracy": 0.75,
                "decision_status": "REVIEW_REQUIRED",
                "recommended_truck": None,
                "recommended_destination": None,
                "expected_decision": "TRK-1->DST-COV-01",
                "latency_ms_total": 42,
            }
        ]
    )

    assert rows == [
        {
            "scenario_id": "S1",
            "scenario_family": "rain",
            "modality": "png",
            "perturbation_recipe": "rotation",
            "expected_decision": "TRK-1->DST-COV-01",
            "predicted_decision": "REVIEW_REQUIRED",
            "decision_correct": False,
            "primary_failure_type": "perception_failure",
            "failed_field": "ticket_fields",
            "confidence": "",
            "manual_review_flag": True,
            "latency_ms_total": 42,
            "notes": "ticket_field_accuracy=0.75",
        }
    ]


def test_build_error_analysis_rows_handles_unavailable_ticket_accuracy() -> None:
    rows = build_error_analysis_rows(
        [
            {
                "scenario_id": "S1",
                "variant": "full",
                "scenario_family": "rain",
                "modality": "png",
                "perturbation_recipe": [],
                "decision_match_at_1": False,
                "constraint_violation": False,
                "audit_complete": True,
                "tool_error_count": 0,
                "ticket_field_accuracy": None,
                "decision_status": "REVIEW_REQUIRED",
                "recommended_truck": None,
                "recommended_destination": None,
                "expected_decision": "TRK-1->DST-COV-01",
                "latency_ms_total": 42,
            }
        ]
    )

    assert rows[0]["failed_field"] == "ticket_fields"
