from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import CalibrationResult
from app.domain.models import FieldExtractionResult


CRITICAL_FIELDS = ("truck_id", "document_status", "load_condition")


@dataclass(frozen=True)
class CalibrationPolicy:
    threshold_version: str
    field_thresholds: dict[str, float]


DEFAULT_CALIBRATION_POLICY = CalibrationPolicy(
    threshold_version="field-calibration-v1",
    field_thresholds={
        "truck_id": 0.70,
        "document_status": 0.70,
        "load_condition": 0.70,
    },
)


def calibrate_field_extraction(
    extraction: FieldExtractionResult,
    *,
    policy: CalibrationPolicy = DEFAULT_CALIBRATION_POLICY,
    source_conflicts: list[str] | None = None,
    ocr_model_disagreements: list[str] | None = None,
) -> CalibrationResult:
    reasons: list[str] = []
    for field in CRITICAL_FIELDS:
        evidence = extraction.fields.get(field)
        threshold = policy.field_thresholds[field]
        if evidence is None:
            reasons.append(f"{field} missing")
            continue
        if evidence.confidence < threshold:
            reasons.append(
                f"{field} confidence {evidence.confidence:g} below threshold {threshold:g}"
            )

    if extraction.needs_review and extraction.reason:
        reasons.append(extraction.reason)
    reasons.extend(source_conflicts or [])
    reasons.extend(ocr_model_disagreements or [])

    return CalibrationResult(
        threshold_version=policy.threshold_version,
        manual_review_required=bool(reasons),
        reasons=reasons,
        field_thresholds=dict(policy.field_thresholds),
    )
