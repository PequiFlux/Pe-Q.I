from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import DecisionRequest, FrontEndPayload
from app.orchestration.orchestrator import DecisionOrchestrator
from bench.metrics import compute_benchmark_metrics


class BenchmarkRunner:
    def __init__(self, orchestrator: DecisionOrchestrator) -> None:
        self.orchestrator = orchestrator

    def run_manifest(self, manifest_path: str) -> tuple[list[FrontEndPayload], dict[str, float]]:
        manifest = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
        payloads: list[FrontEndPayload] = []
        for case in manifest.get("cases", []):
            request = DecisionRequest.model_validate(case["request"])
            payloads.append(self.orchestrator.run_decision(request))
        return payloads, compute_benchmark_metrics(payloads)

