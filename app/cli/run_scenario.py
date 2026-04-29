from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from app.domain.models import DecisionRequest, FrontEndPayload
from app.gemma.runtime_factory import build_gemma_adapter
from app.orchestration.orchestrator import DecisionOrchestrator


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
        _validate_payload(payload, expected)

    print(json.dumps(_summary(payload), indent=2, sort_keys=True))


def _find_case(manifest: dict[str, Any], scenario_id: str) -> dict[str, Any]:
    for case in manifest.get("cases", []):
        if case.get("scenario_id") == scenario_id:
            return case
    raise SystemExit(f"Scenario not found in manifest: {scenario_id}")


def _validate_payload(payload: FrontEndPayload, expected: dict[str, Any]) -> None:
    errors: list[str] = []
    if payload.decision_status != expected["expected_status"]:
        errors.append(f"status={payload.decision_status!s}, expected={expected['expected_status']}")

    truck_id = payload.recommended_truck.truck_id if payload.recommended_truck else None
    if truck_id not in expected["acceptable_trucks"]:
        errors.append(f"truck={truck_id}, acceptable={expected['acceptable_trucks']}")

    destination_id = payload.recommended_destination.destination_id if payload.recommended_destination else None
    if destination_id not in expected["acceptable_destinations"]:
        errors.append(f"destination={destination_id}, acceptable={expected['acceptable_destinations']}")

    fifo_break = bool(payload.recommended_truck and payload.recommended_truck.queue_position_before != 1)
    if fifo_break != expected["fifo_break_expected"]:
        errors.append(f"fifo_break={fifo_break}, expected={expected['fifo_break_expected']}")

    rejected_constraints = {
        failure["constraint_id"]
        for rejected in (payload.audit_record.rejected_candidates if payload.audit_record else [])
        for failure in rejected.get("failed_constraints", [])
    }
    missing_constraints = set(expected["required_constraints"]) - rejected_constraints
    if missing_constraints:
        errors.append(f"missing rejected constraints={sorted(missing_constraints)}")

    if errors:
        raise SystemExit("Scenario validation failed: " + "; ".join(errors))


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
        "rejected_count": len(payload.audit_record.rejected_candidates) if payload.audit_record else 0,
        "latency_ms": payload.latency_ms,
        "benchmark_tags": payload.benchmark_tags,
        "confidence_notes": payload.confidence_notes,
    }


if __name__ == "__main__":
    main()
