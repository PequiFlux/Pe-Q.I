from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import DecisionRequest
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.orchestration.orchestrator import DecisionOrchestrator
from bench.validation import validate_payload


def test_all_manifest_scenarios_run_end_to_end() -> None:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    orchestrator = DecisionOrchestrator(
        gemma_adapter=GemmaAdapter(runtime=TextTicketRuntime()),
    )

    for case in manifest["cases"]:
        request = DecisionRequest.model_validate(case["request"])
        payload = orchestrator.run_decision(request)
        expected = json.loads(Path(case["files"]["expected_decision"]).read_text(encoding="utf-8"))

        validate_payload(payload, expected)
