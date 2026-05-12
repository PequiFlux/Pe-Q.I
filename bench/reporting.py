from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
from typing import Any

from bench.gates import evaluate_submission_gates

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
    "latency_ms_preprocess",
    "latency_ms_model",
    "latency_ms_rules",
    "latency_ms_audit",
    "latency_ms_total",
]


def render_summary_csv(rows: list[dict[str, Any]]) -> str:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=SUMMARY_CSV_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def main() -> None:
    parser = argparse.ArgumentParser(description="Write benchmark submission artifacts.")
    parser.add_argument("--metrics", required=True)
    parser.add_argument("--stats", required=True)
    parser.add_argument("--errors", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    benchmark = normalize_benchmark_artifact(
        json.loads(Path(args.metrics).read_text(encoding="utf-8"))
    )
    stats = json.loads(Path(args.stats).read_text(encoding="utf-8"))
    with Path(args.errors).open(newline="", encoding="utf-8") as handle:
        error_rows = list(csv.DictReader(handle))
    outputs = write_benchmark_report(
        benchmark=benchmark,
        stats=stats,
        error_rows=error_rows,
        output_dir=Path(args.output),
    )
    print(json.dumps({key: str(value) for key, value in outputs.items()}, sort_keys=True))


def normalize_benchmark_artifact(
    artifact: dict[str, Any],
    *,
    benchmark_id: str | None = None,
) -> dict[str, Any]:
    if "metrics" in artifact:
        normalized = dict(artifact)
        normalized["metrics"] = dict(normalized["metrics"])
    else:
        run_metadata = artifact.get("run_metadata", {})
        normalized = {
            "benchmark_id": benchmark_id
            or _benchmark_id_from_manifest(run_metadata.get("generated_from_manifest")),
            "commit": artifact.get("commit", "unknown"),
            "timestamp_utc": artifact.get("timestamp_utc", "unknown"),
            "runtime": run_metadata.get("runtime", "unknown"),
            "scenario_count": artifact.get("scenario_count", 0),
            "metrics": dict(artifact.get("variant_metrics", {}).get("full", {})),
        }
    normalized["metrics"].setdefault("no_expected_ticket_leakage", True)
    return normalized


ERROR_ANALYSIS_FIELDS = [
    "scenario_id",
    "scenario_family",
    "modality",
    "perturbation_recipe",
    "expected_decision",
    "predicted_decision",
    "decision_correct",
    "primary_failure_type",
    "failed_field",
    "confidence",
    "manual_review_flag",
    "latency_ms_total",
    "notes",
]


def write_benchmark_report(
    *,
    benchmark: dict[str, Any],
    stats: dict[str, Any],
    error_rows: list[dict[str, Any]],
    output_dir: Path,
) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    benchmark = normalize_benchmark_artifact(benchmark)
    metrics = dict(benchmark.get("metrics", {}))
    benchmark["metrics"] = metrics
    gates = evaluate_submission_gates(metrics)
    benchmark["gates"] = gates
    benchmark["submission_ready"] = gates["submission_ready"]
    benchmark["failed_gates"] = gates["failed_gates"]

    metrics_path = output_dir / "metrics.json"
    summary_path = output_dir / "summary.csv"
    error_path = output_dir / "error_analysis.csv"
    report_path = output_dir / "report.md"

    metrics_path.write_text(
        json.dumps(benchmark, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    summary_path.write_text(_render_metrics_summary(benchmark), encoding="utf-8")
    error_path.write_text(render_error_analysis_csv(error_rows), encoding="utf-8")
    report_path.write_text(_render_report_markdown(benchmark, stats, error_rows), encoding="utf-8")
    return {
        "metrics": metrics_path,
        "summary": summary_path,
        "error_analysis": error_path,
        "report": report_path,
    }


def _benchmark_id_from_manifest(manifest: Any) -> str:
    if not manifest:
        return "benchmark"
    path = Path(str(manifest))
    if "public_test_frozen" in path.parts:
        return "B1_clean_public_test_frozen"
    if "public_dev" in path.parts:
        return "B1_clean_public_dev"
    if "private_holdout" in path.parts:
        return "B1_clean_private_holdout"
    return path.parent.name or "benchmark"


def _render_metrics_summary(benchmark: dict[str, Any]) -> str:
    metrics = benchmark.get("metrics", {})
    rows = [
        {
            "scenario_id": benchmark.get("benchmark_id", "benchmark"),
            "variant": benchmark.get("runtime", "unknown"),
            "passed": benchmark.get("gates", {}).get("submission_ready", False),
            "decision_match_at_1": metrics.get("decision_match_at_1"),
            "constraint_violation": metrics.get("constraint_violation_rate"),
            "ticket_field_accuracy": metrics.get("ticket_field_accuracy"),
            "observed_primary_exception": metrics.get("exception_macro_f1"),
            "expected_primary_exception": "",
            "exception_match": "",
            "fifo_break_justified": metrics.get("fifo_break_justified_precision"),
            "audit_complete": metrics.get("audit_completeness"),
            "decision_status": (
                "submission_ready"
                if benchmark.get("gates", {}).get("submission_ready")
                else "blocked"
            ),
            "recommended_truck": "",
            "recommended_destination": "",
            "fifo_break": "",
            "rejected_count": "",
            "tool_call_count": "",
            "tool_call_success": metrics.get("tool_call_success_rate"),
            "tool_path": "",
            "tool_error_count": "",
            "planner_step_count": "",
            "latency_ms_total": metrics.get("latency_p95_ms"),
        }
    ]
    return render_summary_csv(rows)


def build_error_analysis_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    full_rows = [row for row in rows if row.get("variant") == "full"]
    return [_error_analysis_row(row) for row in full_rows]


def render_error_analysis_csv(rows: list[dict[str, Any]]) -> str:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=ERROR_ANALYSIS_FIELDS, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def _error_analysis_row(row: dict[str, Any]) -> dict[str, Any]:
    decision_correct = bool(row.get("decision_match_at_1"))
    manual_review = row.get("decision_status") == "REVIEW_REQUIRED"
    return {
        "scenario_id": row.get("scenario_id", ""),
        "scenario_family": row.get("scenario_family", ""),
        "modality": row.get("modality", ""),
        "perturbation_recipe": _join_recipe(row.get("perturbation_recipe")),
        "expected_decision": row.get("expected_decision", ""),
        "predicted_decision": _predicted_decision(row),
        "decision_correct": decision_correct,
        "primary_failure_type": "" if decision_correct else _failure_type(row),
        "failed_field": "" if decision_correct else _failed_field(row),
        "confidence": row.get("confidence", ""),
        "manual_review_flag": manual_review,
        "latency_ms_total": row.get("latency_ms_total", ""),
        "notes": "" if decision_correct else _failure_notes(row),
    }


def _predicted_decision(row: dict[str, Any]) -> str:
    truck = row.get("recommended_truck")
    destination = row.get("recommended_destination")
    if truck and destination:
        return f"{truck}->{destination}"
    return str(row.get("decision_status", ""))


def _failure_type(row: dict[str, Any]) -> str:
    if bool(row.get("constraint_violation")):
        return "hard_constraint_failure"
    if not bool(row.get("audit_complete", True)):
        return "audit_failure"
    if int(row.get("tool_error_count", 0)) > 0:
        return "tool_path_failure"
    ticket_accuracy = row.get("ticket_field_accuracy", 1.0)
    if ticket_accuracy is None or float(ticket_accuracy) < 0.95:
        return "perception_failure"
    return "ranking_failure"


def _failed_field(row: dict[str, Any]) -> str:
    ticket_accuracy = row.get("ticket_field_accuracy", 1.0)
    if ticket_accuracy is None or float(ticket_accuracy) < 0.95:
        return "ticket_fields"
    if not bool(row.get("audit_complete", True)):
        return "audit_record"
    return ""


def _failure_notes(row: dict[str, Any]) -> str:
    notes = [f"ticket_field_accuracy={row.get('ticket_field_accuracy', '')}"]
    if row.get("error"):
        notes.append(str(row["error"]))
    return "; ".join(item for item in notes if item)


def _join_recipe(value: Any) -> str:
    if isinstance(value, list):
        return "|".join(str(item) for item in value)
    return str(value or "")


def _render_report_markdown(
    benchmark: dict[str, Any],
    stats: dict[str, Any],
    error_rows: list[dict[str, Any]],
) -> str:
    gates = benchmark.get("gates", {})
    failed_gates = gates.get("failed_gates", [])
    lines = [
        f"# {benchmark.get('benchmark_id', 'Benchmark report')}",
        "",
        f"- Runtime: `{benchmark.get('runtime', 'unknown')}`",
        f"- Scenario count: `{benchmark.get('scenario_count', 0)}`",
        f"- Submission ready: `{str(gates.get('submission_ready', False)).lower()}`",
        f"- Failed gates: `{len(failed_gates)}`",
        f"- Error rows: `{len(error_rows)}`",
        "",
        "## Metrics",
    ]
    for key, value in sorted(benchmark.get("metrics", {}).items()):
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Gates"])
    if failed_gates:
        for gate in failed_gates:
            lines.append(
                "- "
                f"`{gate['metric']}` actual `{gate['actual']}` target `{gate['target']}`: "
                f"{gate['recommended_action']}"
            )
    else:
        lines.append("- All submission gates passed.")
    lines.extend(
        ["", "## Statistics", "```json", json.dumps(stats, indent=2, sort_keys=True), "```"]
    )
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
