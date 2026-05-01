from __future__ import annotations

from app.adapters.document_adapter import build_document_bundle
from app.domain.models import ParsedTicket
from app.gemma import GemmaAdapter


class DemoRuntime:
    def generate_structured(self, **kwargs):
        return ParsedTicket(ticket_id="TCK-DEMO", truck_id="TRK-DEMO", parse_confidence=0.9)

    def summarize(self, **kwargs) -> str:
        return "Demo summary."


if __name__ == "__main__":
    bundle = build_document_bundle(
        request_id="REQ-DEMO",
        document_ref="data/tickets/ticket_teste.pdf",
        content_type="application/pdf",
        candidate_truck_ids=["TRK-DEMO"],
    )
    result = GemmaAdapter(runtime=DemoRuntime()).parse_ticket_document(bundle)
    print(result.model_dump())
