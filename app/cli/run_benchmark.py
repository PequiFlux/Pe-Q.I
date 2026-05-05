from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from app.domain.models import DecisionRequest
from app.gemma.runtime_factory import build_gemma_adapter
from app.orchestration.orchestrator import DecisionOrchestrator
from app.services.structured_ticket_parser import (
    load_expected_ticket_fixture,
    parse_structured_ticket_document,
)
from bench.metrics import compute_variant_metrics
from bench.reporting import render_summary_csv
from bench.rows import build_payload_row, build_raw_fifo_row, has_constraint_violation
from bench.rows import ticket_field_accuracy as compute_ticket_field_accuracy
from bench.validation import validate_payload
from bench.variants import FULL_VARIANT, OPERATIONAL_FIFO_VARIANT, OPERATIONAL_VARIANTS
from bench.variants import REPORT_VARIANTS, report_variant_name


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all Yard Copilot scenarios from a manifest.")
    parser.add_argument("--manifest", default="scenarios/manifest.json")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = Path(args.output_dir or f"bench/reports/extended/{run_id}")
    output_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = DecisionOrchestrator(gemma_adapter=build_gemma_adapter())

    per_scenario: list[dict[str, object]] = []
    failures: list[str] = []
    for case in manifest["cases"]:
        base_request = DecisionRequest.model_validate(case["request"])
        expected = json.loads(Path(case["files"]["expected_decision"]).read_text(encoding="utf-8"))
        expected_ticket = load_expected_ticket_fixture(base_request.ticket_ref)
        if expected_ticket is None:
            expected_ticket = parse_structured_ticket_document(
                request_id=base_request.request_id,
                document_ref=base_request.ticket_ref,
                content_type=base_request.ticket_content_type,
                candidate_truck_ids=[],
            )

        payload_by_variant = {}
        for variant in OPERATIONAL_VARIANTS:
            request = base_request.model_copy(update={"variant": variant})
            payload_by_variant[variant] = orchestrator.run_decision(request)

        per_scenario.append(
            build_raw_fifo_row(
                request=base_request,
                expected=expected,
                fifo_safe_payload=payload_by_variant[OPERATIONAL_FIFO_VARIANT],
            )
        )

        for variant in OPERATIONAL_VARIANTS:
            payload = payload_by_variant[variant]
            observed_ticket = payload.benchmark_observed.get("parsed_ticket", {})
            accuracy = (
                0.0
                if variant == OPERATIONAL_FIFO_VARIANT
                else compute_ticket_field_accuracy(
                    observed_ticket, expected_ticket.model_dump(mode="json")
                )
            )
            row = build_payload_row(
                scenario_id=case["scenario_id"],
                variant=report_variant_name(variant),
                payload=payload,
                expected=expected,
                ticket_field_accuracy=accuracy,
            )

            try:
                if not args.no_validate and variant == FULL_VARIANT:
                    validate_payload(payload, expected)
                if variant == FULL_VARIANT and has_constraint_violation(payload):
                    raise SystemExit("Recommended pair violates a hard constraint.")
                passed = True
                error = None
            except SystemExit as exc:
                passed = False
                error = str(exc)
                failures.append(f"{case['scenario_id']}:{variant}: {error}")

            row["passed"] = passed
            row["error"] = error
            per_scenario.append(row)

    full_rows = [item for item in per_scenario if item["variant"] == "full"]
    variant_metrics = {}
    for variant in REPORT_VARIANTS:
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


if __name__ == "__main__":
    main()
