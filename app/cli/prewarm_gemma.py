from __future__ import annotations

import json

from app.gemma.ollama_runtime import OllamaGemmaRuntime
from app.gemma.runtime_factory import build_gemma_runtime


def main() -> None:
    runtime = build_gemma_runtime()
    if runtime is None:
        raise SystemExit("Gemma runtime is disabled.")
    if isinstance(runtime, OllamaGemmaRuntime):
        runtime.prewarm()
        print(json.dumps({"runtime": "ollama", "model": runtime.model, "status": "ready"}))
        return
    print(json.dumps({"runtime": runtime.__class__.__name__, "status": "ready"}))


if __name__ == "__main__":
    main()
