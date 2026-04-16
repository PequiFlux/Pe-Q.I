from __future__ import annotations

import hashlib
from pathlib import Path

from app.domain.errors import PequiFluxError
from app.domain.models import DocumentBundle, TicketContentType

ALLOWED_CONTENT_TYPES: set[str] = {"application/pdf", "image/png", "image/jpeg", "text/plain"}


def build_document_bundle(
    *,
    request_id: str,
    document_ref: str,
    content_type: TicketContentType,
    candidate_truck_ids: list[str],
) -> DocumentBundle:
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise PequiFluxError("UNSUPPORTED_CONTENT_TYPE", f"Unsupported content type: {content_type}")

    path = Path(document_ref)
    if not path.exists():
        raise PequiFluxError("DOCUMENT_NOT_FOUND", f"Document not found: {document_ref}")

    content = path.read_bytes()
    extracted_text = None
    if path.suffix.lower() in {".txt", ".md"}:
        extracted_text = path.read_text(encoding="utf-8")

    return DocumentBundle(
        request_id=request_id,
        document_ref=document_ref,
        content_type=content_type,
        sha256=hashlib.sha256(content).hexdigest(),
        extracted_text=extracted_text,
        candidate_truck_ids=candidate_truck_ids,
    )
