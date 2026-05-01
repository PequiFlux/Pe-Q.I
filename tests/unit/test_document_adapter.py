from __future__ import annotations

from pathlib import Path

from app.adapters.document_adapter import build_document_bundle


def test_pdf_ticket_is_extracted_and_rendered_for_multimodal_gemma(tmp_path: Path) -> None:
    bundle = build_document_bundle(
        request_id="REQ-PDF",
        document_ref="data/tickets/ticket_teste.pdf",
        content_type="application/pdf",
        candidate_truck_ids=["TRK-DEMO"],
        cache_dir=tmp_path,
    )

    assert bundle.extracted_text
    assert bundle.rendered_pages
    assert Path(bundle.rendered_pages[0]).read_bytes().startswith(b"\x89PNG\r\n\x1a\n")


def test_image_ticket_is_carried_as_multimodal_page(tmp_path: Path) -> None:
    image_path = tmp_path / "ticket.png"
    image_path.write_bytes(b"\x89PNG\r\n\x1a\n")

    bundle = build_document_bundle(
        request_id="REQ-IMAGE",
        document_ref=str(image_path),
        content_type="image/png",
        candidate_truck_ids=["TRK-DEMO"],
    )

    assert bundle.extracted_text is None
    assert bundle.rendered_pages == [str(image_path)]
