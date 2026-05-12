from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from app.domain.errors import PequiFluxError
from app.domain.models import DecisionRequest
from app.gemma.runtime_factory import build_gemma_adapter
from app.orchestration.orchestrator import DecisionOrchestrator
from app.services.structured_ticket_parser import (
    load_expected_ticket_fixture,
    parse_structured_ticket_document,
)
from bench.metrics import compute_variant_metrics
from bench.reporting import build_error_analysis_rows
from bench.reporting import render_error_analysis_csv
from bench.reporting import render_summary_csv
from bench.rows import build_payload_row, build_raw_fifo_row, has_constraint_violation
from bench.rows import ticket_field_accuracy as compute_ticket_field_accuracy
from bench.validation import validate_payload
from bench.variants import FIFO_SAFE_VARIANT, FULL_VARIANT, HEURISTIC_VARIANT
from bench.variants import OPERATIONAL_FIFO_VARIANT, OPERATIONAL_VARIANTS
from bench.variants import RAW_FIFO_VARIANT, REPORT_VARIANTS, report_variant_name

PUBLIC_SAMPLE_OUTPUT_DIR = Path("bench/reports/sample")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all Yard Copilot scenarios from a manifest.")
    parser.add_argument("--manifest", default="scenarios/manifest.json")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument(
        "--variant",
        default="all",
        choices=(
            "all",
            RAW_FIFO_VARIANT,
            OPERATIONAL_FIFO_VARIANT,
            FIFO_SAFE_VARIANT,
            HEURISTIC_VARIANT,
            FULL_VARIANT,
        ),
    )
    parser.add_argument("--no-validate", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    operational_variants, report_variants, include_raw_fifo = _selected_variants(args.variant)
    runtime = os.getenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama").strip().lower()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = _benchmark_output_dir(args.output_dir, run_id)
    output_dir.mkdir(parents=True, exist_ok=True)

    orchestrator = DecisionOrchestrator(gemma_adapter=build_gemma_adapter())

    per_scenario: list[dict[str, object]] = []
    failures: list[str] = []
    for case in manifest["cases"]:
        base_request = DecisionRequest.model_validate(case["request"])
        expected = json.loads(Path(case["files"]["expected_decision"]).read_text(encoding="utf-8"))
        expected_ticket = _expected_ticket_data(base_request)

        payload_by_variant = {}
        for variant in operational_variants:
            request = base_request.model_copy(update={"variant": variant})
            payload_by_variant[variant] = orchestrator.run_decision(request)

        if include_raw_fifo:
            per_scenario.append(
                build_raw_fifo_row(
                    request=base_request,
                    expected=expected,
                    fifo_safe_payload=payload_by_variant[OPERATIONAL_FIFO_VARIANT],
                )
            )

        for variant in operational_variants:
            payload = payload_by_variant[variant]
            observed_ticket = payload.benchmark_observed.get("parsed_ticket", {})
            accuracy = (
                0.0
                if variant == OPERATIONAL_FIFO_VARIANT
                else (
                    None
                    if expected_ticket is None
                    else compute_ticket_field_accuracy(observed_ticket, expected_ticket)
                )
            )
            row = build_payload_row(
                scenario_id=case["scenario_id"],
                variant=report_variant_name(variant),
                payload=payload,
                expected=expected,
                ticket_field_accuracy=accuracy,
                metadata=case.get("metadata", {}),
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
    for variant in report_variants:
        rows = [item for item in per_scenario if item["variant"] == variant]
        variant_metrics[variant] = compute_variant_metrics(rows)

    metrics = {
        "scenario_count": len(full_rows),
        "passed_count": sum(1 for item in full_rows if item["passed"]),
        "failed_count": sum(1 for item in full_rows if not item["passed"]),
        "run_metadata": {
            "runtime": runtime,
            "scenario_count": len(full_rows),
            "report_variants": list(report_variants),
            "generated_from_manifest": str(manifest_path),
            "latency_note": (
                "text-runtime fixture; not Ollama/Gemma performance"
                if runtime == "text"
                else "runtime-reported latency; hardware and model dependent"
            ),
        },
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
    (output_dir / "error_analysis.csv").write_text(
        render_error_analysis_csv(build_error_analysis_rows(per_scenario)),
        encoding="utf-8",
    )

    print(json.dumps({"run_id": run_id, "output_dir": str(output_dir), **metrics}, indent=2))
    if failures:
        raise SystemExit("Benchmark validation failed: " + "; ".join(failures))


def _selected_variants(variant: str) -> tuple[tuple[str, ...], tuple[str, ...], bool]:
    if variant == "all":
        return OPERATIONAL_VARIANTS, REPORT_VARIANTS, True
    if variant == RAW_FIFO_VARIANT:
        return (OPERATIONAL_FIFO_VARIANT,), (RAW_FIFO_VARIANT,), True
    if variant in {OPERATIONAL_FIFO_VARIANT, FIFO_SAFE_VARIANT}:
        return (OPERATIONAL_FIFO_VARIANT,), (FIFO_SAFE_VARIANT,), False
    if variant == HEURISTIC_VARIANT:
        return (HEURISTIC_VARIANT,), (HEURISTIC_VARIANT,), False
    if variant == FULL_VARIANT:
        return (FULL_VARIANT,), (FULL_VARIANT,), False
    raise SystemExit(f"Unknown benchmark variant: {variant}")


def _expected_ticket_data(request: DecisionRequest) -> dict[str, object] | None:
    expected_ticket = load_expected_ticket_fixture(request.ticket_ref)
    if expected_ticket is None:
        try:
            expected_ticket = parse_structured_ticket_document(
                request_id=request.request_id,
                document_ref=request.ticket_ref,
                content_type=request.ticket_content_type,
                candidate_truck_ids=[],
            )
        except PequiFluxError as exc:
            if exc.code == "STRUCTURED_TICKET_TEXT_REQUIRED":
                return None
            raise
    return expected_ticket.model_dump(mode="json")


def _benchmark_output_dir(output_dir: str | None, run_id: str) -> Path:
    report_dir = Path(output_dir or f"bench/reports/extended/{run_id}")
    _reject_public_sample_output_dir(report_dir)
    return report_dir


def _reject_public_sample_output_dir(output_dir: Path) -> None:
    resolved_output = output_dir.resolve()
    resolved_sample = PUBLIC_SAMPLE_OUTPUT_DIR.resolve()
    if resolved_output == resolved_sample or resolved_sample in resolved_output.parents:
        raise SystemExit(
            "bench/reports/sample/ is frozen public evidence. "
            "Write new reports to bench/reports/extended-sample/<run_id>, "
            "bench/reports/extended/<run_id>, or /tmp."
        )


if __name__ == "__main__":
    main()
