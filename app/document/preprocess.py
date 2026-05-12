from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

from app.domain.models import DocumentView, TicketContentType


IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


def render_pdf_pages(
    *,
    rendered_pages: list[str],
    document_ref: str,
    request_id: str,
) -> list[DocumentView]:
    return [
        _view(
            view_id=f"{request_id}-page-{index}",
            source_ref=document_ref,
            path=Path(page_ref),
            purpose="pdf_rendered_page",
            rotation_hint=detect_rotation_hint(Path(page_ref)),
        )
        for index, page_ref in enumerate(rendered_pages, start=1)
    ]


def normalize_image(
    *,
    image_ref: str,
    request_id: str,
    cache_dir: str | Path,
) -> DocumentView:
    source = Path(image_ref)
    target_dir = Path(cache_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{_safe_stem(request_id)}-{source.name}"
    if source.resolve() != target.resolve():
        shutil.copy2(source, target)
    return _view(
        view_id=f"{request_id}-image-normalized",
        source_ref=image_ref,
        path=target,
        purpose="normalized_image",
        rotation_hint=detect_rotation_hint(target),
    )


def generate_document_views(
    *,
    document_ref: str,
    content_type: TicketContentType,
    request_id: str,
    rendered_pages: list[str],
    cache_dir: str | Path,
) -> list[DocumentView]:
    path = Path(document_ref)
    if content_type == "application/pdf":
        return render_pdf_pages(
            rendered_pages=rendered_pages,
            document_ref=document_ref,
            request_id=request_id,
        )
    if path.suffix.lower() in IMAGE_SUFFIXES:
        return [
            normalize_image(
                image_ref=document_ref,
                request_id=request_id,
                cache_dir=cache_dir,
            )
        ]
    return []


def detect_rotation_hint(path: Path) -> int | None:
    name = path.name.lower()
    if "rotated" in name or "rotate90" in name or "rotation_90" in name:
        return 90
    if "rotation_minus_90" in name or "rotate-90" in name:
        return -90
    return None


def _view(
    *,
    view_id: str,
    source_ref: str,
    path: Path,
    purpose: str,
    rotation_hint: int | None,
) -> DocumentView:
    return DocumentView(
        view_id=view_id,
        source_ref=source_ref,
        path=str(path),
        purpose=purpose,
        rotation_hint=rotation_hint,
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _safe_stem(value: str) -> str:
    return "".join(char if char.isalnum() or char in {"-", "_"} else "-" for char in value)
