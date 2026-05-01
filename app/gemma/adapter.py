from __future__ import annotations

from typing import Any, Protocol, TypeVar

from pydantic import ValidationError

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
    ) -> ModelT | dict[str, Any]:
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

        try:
            result = self.runtime.generate_structured(
                prompt=build_parse_ticket_prompt(bundle),
                response_model=ParsedTicket,
                metadata={
                    "request_id": bundle.request_id,
                    "document_ref": bundle.document_ref,
                    "content_type": bundle.content_type,
                    "sha256": bundle.sha256,
                    "rendered_pages": list(bundle.rendered_pages),
                },
            )
        except PequiFluxError:
            raise
        except Exception as exc:
            raise PequiFluxError(
                "MODEL_RUNTIME_ERROR",
                "Gemma runtime failed while parsing the ticket document.",
            ) from exc
        if isinstance(result, ParsedTicket):
            return result
        try:
            return ParsedTicket.model_validate(result)
        except ValidationError as exc:
            raise SchemaViolationError("Gemma runtime did not return a valid ParsedTicket.") from exc

    def summarize_decision(self, preview: DecisionPreview) -> str:
        if self.runtime is None:
            raise PequiFluxError(
                "MODEL_RUNTIME_UNAVAILABLE",
                "Gemma runtime is not configured; the system fails closed.",
            )
        try:
            summary = self.runtime.summarize(
                prompt=build_reason_summary_prompt(preview),
                metadata={"decision_id": preview.decision_id, "variant": preview.variant},
            )
        except PequiFluxError:
            raise
        except Exception as exc:
            raise PequiFluxError(
                "MODEL_RUNTIME_ERROR",
                "Gemma runtime failed while summarizing the decision.",
            ) from exc
        if not summary.strip():
            raise SchemaViolationError("Gemma runtime returned an empty decision summary.")
        return summary
