from __future__ import annotations

from typing import Any

from app.domain.models import FrontEndPayload


def compute_benchmark_metrics(payloads: list[FrontEndPayload]) -> dict[str, float]:
    total = len(payloads)
    preview_ready = sum(1 for payload in payloads if payload.decision_status == "PREVIEW_READY")
    blocked = sum(1 for payload in payloads if payload.decision_status == "BLOCKED")
    review_required = sum(
        1 for payload in payloads if payload.decision_status == "REVIEW_REQUIRED"
    )
    return {
        "total_runs": float(total),
        "preview_ready_ratio": (preview_ready / total) if total else 0.0,
        "blocked_ratio": (blocked / total) if total else 0.0,
        "review_required_ratio": (review_required / total) if total else 0.0,
    }


def compute_variant_metrics(rows: list[dict[str, Any]]) -> dict[str, float | int]:
    return {
        "scenario_count": len(rows),
        "passed_count": sum(1 for item in rows if item["passed"]),
        "failed_count": sum(1 for item in rows if not item["passed"]),
        "decision_match_at_1": _ratio(rows, "decision_match_at_1"),
        "constraint_violation_rate": _ratio(rows, "constraint_violation"),
        "ticket_field_accuracy": round(_mean([item["ticket_field_accuracy"] for item in rows]), 3),
        "exception_f1": round(_macro_f1(rows), 3),
        "fifo_break_justified_precision": round(_fifo_break_precision(rows), 3),
        "audit_completeness": _ratio(rows, "audit_complete"),
        "latency_p50": _percentile([item["latency_ms_total"] for item in rows], 0.50),
        "latency_p95": _percentile([item["latency_ms_total"] for item in rows], 0.95),
        "p50_latency_ms": _percentile([item["latency_ms_total"] for item in rows], 0.50),
        "p95_latency_ms": _percentile([item["latency_ms_total"] for item in rows], 0.95),
    }


def _ratio(rows: list[dict[str, Any]], key: str) -> float:
    return round(sum(1 for item in rows if item[key]) / len(rows), 3) if rows else 0.0


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _macro_f1(rows: list[dict[str, Any]]) -> float:
    labels = {
        item["expected_primary_exception"] for item in rows
    } | {
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


def _fifo_break_precision(rows: list[dict[str, Any]]) -> float:
    breaks = [item for item in rows if item["fifo_break"]]
    if not breaks:
        return 0.0
    justified = sum(1 for item in breaks if item["fifo_break_expected"])
    return justified / len(breaks)


def _percentile(values: list[int], quantile: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    index = round((len(ordered) - 1) * quantile)
    return ordered[index]
