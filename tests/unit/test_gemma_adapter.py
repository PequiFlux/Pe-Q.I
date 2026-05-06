from __future__ import annotations

import pytest

from app.domain.errors import PequiFluxError, SchemaViolationError
from app.domain.models import DocumentBundle, ParsedTicket, ToolCallIntent
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


def _text_fixture_bundle() -> DocumentBundle:
    return DocumentBundle(
        request_id="REQ-001",
        document_ref="scenarios/cases/S10_FIFO_BREAK_JUSTIFIED/ticket.txt",
        content_type="text/plain",
        sha256="abc123",
        extracted_text="\n".join(
            [
                "ticket_id: TCK-001",
                "truck_id: TRK-001",
                "vehicle_type: truck",
                "document_status: clear",
                "load_condition: dry",
                "parse_confidence: 0.92",
                "evidence_refs:",
                "- nota fiscal validada",
            ]
        ),
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


class ToolRuntime:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.last_prompt: str | None = None
        self.last_metadata: dict | None = None

    def generate_structured(self, **kwargs):
        self.last_prompt = kwargs["prompt"]
        self.last_metadata = kwargs["metadata"]
        return self.result

    def summarize(self, **kwargs) -> str:
        return "Decision summary."


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
    with pytest.raises(PequiFluxError, match="TEXT_RUNTIME_REQUIRES_EXPECTED_TICKET"):
        GemmaAdapter(runtime=TextTicketRuntime()).parse_ticket_document(_bundle())


def test_text_runtime_reads_fixture_text_from_metadata_not_prompt_marker() -> None:
    runtime = TextTicketRuntime()

    ticket = runtime.generate_structured(
        prompt="Prompt wording changed without embedded fixture text.",
        response_model=ParsedTicket,
        metadata={
            "content_type": "text/plain",
            "extracted_text": _text_fixture_bundle().extracted_text,
        },
    )

    assert isinstance(ticket, ParsedTicket)
    assert ticket.ticket_id == "TCK-001"
    assert ticket.evidence_refs == ["nota fiscal validada"]


def test_gemma_adapter_passes_extracted_text_as_runtime_metadata() -> None:
    ticket = GemmaAdapter(runtime=TextTicketRuntime()).parse_ticket_document(_text_fixture_bundle())

    assert ticket.truck_id == "TRK-001"
    assert ticket.parse_confidence == 0.92


def test_gemma_adapter_choose_tool_validates_runtime_intent() -> None:
    runtime = ToolRuntime(
        {
            "tool_name": "validate_hard_constraints",
            "request_id": "REQ-001",
            "purpose": "Validate candidate destinations.",
        }
    )

    intent = GemmaAdapter(runtime=runtime).choose_tool(
        request_id="REQ-001",
        current_state="INTERPRETED",
        allowed_tools=["validate_hard_constraints"],
        context_summary="Truth resolved.",
    )

    assert intent.tool_name == "validate_hard_constraints"
    assert runtime.last_metadata == {
        "request_id": "REQ-001",
        "task": "choose_tool",
        "current_state": "INTERPRETED",
        "allowed_tools": ["validate_hard_constraints"],
    }
    assert runtime.last_prompt is not None
    assert "ToolCallIntent schema" in runtime.last_prompt


def test_gemma_adapter_choose_tool_rejects_disallowed_tool() -> None:
    runtime = ToolRuntime(
        {
            "tool_name": "rank_candidates",
            "request_id": "REQ-001",
        }
    )

    with pytest.raises(PequiFluxError, match="MODEL_TOOL_NOT_ALLOWED"):
        GemmaAdapter(runtime=runtime).choose_tool(
            request_id="REQ-001",
            current_state="INTERPRETED",
            allowed_tools=["validate_hard_constraints"],
            context_summary="Truth resolved.",
        )


def test_gemma_adapter_choose_tool_rejects_request_id_mismatch() -> None:
    runtime = ToolRuntime(
        {
            "tool_name": "validate_hard_constraints",
            "request_id": "REQ-OTHER",
        }
    )

    with pytest.raises(PequiFluxError, match="MODEL_TOOL_REQUEST_ID_MISMATCH"):
        GemmaAdapter(runtime=runtime).choose_tool(
            request_id="REQ-001",
            current_state="INTERPRETED",
            allowed_tools=["validate_hard_constraints"],
            context_summary="Truth resolved.",
        )


def test_gemma_adapter_choose_tool_rejects_invalid_schema_output() -> None:
    runtime = ToolRuntime({"tool_name": "not_a_tool", "request_id": "REQ-001"})

    with pytest.raises(SchemaViolationError):
        GemmaAdapter(runtime=runtime).choose_tool(
            request_id="REQ-001",
            current_state="INTERPRETED",
            allowed_tools=["validate_hard_constraints"],
            context_summary="Truth resolved.",
        )


def test_text_runtime_returns_deterministic_tool_intent() -> None:
    intent = GemmaAdapter(runtime=TextTicketRuntime()).choose_tool(
        request_id="REQ-001",
        current_state="INTERPRETED",
        allowed_tools=["validate_hard_constraints", "rank_candidates"],
        context_summary="Truth resolved.",
    )

    assert intent.tool_name == "validate_hard_constraints"
    assert intent.request_id == "REQ-001"
    assert intent.purpose == "Deterministic CI tool intent."


def test_text_runtime_requires_tool_intent_metadata() -> None:
    with pytest.raises(PequiFluxError, match="TEXT_RUNTIME_TOOL_METADATA_REQUIRED"):
        TextTicketRuntime().generate_structured(
            prompt="Select a tool.",
            response_model=ToolCallIntent,
            metadata={"request_id": "REQ-001", "allowed_tools": []},
        )


def test_text_runtime_reads_expected_ticket_sidecar_for_multimodal_fixture() -> None:
    bundle = DocumentBundle(
        request_id="REQ-S03",
        document_ref="scenarios/cases/S03_WET_LOAD/ticket.png",
        content_type="image/png",
        sha256="abc123",
        rendered_pages=["scenarios/cases/S03_WET_LOAD/ticket.png"],
        candidate_truck_ids=["TRK-001"],
    )

    ticket = GemmaAdapter(runtime=TextTicketRuntime()).parse_ticket_document(bundle)

    assert ticket.ticket_id == "TCK-S03-001"
    assert ticket.load_condition.value == "wet"
