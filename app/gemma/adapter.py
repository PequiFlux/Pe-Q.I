from __future__ import annotations

from typing import Any, Protocol, TypeVar

from app.domain.errors import PequiFluxError, SchemaViolationError
from app.domain.models import DecisionPreview, DocumentBundle, ParsedTicket
from app.gemma.prompts import build_parse_ticket_prompt, build_reason_summary_prompt

ModelT = TypeVar("ModelT")


class StructuredGemmaRuntime(Protocol):
    def generate_structured(
        self,
        *,
        prompt: str,
        response_model: type[ModelT],
        metadata: dict[str, Any],
    ) -> ModelT:
        ...

    def summarize(self, *, prompt: str, metadata: dict[str, Any]) -> str:
        ...


class GemmaAdapter:
    """Schema-bound integration point for the configured Gemma runtime."""

    def __init__(self, runtime: StructuredGemmaRuntime | None = None) -> None:
        self.runtime = runtime

    def parse_ticket_document(self, bundle: DocumentBundle) -> ParsedTicket:
        if self.runtime is None:
            raise PequiFluxError(
                "MODEL_RUNTIME_UNAVAILABLE",
                "Gemma runtime is not configured; the system fails closed.",
            )

        result = self.runtime.generate_structured(
            prompt=build_parse_ticket_prompt(bundle),
            response_model=ParsedTicket,
            metadata={
                "request_id": bundle.request_id,
                "document_ref": bundle.document_ref,
                "content_type": bundle.content_type,
            },
        )
        if not isinstance(result, ParsedTicket):
            raise SchemaViolationError("Gemma runtime did not return a ParsedTicket instance.")
        return result

    def summarize_decision(self, preview: DecisionPreview) -> str:
        if self.runtime is None:
            raise PequiFluxError(
                "MODEL_RUNTIME_UNAVAILABLE",
                "Gemma runtime is not configured; the system fails closed.",
            )
        return self.runtime.summarize(
            prompt=build_reason_summary_prompt(preview),
            metadata={"decision_id": preview.decision_id, "variant": preview.variant},
        )

