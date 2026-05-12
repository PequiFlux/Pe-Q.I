from __future__ import annotations

from pathlib import Path

from app.document.preprocess import detect_rotation_hint
from app.document.preprocess import generate_document_views
from app.document.preprocess import normalize_image


def test_normalize_image_copies_without_mutating_source(tmp_path: Path) -> None:
    source = tmp_path / "ticket_rotated.png"
    source.write_bytes(b"\x89PNG\r\n\x1a\nsource")
    cache_dir = tmp_path / "cache"

    view = normalize_image(image_ref=str(source), request_id="REQ-001", cache_dir=cache_dir)

    assert Path(view.path).exists()
    assert Path(view.path) != source
    assert source.read_bytes() == b"\x89PNG\r\n\x1a\nsource"
    assert view.purpose == "normalized_image"
    assert view.rotation_hint == 90
    assert len(view.sha256) == 64


def test_generate_document_views_wraps_pdf_rendered_pages(tmp_path: Path) -> None:
    page = tmp_path / "page-1.png"
    page.write_bytes(b"\x89PNG\r\n\x1a\npage")

    views = generate_document_views(
        document_ref="ticket.pdf",
        content_type="application/pdf",
        request_id="REQ-PDF",
        rendered_pages=[str(page)],
        cache_dir=tmp_path,
    )

    assert [view.view_id for view in views] == ["REQ-PDF-page-1"]
    assert views[0].purpose == "pdf_rendered_page"
    assert views[0].source_ref == "ticket.pdf"


def test_detect_rotation_hint_is_name_based_and_optional(tmp_path: Path) -> None:
    assert detect_rotation_hint(tmp_path / "ticket_rotated.png") == 90
    assert detect_rotation_hint(tmp_path / "ticket.png") is None
