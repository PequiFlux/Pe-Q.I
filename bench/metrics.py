from __future__ import annotations

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

