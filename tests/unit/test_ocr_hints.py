from __future__ import annotations

from app.document.ocr_hints import generate_ocr_hints
from app.domain.models import DocumentBundle


def test_ocr_hint_uses_extracted_text_as_auxiliary_signal() -> None:
    bundle = DocumentBundle(
        request_id="REQ-OCR",
        document_ref="ticket.pdf",
        content_type="application/pdf",
        sha256="abc",
        extracted_text="ticket_id: TCK-001",
        rendered_pages=["page-1.png"],
    )

    hints = generate_ocr_hints(bundle)

    assert len(hints) == 1
    assert hints[0].available is True
    assert hints[0].text == "ticket_id: TCK-001"
    assert hints[0].confidence == 0.85


def test_missing_ocr_engine_is_a_hint_not_pipeline_fallback() -> None:
    bundle = DocumentBundle(
        request_id="REQ-OCR",
        document_ref="ticket.png",
        content_type="image/png",
        sha256="abc",
        rendered_pages=["ticket.png"],
    )

    hints = generate_ocr_hints(bundle)

    assert len(hints) == 1
    assert hints[0].available is False
    assert hints[0].text == ""
    assert hints[0].error is not None
