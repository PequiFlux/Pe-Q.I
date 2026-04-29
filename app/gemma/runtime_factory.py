from __future__ import annotations

import os

from app.domain.errors import PequiFluxError
from app.gemma.adapter import GemmaAdapter, StructuredGemmaRuntime
from app.gemma.ollama_runtime import OllamaGemmaRuntime
from app.gemma.text_runtime import TextTicketRuntime


def build_gemma_runtime() -> StructuredGemmaRuntime | None:
    runtime = os.getenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama").strip().lower()
    if runtime == "ollama":
        return OllamaGemmaRuntime.from_env()
    if runtime == "text":
        return TextTicketRuntime()
    if runtime in {"none", "disabled"}:
        return None
    raise PequiFluxError("UNKNOWN_GEMMA_RUNTIME", f"Unknown Gemma runtime: {runtime}")


def build_gemma_adapter() -> GemmaAdapter:
    return GemmaAdapter(runtime=build_gemma_runtime())
