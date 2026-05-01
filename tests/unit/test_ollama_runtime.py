from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import pytest

from app.domain.errors import PequiFluxError
from app.domain.models import ParsedTicket
from app.gemma.ollama_runtime import OllamaGemmaRuntime


class CapturingOllamaRuntime(OllamaGemmaRuntime):
    def __init__(self) -> None:
        super().__init__(base_url="http://gemma:11434", model="gemma4:latest")
        self.payload: dict[str, Any] | None = None

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        self.payload = payload
        return {"response": '{"parse_confidence": 0.8}'}


def test_ollama_runtime_sends_rendered_pdf_pages_as_images(tmp_path: Path) -> None:
    page_path = tmp_path / "page.png"
    page_path.write_bytes(b"image-bytes")
    runtime = CapturingOllamaRuntime()

    runtime.generate_structured(
        prompt="parse",
        response_model=ParsedTicket,
        metadata={
            "document_ref": "ticket.pdf",
            "content_type": "application/pdf",
            "rendered_pages": [str(page_path)],
        },
    )

    assert runtime.payload is not None
    assert runtime.payload["images"] == [base64.b64encode(b"image-bytes").decode("ascii")]


def test_ollama_runtime_fails_closed_when_pdf_has_no_rendered_pages() -> None:
    runtime = CapturingOllamaRuntime()

    with pytest.raises(PequiFluxError, match="PDF_RENDERED_PAGES_REQUIRED"):
        runtime.generate_structured(
            prompt="parse",
            response_model=ParsedTicket,
            metadata={"document_ref": "ticket.pdf", "content_type": "application/pdf"},
        )
