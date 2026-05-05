from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path

EXPECTED_SCENARIO_COUNT = 20
EXPECTED_VARIANTS = {"raw_fifo", "fifo_safe", "heuristic", "full"}
EXPECTED_README_METRICS = {
    "full": {
        "decision_match_at_1": 1.0,
        "exception_f1": 1.0,
        "ticket_field_accuracy": 0.969,
        "audit_completeness": 1.0,
    },
    "heuristic": {
        "decision_match_at_1": 0.85,
        "exception_f1": 0.678,
        "ticket_field_accuracy": 0.85,
        "audit_completeness": 0.85,
    },
    "fifo_safe": {
        "decision_match_at_1": 0.7,
        "constraint_violation_rate": 0.0,
    },
    "raw_fifo": {
        "decision_match_at_1": 0.25,
        "constraint_violation_rate": 0.35,
    },
}


def test_public_sample_metrics_summary_and_readme_stay_consistent() -> None:
    metrics = json.loads(Path("bench/reports/sample/metrics.json").read_text(encoding="utf-8"))
    summary_rows = list(
        csv.DictReader(
            Path("bench/reports/sample/summary.csv").read_text(encoding="utf-8").splitlines()
        )
    )
    readme_text = Path("README.md").read_text(encoding="utf-8")

    assert metrics["scenario_count"] == EXPECTED_SCENARIO_COUNT
    assert metrics["passed_count"] == EXPECTED_SCENARIO_COUNT
    assert set(metrics["variant_metrics"]) == EXPECTED_VARIANTS

    assert len(summary_rows) == EXPECTED_SCENARIO_COUNT * len(EXPECTED_VARIANTS)
    assert {row["variant"] for row in summary_rows} == EXPECTED_VARIANTS

    rows_by_scenario: dict[str, set[str]] = defaultdict(set)
    for row in summary_rows:
        rows_by_scenario[row["scenario_id"]].add(row["variant"])
    assert len(rows_by_scenario) == EXPECTED_SCENARIO_COUNT
    assert all(variants == EXPECTED_VARIANTS for variants in rows_by_scenario.values())

    for variant, expected_metrics in EXPECTED_README_METRICS.items():
        variant_metrics = metrics["variant_metrics"][variant]
        assert variant_metrics["scenario_count"] == EXPECTED_SCENARIO_COUNT
        assert variant_metrics["passed_count"] == EXPECTED_SCENARIO_COUNT
        for metric_name, expected_value in expected_metrics.items():
            assert variant_metrics[metric_name] == expected_value
            assert _readme_metric(readme_text, variant, metric_name) == expected_value

    assert _readme_full_count(readme_text) == (EXPECTED_SCENARIO_COUNT, EXPECTED_SCENARIO_COUNT)


def _readme_metric(readme_text: str, variant: str, metric_name: str) -> float:
    body = _readme_variant_body(readme_text, variant)
    match = re.search(rf"`{re.escape(metric_name)}`?\s*=\s*([0-9.]+)", body)
    assert match is not None, f"README missing {metric_name} for {variant}"
    return float(match.group(1))


def _readme_full_count(readme_text: str) -> tuple[int, int]:
    body = _readme_variant_body(readme_text, "full")
    match = re.search(r"`(\d+)/(\d+)`", body)
    assert match is not None, "README missing full passed/scenario count"
    return int(match.group(1)), int(match.group(2))


def _readme_variant_body(readme_text: str, variant: str) -> str:
    match = re.search(rf"^- `{re.escape(variant)}`: (?P<body>.+)$", readme_text, re.MULTILINE)
    assert match is not None, f"README missing sample bullet for {variant}"
    return match.group("body")
