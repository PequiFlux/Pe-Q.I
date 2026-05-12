from __future__ import annotations

from app.domain.models import DocumentBundle, OcrHint


def generate_ocr_hints(bundle: DocumentBundle) -> list[OcrHint]:
    if bundle.extracted_text:
        return [
            OcrHint(
                hint_id=f"{bundle.request_id}-extracted-text",
                source_ref=bundle.document_ref,
                text=bundle.extracted_text,
                confidence=0.85,
                available=True,
            )
        ]
    if bundle.rendered_pages:
        return [
            OcrHint(
                hint_id=f"{bundle.request_id}-ocr-unavailable",
                source_ref=bundle.rendered_pages[0],
                text="",
                confidence=0.0,
                available=False,
                error="OCR engine not configured; hint omitted without changing decision logic.",
            )
        ]
    return []
