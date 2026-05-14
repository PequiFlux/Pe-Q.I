from __future__ import annotations

from collections.abc import Callable
from typing import Any


GatePredicate = Callable[[Any], bool]


GATE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "metric": "constraint_violation_rate",
        "target": "== 0.0",
        "predicate": lambda value: value == 0.0,
        "action": "fix hard-constraint evaluation before changing model behavior",
    },
    {
        "metric": "audit_completeness",
        "target": "== 1.0",
        "predicate": lambda value: value == 1.0,
        "action": "complete audit payload inputs, evidence, rules, ranking, and runtime metadata",
    },
    {
        "metric": "decision_match_at_1",
        "target": ">= 0.92",
        "predicate": lambda value: value >= 0.92,
        "action": "review perception, exception classification, ranking, and labels",
    },
    {
        "metric": "ticket_field_accuracy",
        "target": ">= 0.95",
        "predicate": lambda value: value >= 0.95,
        "action": "improve field extraction schema, prompts, or labels",
    },
    {
        "metric": "ticket_field_accuracy_pdf_or_image_degraded",
        "target": ">= 0.9",
        "predicate": lambda value: value >= 0.90,
        "action": "improve preprocess, OCR hints, or field extraction evidence",
    },
    {
        "metric": "exception_macro_f1",
        "target": ">= 0.9",
        "predicate": lambda value: value >= 0.90,
        "action": "audit exception class hierarchy and ambiguous operator notes",
    },
    {
        "metric": "fifo_break_justified_precision",
        "target": ">= 0.95 or null with explicit no-break case",
        "predicate": lambda value: value is None or value >= 0.95,
        "action": "tighten FIFO break policy evidence and expected labels",
    },
    {
        "metric": "tool_call_success_rate",
        "target": ">= 0.98",
        "predicate": lambda value: value >= 0.98,
        "action": "fix tool whitelist, schemas, and fail-closed tool errors",
    },
    {
        "metric": "latency_p50_ms",
        "target": "<= 6000",
        "predicate": lambda value: value <= 6000,
        "action": "reduce preprocessing/model path or narrow demo runtime scope",
    },
    {
        "metric": "latency_p95_ms",
        "target": "<= 12000",
        "predicate": lambda value: value <= 12000,
        "action": "reduce tail latency before making demo latency claims",
    },
    {
        "metric": "timeout_rate",
        "target": "< 0.01",
        "predicate": lambda value: value < 0.01,
        "action": "bound model/runtime execution and report timeout causes",
    },
    {
        "metric": "manual_review_rate",
        "target": "<= 0.15",
        "predicate": lambda value: value <= 0.15,
        "action": "calibrate review thresholds without hiding parser failures",
    },
    {
        "metric": "no_expected_ticket_leakage",
        "target": "== true",
        "predicate": lambda value: value is True,
        "action": "remove expected_ticket sidecars from clean evaluation splits",
    },
)


ALIASES = {
    "exception_macro_f1": "exception_f1",
    "latency_p50_ms": "p50_latency_ms",
    "latency_p95_ms": "p95_latency_ms",
}


def evaluate_submission_gates(metrics: dict[str, Any]) -> dict[str, Any]:
    failed_gates: list[dict[str, Any]] = []
    for spec in GATE_SPECS:
        metric = spec["metric"]
        value = _metric_value(metrics, metric)
        predicate: GatePredicate = spec["predicate"]
        try:
            passed = value is not _MISSING and predicate(value)
        except TypeError:
            passed = False
        if not passed:
            failed_gates.append(
                {
                    "metric": metric,
                    "actual": None if value is _MISSING else value,
                    "target": spec["target"],
                    "recommended_action": spec["action"],
                }
            )
    return {
        "submission_ready": not failed_gates,
        "failed_gates": failed_gates,
    }


_MISSING = object()


def _metric_value(metrics: dict[str, Any], metric: str) -> Any:
    if metric in metrics:
        return metrics[metric]
    alias = ALIASES.get(metric)
    if alias and alias in metrics:
        return metrics[alias]
    return _MISSING
