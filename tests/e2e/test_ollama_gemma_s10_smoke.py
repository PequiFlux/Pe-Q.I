from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from app.gemma.adapter import GemmaAdapter
from app.gemma.ollama_runtime import OllamaGemmaRuntime
from app.orchestration.orchestrator import DecisionOrchestrator
from app.ui.scenario_loader import build_request_from_inputs
from app.ui.scenario_loader import load_case_defaults


pytestmark = pytest.mark.skipif(
    not os.getenv("GEMMA_BASE_URL"),
    reason="GEMMA_BASE_URL is not configured for manual Ollama/Gemma smoke tests.",
)


def test_ollama_gemma_s10_smoke(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama")

    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    case = next(
        item for item in manifest["cases"] if item["scenario_id"] == "S10_FIFO_BREAK_JUSTIFIED"
    )
    inputs = load_case_defaults(case)
    inputs["uploaded_ticket"] = None

    request, error = build_request_from_inputs(
        inputs,
        scenario_id=case["scenario_id"],
        variant="full",
    )
    assert error is None
    assert request is not None

    payload = DecisionOrchestrator(
        gemma_adapter=GemmaAdapter(runtime=OllamaGemmaRuntime.from_env())
    ).run_decision(request)

    assert payload.scenario_id == "S10_FIFO_BREAK_JUSTIFIED"
    assert payload.decision_status == "PREVIEW_READY"
    assert payload.audit_record is not None
    assert payload.audit_record.tool_calls
    assert all(
        record.purpose != "Deterministic CI tool intent."
        for record in payload.audit_record.tool_calls
        if record.status == "executed"
    )
    assert payload.gemma_visible_summary.parsed_fields
    assert payload.gemma_visible_summary.exception_label
