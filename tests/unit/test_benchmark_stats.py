from __future__ import annotations

import json
from pathlib import Path

from bench.stats import compare_benchmark_metrics
from bench.stats import load_benchmark_artifact


def test_compare_benchmark_metrics_reports_mcnemar_and_bootstrap_deltas() -> None:
    baseline = {
        "per_scenario": [
            {
                "scenario_id": "S1",
                "scenario_family": "rain",
                "decision_match_at_1": False,
                "ticket_field_accuracy": 0.5,
                "exception_match": False,
                "latency_ms_total": 40,
            },
            {
                "scenario_id": "S2",
                "scenario_family": "rain",
                "decision_match_at_1": True,
                "ticket_field_accuracy": 0.5,
                "exception_match": True,
                "latency_ms_total": 60,
            },
        ]
    }
    candidate = {
        "per_scenario": [
            {
                "scenario_id": "S1",
                "scenario_family": "rain",
                "decision_match_at_1": True,
                "ticket_field_accuracy": 1.0,
                "exception_match": True,
                "latency_ms_total": 30,
            },
            {
                "scenario_id": "S2",
                "scenario_family": "rain",
                "decision_match_at_1": True,
                "ticket_field_accuracy": 1.0,
                "exception_match": True,
                "latency_ms_total": 50,
            },
        ]
    }

    report = compare_benchmark_metrics(
        baseline,
        candidate,
        bootstrap_samples=200,
        random_seed=42,
    )

    assert report["scenario_count"] == 2
    assert report["mcnemar"]["candidate_only_correct"] == 1
    assert report["mcnemar"]["baseline_only_correct"] == 0
    assert report["bootstrap"]["ticket_field_accuracy"]["delta"] == 0.5
    assert report["bootstrap"]["exception_macro_f1"]["delta"] == 0.5
    assert report["bootstrap"]["latency_ms_total"]["delta"] == -10.0


def test_load_benchmark_artifact_reads_sibling_per_scenario_for_metrics_file(
    tmp_path: Path,
) -> None:
    metrics_path = tmp_path / "metrics.json"
    metrics_path.write_text(json.dumps({"variant_metrics": {"full": {}}}), encoding="utf-8")
    (tmp_path / "per_scenario.json").write_text(
        json.dumps(
            [
                {"scenario_id": "S1", "variant": "full", "decision_match_at_1": True},
                {
                    "scenario_id": "S1",
                    "variant": "heuristic",
                    "decision_match_at_1": False,
                },
            ]
        ),
        encoding="utf-8",
    )

    artifact = load_benchmark_artifact(metrics_path, variant="full")

    assert artifact["per_scenario"] == [
        {"scenario_id": "S1", "variant": "full", "decision_match_at_1": True}
    ]
