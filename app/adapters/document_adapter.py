from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from app.domain.errors import PequiFluxError
from app.domain.models import DocumentBundle, TicketContentType

ALLOWED_CONTENT_TYPES: set[str] = {"application/pdf", "image/png", "image/jpeg", "text/plain"}
DEFAULT_RENDER_DPI = 180
DEFAULT_MAX_RENDERED_PAGES = 2


def build_document_bundle(
    *,
    request_id: str,
    document_ref: str,
    content_type: TicketContentType,
    candidate_truck_ids: list[str],
    cache_dir: str | Path | None = None,
) -> DocumentBundle:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise PequiFluxError(
            "UNSUPPORTED_CONTENT_TYPE", f"Unsupported content type: {content_type}"
        )

    path = Path(document_ref)
    if not path.exists():
        raise PequiFluxError("DOCUMENT_NOT_FOUND", f"Document not found: {document_ref}")

    content = path.read_bytes()
    extracted_text = None
    rendered_pages: list[str] = []
    if path.suffix.lower() in {".txt", ".md"}:
        extracted_text = path.read_text(encoding="utf-8")
    elif content_type == "application/pdf":
        extracted_text, rendered_pages = _read_pdf_document(
            path=path,
            request_id=request_id,
            cache_dir=Path(cache_dir) if cache_dir is not None else _default_cache_dir(),
        )
    elif content_type in {"image/png", "image/jpeg"}:
        rendered_pages = [str(path)]

    return DocumentBundle(
        request_id=request_id,
        document_ref=document_ref,
        content_type=content_type,
        sha256=hashlib.sha256(content).hexdigest(),
        extracted_text=extracted_text,
        rendered_pages=rendered_pages,
        candidate_truck_ids=candidate_truck_ids,
    )


def _read_pdf_document(
    *,
    path: Path,
    request_id: str,
    cache_dir: Path,
) -> tuple[str | None, list[str]]:
    fitz = _load_pymupdf()
    try:
        document = fitz.open(path)
    except Exception as exc:
        raise PequiFluxError("PDF_OPEN_FAILED", f"Could not open PDF document: {path}") from exc

    if document.page_count == 0:
        document.close()
        raise PequiFluxError("PDF_EMPTY", f"PDF document has no pages: {path}")

    try:
        text_parts = [
            document.load_page(index).get_text("text").strip()
            for index in range(document.page_count)
        ]
        rendered_pages = _render_pdf_pages(
            document=document,
            request_id=request_id,
            source_path=path,
            cache_dir=cache_dir,
        )
    except PequiFluxError:
        raise
    except Exception as exc:
        raise PequiFluxError("PDF_RENDER_FAILED", f"Could not render PDF document: {path}") from exc
    finally:
        document.close()

    extracted_text = "\n\n".join(part for part in text_parts if part).strip() or None
    return extracted_text, rendered_pages


def _render_pdf_pages(
    *,
    document: Any,
    request_id: str,
    source_path: Path,
    cache_dir: Path,
) -> list[str]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    max_pages = min(document.page_count, _max_rendered_pages())
    rendered_pages: list[str] = []
    fitz = _load_pymupdf()
    zoom = _render_dpi() / 72
    render_matrix = fitz.Matrix(zoom, zoom)

    for page_index in range(max_pages):
        page = document.load_page(page_index)
        pixmap = page.get_pixmap(matrix=render_matrix, alpha=False)
        output_path = cache_dir / (
            f"{_safe_stem(request_id)}_{source_path.stem}_p{page_index + 1}.png"
        )
        pixmap.save(output_path)
        rendered_pages.append(str(output_path))

    if not rendered_pages:
        raise PequiFluxError("PDF_RENDER_EMPTY", f"PDF document rendered no pages: {source_path}")
    return rendered_pages


def _load_pymupdf() -> Any:
    try:
        import fitz
    except ImportError as exc:
        raise PequiFluxError(
            "PDF_RENDERER_UNAVAILABLE",
            "PyMuPDF is required to extract and render PDF tickets.",
        ) from exc
    return fitz


def _default_cache_dir() -> Path:
    return Path(os.getenv("PEQUIFLUX_CACHE_DIR", "cache")) / "doc_pages"


def _render_dpi() -> int:
    return int(os.getenv("PEQUIFLUX_PDF_RENDER_DPI", str(DEFAULT_RENDER_DPI)))


def _max_rendered_pages() -> int:
    return int(os.getenv("PEQUIFLUX_MAX_RENDERED_PAGES", str(DEFAULT_MAX_RENDERED_PAGES)))


def _safe_stem(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_"} else "_" for character in value
    )
