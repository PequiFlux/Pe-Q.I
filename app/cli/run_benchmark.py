from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.domain.models import DecisionRequest
from app.gemma.runtime_factory import build_gemma_adapter
from app.orchestration.orchestrator import DecisionOrchestrator
from app.services.structured_ticket_parser import parse_structured_ticket_document
from bench.metrics import compute_variant_metrics
from bench.reporting import render_summary_csv
from bench.validation import validate_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all Yard Copilot scenarios from a manifest.")
    parser.add_argument("--manifest", default="scenarios/manifest.json")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir or f"bench/reports/{run_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = DecisionOrchestrator(gemma_adapter=build_gemma_adapter())

    per_scenario: list[dict[str, Any]] = []
    failures: list[str] = []
    variants = ("fifo", "heuristic", "full")
    for case in manifest["cases"]:
        base_request = DecisionRequest.model_validate(case["request"])
        expected = json.loads(Path(case["files"]["expected_decision"]).read_text(encoding="utf-8"))
        expected_ticket = parse_structured_ticket_document(
            request_id=base_request.request_id,
            document_ref=base_request.ticket_ref,
            content_type=base_request.ticket_content_type,
            candidate_truck_ids=[],
        )
        for variant in variants:
            request = base_request.model_copy(update={"variant": variant})
            payload = orchestrator.run_decision(request)
            match_at_1 = _matches_expected(payload, expected)
            constraint_violation = _has_constraint_violation(payload)
            fifo_break = bool(
                payload.recommended_truck
                and payload.recommended_truck.queue_position_before != 1
            )
            observed_ticket = payload.benchmark_observed.get("parsed_ticket", {})
            observed_primary_exception = str(
                payload.benchmark_observed.get("primary_exception", "UNKNOWN")
            )
            ticket_field_accuracy = (
                0.0
                if variant == "fifo"
                else _ticket_field_accuracy(observed_ticket, expected_ticket.model_dump(mode="json"))
            )
            audit_complete = _audit_complete(payload)
            fifo_break_justified = fifo_break and expected["fifo_break_expected"]

            try:
                if not args.no_validate and variant == "full":
                    validate_payload(payload, expected)
                if variant == "full" and constraint_violation:
                    raise SystemExit("Recommended pair violates a hard constraint.")
                passed = True
                error = None
            except SystemExit as exc:
                passed = False
                error = str(exc)
                failures.append(f"{case['scenario_id']}:{variant}: {error}")

            per_scenario.append(
                {
                    "scenario_id": case["scenario_id"],
                    "variant": variant,
                    "passed": passed,
                    "error": error,
                    "decision_match_at_1": match_at_1,
                    "constraint_violation": constraint_violation,
                    "ticket_field_accuracy": ticket_field_accuracy,
                    "observed_primary_exception": observed_primary_exception,
                    "expected_primary_exception": expected["expected_primary_exception"],
                    "exception_match": (
                        observed_primary_exception == expected["expected_primary_exception"]
                    ),
                    "audit_complete": audit_complete,
                    "decision_status": payload.decision_status,
                    "recommended_truck": (
                        payload.recommended_truck.truck_id if payload.recommended_truck else None
                    ),
                    "recommended_destination": (
                        payload.recommended_destination.destination_id
                        if payload.recommended_destination
                        else None
                    ),
                    "fifo_break": fifo_break,
                    "fifo_break_expected": expected["fifo_break_expected"],
                    "fifo_break_justified": fifo_break_justified,
                    "rejected_count": (
                        len(payload.audit_record.rejected_candidates) if payload.audit_record else 0
                    ),
                    "latency_ms_total": sum(payload.latency_ms.values()),
                }
            )

    full_rows = [item for item in per_scenario if item["variant"] == "full"]
    variant_metrics = {}
    for variant in variants:
        rows = [item for item in per_scenario if item["variant"] == variant]
        variant_metrics[variant] = compute_variant_metrics(rows)

    metrics = {
        "scenario_count": len(full_rows),
        "passed_count": sum(1 for item in full_rows if item["passed"]),
        "failed_count": sum(1 for item in full_rows if not item["passed"]),
        "variant_metrics": variant_metrics,
    }

    (output_dir / "per_scenario.json").write_text(
        json.dumps(per_scenario, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_dir / "summary.csv").write_text(render_summary_csv(per_scenario), encoding="utf-8")

    print(json.dumps({"run_id": run_id, "output_dir": str(output_dir), **metrics}, indent=2))
    if failures:
        raise SystemExit("Benchmark validation failed: " + "; ".join(failures))


def _matches_expected(payload, expected: dict[str, Any]) -> bool:
    truck_id = payload.recommended_truck.truck_id if payload.recommended_truck else None
    destination_id = payload.recommended_destination.destination_id if payload.recommended_destination else None
    fifo_break = bool(payload.recommended_truck and payload.recommended_truck.queue_position_before != 1)
    return (
        payload.decision_status == expected["expected_status"]
        and truck_id in expected["acceptable_trucks"]
        and destination_id in expected["acceptable_destinations"]
        and fifo_break == expected["fifo_break_expected"]
    )


def _has_constraint_violation(payload) -> bool:
    if not payload.recommended_truck or not payload.recommended_destination or not payload.audit_record:
        return False
    truck_id = payload.recommended_truck.truck_id
    destination_id = payload.recommended_destination.destination_id
    for rejected in payload.audit_record.rejected_candidates:
        if rejected["truck_id"] == truck_id and rejected["destination_id"] == destination_id:
            return True
    return False


def _ticket_field_accuracy(observed: dict[str, Any], expected: dict[str, Any]) -> float:
    fields = [
        "ticket_id",
        "truck_id",
        "vehicle_type",
        "document_status",
        "document_block_flags",
        "load_condition",
        "contract_priority_flag",
        "destination_constraints",
    ]
    matches = sum(1 for field in fields if observed.get(field) == expected.get(field))
    return round(matches / len(fields), 3)


def _audit_complete(payload) -> bool:
    audit = payload.audit_record
    if audit is None:
        return False
    has_recommendation = payload.recommended_truck is None or audit.recommended_pair is not None
    return all(
        [
            bool(audit.hard_constraints_checked),
            bool(audit.provenance),
            bool(audit.latencies_ms),
            {"queue_csv_ref", "ticket_ref"}.issubset(audit.source_hashes),
            has_recommendation,
        ]
    )


if __name__ == "__main__":
    main()
