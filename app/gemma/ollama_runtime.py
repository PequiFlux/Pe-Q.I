from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from app.domain.errors import PequiFluxError, SchemaViolationError


class OllamaGemmaRuntime:
    """Ollama-backed local Gemma runtime.

    The runtime is intentionally thin: it returns schema-shaped data or raises a
    formal error. It never falls back to another parser/model.
    """

    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 45.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_env(cls) -> "OllamaGemmaRuntime":
        return cls(
            base_url=os.getenv("GEMMA_BASE_URL", "http://gemma:11434"),
            model=os.getenv("GEMMA_MODEL", "gemma4:latest"),
            timeout_seconds=float(os.getenv("GEMMA_TIMEOUT_SECONDS", "45")),
        )

    def generate_structured(
        self,
        *,
        prompt: str,
        response_model: type,
        metadata: dict[str, Any],
    ) -> BaseModel | dict[str, Any]:
        if not issubclass(response_model, BaseModel):
            raise PequiFluxError("UNSUPPORTED_SCHEMA", "Ollama runtime requires a Pydantic schema.")

        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": _structured_prompt(prompt, response_model),
            "stream": False,
            "format": "json",
            "options": {"temperature": 0},
        }
        image = _image_payload(metadata)
        if image is not None:
            payload["images"] = [image]

        raw = self._post_json("/api/generate", payload)
        text = str(raw.get("response") or "").strip()
        if not text:
            raise SchemaViolationError("Ollama returned an empty structured response.")
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise SchemaViolationError("Ollama did not return valid JSON.") from exc

    def summarize(self, *, prompt: str, metadata: dict[str, Any]) -> str:
        raw = self._post_json(
            "/api/generate",
            {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0},
            },
        )
        summary = str(raw.get("response") or "").strip()
        if not summary:
            raise SchemaViolationError("Ollama returned an empty summary.")
        return summary

    def prewarm(self) -> None:
        self._post_json(
            "/api/generate",
            {
                "model": self.model,
                "prompt": "Return only: ok",
                "stream": False,
                "options": {"temperature": 0, "num_predict": 4},
            },
        )

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(
            f"{self.base_url}{path}",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise PequiFluxError("GEMMA_RUNTIME_HTTP_ERROR", body) from exc
        except (urllib.error.URLError, TimeoutError) as exc:
            raise PequiFluxError(
                "GEMMA_RUNTIME_UNAVAILABLE",
                f"Could not reach Gemma runtime at {self.base_url}.",
            ) from exc
        except json.JSONDecodeError as exc:
            raise SchemaViolationError("Gemma runtime returned non-JSON transport data.") from exc


def _structured_prompt(prompt: str, response_model: type[BaseModel]) -> str:
    schema = response_model.model_json_schema()
    return (
        f"{prompt}\n\n"
        "Return exactly one JSON object matching this JSON Schema. "
        "Do not include markdown, commentary, or extra keys.\n"
        f"{json.dumps(schema, sort_keys=True)}"
    )


def _image_payload(metadata: dict[str, Any]) -> str | None:
    content_type = str(metadata.get("content_type") or "")
    if content_type not in {"image/png", "image/jpeg"}:
        return None
    document_ref = metadata.get("document_ref")
    if not document_ref:
        raise PequiFluxError("DOCUMENT_REF_REQUIRED", "Image document_ref is required.")
    path = Path(str(document_ref))
    if not path.exists():
        raise PequiFluxError("DOCUMENT_NOT_FOUND", f"Document not found: {document_ref}")
    return base64.b64encode(path.read_bytes()).decode("ascii")
