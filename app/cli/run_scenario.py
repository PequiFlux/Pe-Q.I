from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.domain.models import DecisionRequest, FrontEndPayload
from app.gemma.runtime_factory import build_gemma_adapter
from app.orchestration.orchestrator import DecisionOrchestrator
from bench.validation import validate_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run one Yard Copilot scenario from the manifest.")
    parser.add_argument("--manifest", default="scenarios/manifest.json")
    parser.add_argument("--scenario", default="S01_BASELINE")
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()

    manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    case = _find_case(manifest, args.scenario)
    request = DecisionRequest.model_validate(case["request"])

    orchestrator = DecisionOrchestrator(gemma_adapter=build_gemma_adapter())
    payload = orchestrator.run_decision(request)

    expected = json.loads(Path(case["files"]["expected_decision"]).read_text(encoding="utf-8"))
    if not args.no_validate:
        validate_payload(payload, expected)

    print(json.dumps(_summary(payload), indent=2, sort_keys=True))


def _find_case(manifest: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    for case in manifest.get("cases", []):
        if case.get("scenario_id") == scenario_id:
            return case
    raise SystemExit(f"Scenario not found in manifest: {scenario_id}")


def _summary(payload: FrontEndPayload) -> dict[str, Any]:
    return {
        "request_id": payload.request_id,
        "scenario_id": payload.scenario_id,
        "variant": payload.variant,
        "decision_status": payload.decision_status,
        "recommended_truck": (
            payload.recommended_truck.model_dump(mode="json") if payload.recommended_truck else None
        ),
        "recommended_destination": (
            payload.recommended_destination.model_dump(mode="json")
            if payload.recommended_destination
            else None
        ),
        "reason_summary": payload.reason_summary,
        "fired_rules": payload.audit_record.fired_rules if payload.audit_record else [],
        "rejected_count": (
            len(payload.audit_record.rejected_candidates) if payload.audit_record else 0
        ),
        "latency_ms": payload.latency_ms,
        "benchmark_tags": payload.benchmark_tags,
        "confidence_notes": payload.confidence_notes,
    }


if __name__ == "__main__":
    main()
