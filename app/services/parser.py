from __future__ import annotations

from app.adapters.document_adapter import build_document_bundle
from app.domain.models import ParsedTicket
from app.gemma.adapter import GemmaAdapter


def parse_ticket_document(
    *,
    request_id: str,
    document_ref: str,
    content_type: str,
    candidate_truck_ids: list[str],
    gemma_adapter: GemmaAdapter,
) -> ParsedTicket:
    bundle = build_document_bundle(
        request_id=request_id,
        document_ref=document_ref,
        content_type=content_type,
        candidate_truck_ids=candidate_truck_ids,
    )
    return gemma_adapter.parse_ticket_document(bundle)

