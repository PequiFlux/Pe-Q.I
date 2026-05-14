from __future__ import annotations

from typing import Any

from app.domain.models import FrontEndPayload


def compute_benchmark_metrics(payloads: list[FrontEndPayload]) -> dict[str, float]:
    total = len(payloads)
    preview_ready = sum(1 for payload in payloads if payload.decision_status == "PREVIEW_READY")
    blocked = sum(1 for payload in payloads if payload.decision_status == "BLOCKED")
    review_required = sum(1 for payload in payloads if payload.decision_status == "REVIEW_REQUIRED")
    fifo_precision = _fifo_break_precision(rows)
    return {
        "total_runs": float(total),
        "preview_ready_ratio": (preview_ready / total) if total else 0.0,
        "blocked_ratio": (blocked / total) if total else 0.0,
        "review_required_ratio": (review_required / total) if total else 0.0,
    }


def compute_variant_metrics(rows: list[dict[str, Any]]) -> dict[str, float | int | None]:
    latencies = [item["latency_ms_total"] for item in rows]
    exception_macro_f1 = round(_macro_f1(rows), 3)
    degraded_rows = [
        item
        for item in rows
        if item.get("modality") in {"pdf", "pdf_text", "pdf_scanned", "png", "jpg"}
        or bool(item.get("perturbation_recipe"))
    ]
    degraded_accuracy = (
        round(_mean([item["ticket_field_accuracy"] for item in degraded_rows]), 3)
        if degraded_rows
        else None
    )
    fifo_precision = _fifo_break_precision(rows)
    return {
        "scenario_count": len(rows),
        "passed_count": sum(1 for item in rows if item["passed"]),
        "failed_count": sum(1 for item in rows if not item["passed"]),
        "decision_match_at_1": _ratio(rows, "decision_match_at_1"),
        "constraint_violation_rate": _ratio(rows, "constraint_violation"),
        "ticket_field_accuracy": round(_mean([item["ticket_field_accuracy"] for item in rows]), 3),
        "ticket_field_accuracy_pdf_or_image_degraded": degraded_accuracy,
        "exception_f1": exception_macro_f1,
        "exception_macro_f1": exception_macro_f1,
        "fifo_break_justified_precision": (
            round(fifo_precision, 3) if fifo_precision is not None else None
        ),
        "audit_completeness": _ratio(rows, "audit_complete"),
        "tool_call_success_rate": _ratio(rows, "tool_call_success"),
        "avg_tool_call_count": round(
            _mean([float(item.get("tool_call_count", 0)) for item in rows]), 3
        ),
        "avg_planner_step_count": round(
            _mean([float(item.get("planner_step_count", 0)) for item in rows]), 3
        ),
        "tool_error_count": int(sum(int(item.get("tool_error_count", 0)) for item in rows)),
        "tool_error_rate": _positive_ratio(rows, "tool_error_count"),
        "latency_p50": _percentile(latencies, 0.50),
        "latency_p75": _percentile(latencies, 0.75),
        "latency_p90": _percentile(latencies, 0.90),
        "latency_p95": _percentile(latencies, 0.95),
        "latency_max": max(latencies) if latencies else 0,
        "latency_p50_ms": _percentile(latencies, 0.50),
        "latency_p75_ms": _percentile(latencies, 0.75),
        "latency_p90_ms": _percentile(latencies, 0.90),
        "latency_p95_ms": _percentile(latencies, 0.95),
        "latency_max_ms": max(latencies) if latencies else 0,
        "p50_latency_ms": _percentile(latencies, 0.50),
        "p95_latency_ms": _percentile(latencies, 0.95),
        **_phase_latency_percentiles(rows),
        "timeout_rate": _ratio(rows, "timeout"),
        "manual_review_rate": _ratio(rows, "manual_review_flag"),
    }


def _phase_latency_percentiles(rows: list[dict[str, Any]]) -> dict[str, int]:
    metrics: dict[str, int] = {}
    for key in (
        "latency_ms_preprocess",
        "latency_ms_model",
        "latency_ms_rules",
        "latency_ms_audit",
    ):
        values = [int(item.get(key, 0)) for item in rows]
        metrics[f"{key}_p50"] = _percentile(values, 0.50)
        metrics[f"{key}_p95"] = _percentile(values, 0.95)
    return metrics


def _ratio(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for item in rows if item.get(key)) / len(rows), 3) if rows else 0.0


def _positive_ratio(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for item in rows if item.get(key, 0) > 0) / len(rows), 3) if rows else 0.0


def _mean(values: list[float | None]) -> float:
    observed = [value for value in values if value is not None]
    return sum(observed) / len(observed) if observed else 0.0


def _macro_f1(rows: list[dict[str, Any]]) -> float:
    labels = {item["expected_primary_exception"] for item in rows} | {
        item["observed_primary_exception"] for item in rows
    }
    if not labels:
        return 0.0
    scores: list[float] = []
    for label in labels:
        true_positive = sum(
            1
            for item in rows
            if item["expected_primary_exception"] == label
            and item["observed_primary_exception"] == label
        )
        false_positive = sum(
            1
            for item in rows
            if item["expected_primary_exception"] != label
            and item["observed_primary_exception"] == label
        )
        false_negative = sum(
            1
            for item in rows
            if item["expected_primary_exception"] == label
            and item["observed_primary_exception"] != label
        )
        denominator = (2 * true_positive) + false_positive + false_negative
        scores.append((2 * true_positive / denominator) if denominator else 0.0)
    return _mean(scores)


def _fifo_break_precision(rows: list[dict[str, Any]]) -> float | None:
    breaks = [item for item in rows if item["fifo_break"]]
    if not breaks:
        return None
    justified = sum(1 for item in breaks if item["fifo_break_expected"])
    return justified / len(breaks)


def _percentile(values: list[int], quantile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * quantile)
    return ordered[index]
