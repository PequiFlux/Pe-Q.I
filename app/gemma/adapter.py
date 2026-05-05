from __future__ import annotations

from typing import Any, Protocol, TypeVar

from pydantic import ValidationError

from app.domain.errors import PequiFluxError, SchemaViolationError
from app.domain.models import (
    DecisionPreview,
    DocumentBundle,
    ExceptionAssessment,
    ParsedTicket,
    QueueSnapshot,
    ResourceState,
    WeatherState,
)
from app.gemma.prompts import (
    build_exception_classification_prompt,
    build_parse_ticket_prompt,
    build_reason_summary_prompt,
)

ModelT = TypeVar("ModelT")


class StructuredGemmaRuntime(Protocol):
    def generate_structured(
        self,
        *,
        prompt: str,
        response_model: type[ModelT],
        metadata: dict[str, Any],
    ) -> ModelT | dict[str, Any]: ...

    def summarize(self, *, prompt: str, metadata: dict[str, Any]) -> str: ...


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
                    "extracted_text": bundle.extracted_text,
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
            raise SchemaViolationError(
                "Gemma runtime did not return a valid ParsedTicket."
            ) from exc

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

    def classify_exception(
        self,
        *,
        request_id: str,
        parsed_ticket: ParsedTicket | None,
        operator_note: str,
        weather_state: WeatherState,
        resource_state: list[ResourceState],
        queue_snapshot: QueueSnapshot,
    ) -> ExceptionAssessment:
        if self.runtime is None:
            raise PequiFluxError(
                "MODEL_RUNTIME_UNAVAILABLE",
                "Gemma runtime is not configured; the system fails closed.",
            )
        try:
            result = self.runtime.generate_structured(
                prompt=build_exception_classification_prompt(
                    request_id=request_id,
                    parsed_ticket=parsed_ticket,
                    operator_note=operator_note,
                    weather_state=weather_state,
                    resource_state=resource_state,
                    queue_snapshot=queue_snapshot,
                ),
                response_model=ExceptionAssessment,
                metadata={"request_id": request_id, "task": "classify_exception"},
            )
        except PequiFluxError:
            raise
        except Exception as exc:
            raise PequiFluxError(
                "MODEL_RUNTIME_ERROR",
                "Gemma runtime failed while classifying the operational exception.",
            ) from exc
        if isinstance(result, ExceptionAssessment):
            return result
        try:
            return ExceptionAssessment.model_validate(result)
        except ValidationError as exc:
            raise SchemaViolationError(
                "Gemma runtime did not return a valid ExceptionAssessment."
            ) from exc
