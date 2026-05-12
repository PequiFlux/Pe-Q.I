from __future__ import annotations

from app.domain.models import FieldEvidence
from app.domain.models import FieldExtractionResult
from app.gemma.calibration import DEFAULT_CALIBRATION_POLICY
from app.gemma.calibration import calibrate_field_extraction


def test_low_confidence_critical_field_requires_manual_review() -> None:
    extraction = FieldExtractionResult(
        fields={
            "truck_id": FieldEvidence(
                value="TRK-001",
                confidence=0.69,
                evidence=["line:truck_id"],
                source="gemma4:e4b",
            ),
            "document_status": FieldEvidence(
                value="valid",
                confidence=0.95,
                evidence=["line:status"],
                source="gemma4:e4b",
            ),
            "load_condition": FieldEvidence(
                value="dry",
                confidence=0.95,
                evidence=["line:condition"],
                source="gemma4:e4b",
            ),
        },
        needs_review=False,
        reason="",
    )

    result = calibrate_field_extraction(extraction)

    assert result.threshold_version == DEFAULT_CALIBRATION_POLICY.threshold_version
    assert result.manual_review_required is True
    assert result.reasons == ["truck_id confidence 0.69 below threshold 0.7"]


def test_source_conflict_or_ocr_disagreement_requires_review() -> None:
    extraction = FieldExtractionResult(
        fields={
            "truck_id": FieldEvidence(
                value="TRK-001",
                confidence=0.95,
                evidence=["line:truck_id"],
                source="gemma4:e4b",
            ),
            "document_status": FieldEvidence(
                value="valid",
                confidence=0.95,
                evidence=["line:status"],
                source="gemma4:e4b",
            ),
            "load_condition": FieldEvidence(
                value="dry",
                confidence=0.95,
                evidence=["line:condition"],
                source="gemma4:e4b",
            ),
        },
        needs_review=False,
        reason="",
    )

    result = calibrate_field_extraction(
        extraction,
        source_conflicts=["ticket destination conflicts with queue destination"],
        ocr_model_disagreements=["OCR truck_id TRK-007 differs from model TRK-001"],
    )

    assert result.manual_review_required is True
    assert result.reasons == [
        "ticket destination conflicts with queue destination",
        "OCR truck_id TRK-007 differs from model TRK-001",
    ]
