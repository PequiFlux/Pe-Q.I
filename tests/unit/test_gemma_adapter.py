from __future__ import annotations

import pytest

from app.domain.errors import PequiFluxError, SchemaViolationError
from app.domain.models import DocumentBundle, ParsedTicket
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime


def _bundle() -> DocumentBundle:
    return DocumentBundle(
        request_id="REQ-001",
        document_ref="data/tickets/ticket_teste.pdf",
        content_type="application/pdf",
        sha256="abc123",
        candidate_truck_ids=["TRK-001"],
    )


class DictRuntime:
    def generate_structured(self, **kwargs):
        return {
            "ticket_id": "TCK-001",
            "truck_id": "TRK-001",
            "vehicle_type": "truck",
            "document_status": "clear",
            "load_condition": "dry",
            "parse_confidence": 0.92,
        }

    def summarize(self, **kwargs) -> str:
        return "Decision summary."


class InvalidRuntime:
    def generate_structured(self, **kwargs):
        return {"ticket_id": "TCK-001", "parse_confidence": 2.0}

    def summarize(self, **kwargs) -> str:
        return ""


class FailingRuntime:
    def generate_structured(self, **kwargs):
        raise TimeoutError("network timeout")

    def summarize(self, **kwargs) -> str:
        raise TimeoutError("network timeout")


def test_gemma_adapter_fails_closed_without_runtime() -> None:
    with pytest.raises(PequiFluxError, match="MODEL_RUNTIME_UNAVAILABLE"):
        GemmaAdapter().parse_ticket_document(_bundle())


def test_gemma_adapter_validates_dict_runtime_output() -> None:
    ticket = GemmaAdapter(runtime=DictRuntime()).parse_ticket_document(_bundle())

    assert isinstance(ticket, ParsedTicket)
    assert ticket.ticket_id == "TCK-001"
    assert ticket.parse_confidence == 0.92


def test_gemma_adapter_rejects_invalid_schema_output() -> None:
    with pytest.raises(SchemaViolationError):
        GemmaAdapter(runtime=InvalidRuntime()).parse_ticket_document(_bundle())


def test_gemma_adapter_wraps_runtime_failures_as_formal_errors() -> None:
    with pytest.raises(PequiFluxError, match="MODEL_RUNTIME_ERROR"):
        GemmaAdapter(runtime=FailingRuntime()).parse_ticket_document(_bundle())


def test_text_runtime_is_limited_to_text_plain_fixtures() -> None:
    with pytest.raises(PequiFluxError, match="TEXT_RUNTIME_REQUIRES_TEXT_TICKET"):
        GemmaAdapter(runtime=TextTicketRuntime()).parse_ticket_document(_bundle())
