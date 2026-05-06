from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domain.models import FrontEndPayload


@dataclass(frozen=True)
class AuditCheck:
    check_id: str
    passed: bool
    detail: str


REQUIRED_PATHS = (
    "app/ui/streamlit_app.py",
    "app/ui/scenario_loader.py",
    "app/ui/ui_runner.py",
    "app/ui/components/decision_card.py",
    "app/ui/components/validation_matrix.py",
    "app/ui/components/audit_panel.py",
    "app/orchestration/orchestrator.py",
    "app/domain/constraints.py",
    "app/gemma/adapter.py",
    "app/gemma/text_runtime.py",
    "app/storage/sqlite_store.py",
    "app/cli/run_scenario.py",
    "app/cli/run_benchmark.py",
    "scenarios/manifest.json",
    "docs/docker.md",
    "docs/gemma.md",
    "docs/scenario-pack.md",
    "Dockerfile",
    "compose.yaml",
)

REQUIRED_SCENARIO_IDS = {
    "S01_BASELINE",
    "S02_RAIN_OPEN",
    "S03_WET_LOAD",
    "S04_CONVEYOR_DOWN",
    "S05_CONTRACT_PRIORITY",
    "S06_DOCUMENT_BLOCK",
    "S07_VEHICLE_INCOMPAT",
    "S08_REDUCED_CAPACITY",
    "S09_HUMAN_OVERRIDE",
    "S10_FIFO_BREAK_JUSTIFIED",
    "S11_IMAGE_ROTATED_WET_LOAD",
    "S12_PDF_SCANNED_DOCUMENT_BLOCK",
    "S13_TRUCK_ID_NOT_IN_QUEUE",
    "S14_NOTE_RAIN_WEATHER_NONE_CONFLICT",
    "S15_UNKNOWN_DESTINATION_IN_TICKET",
    "S16_ALL_DESTINATIONS_BLOCKED",
    "S17_OVERRIDE_INELIGIBLE_PAIR",
    "S18_OVERRIDE_ELIGIBLE_NON_TOP_PAIR",
    "S19_TIE_BREAK_EQUAL_SCORE",
    "S20_LARGE_QUEUE_100_TRUCKS",
}

DEPRECATED_BLUEPRINT_PHRASES = (
    "Fallback controlado | Sim",
    "fallback heurístico",
    "modo degradado",
    "DEGRADED_F1",
    "REVIEW_REQUIRED_F2",
    '"fallback_mode"',
    "`fallback_mode`",
    "fallback_rate",
    "entra em F1",
    "entra em fallback",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit blueprint readiness for the Yard Copilot.")
    parser.add_argument("--manifest", default="scenarios/manifest.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    checks = run_audit(Path(args.manifest))
    result = {
        "passed": all(check.passed for check in checks),
        "passed_count": sum(1 for check in checks if check.passed),
        "failed_count": sum(1 for check in checks if not check.passed),
        "checks": [check.__dict__ for check in checks],
    }

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        for check in checks:
            status = "PASS" if check.passed else "FAIL"
            print(f"{status} {check.check_id}: {check.detail}")
        print(
            f"blueprint_audit passed={result['passed']} "
            f"passed_count={result['passed_count']} failed_count={result['failed_count']}"
        )

    if not result["passed"]:
        raise SystemExit(1)


def run_audit(manifest_path: Path) -> list[AuditCheck]:
    checks = [
        _check_required_paths(),
        _check_manifest(manifest_path),
        _check_frontend_contract(),
        _check_streamlit_demo(),
        _check_benchmark_cli(),
        _check_fail_closed_docs(),
        _check_blueprint_bridge(),
        _check_root_env_absent(),
    ]
    return checks


def _check_required_paths() -> AuditCheck:
    missing = [path for path in REQUIRED_PATHS if not Path(path).exists()]
    return AuditCheck(
        "required_paths",
        not missing,
        "all required implementation paths exist" if not missing else f"missing={missing}",
    )


def _check_manifest(manifest_path: Path) -> AuditCheck:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return AuditCheck("scenario_manifest", False, f"manifest is unreadable: {exc}")

    cases = manifest.get("cases", [])
    case_ids = [case.get("scenario_id") for case in cases]
    required_files = (
        "ticket",
        "queue",
        "operator_note",
        "weather_state",
        "resource_state",
        "expected_decision",
    )
    missing_files = []
    for case in cases:
        files: dict[str, Any] = case.get("files", {})
        for key in required_files:
            path = files.get(key)
            if not path or not Path(path).exists():
                missing_files.append(f"{case.get('scenario_id')}:{key}")

    unique_case_ids = set(case_ids)
    missing_required = sorted(REQUIRED_SCENARIO_IDS - unique_case_ids)
    extra_cases = sorted(unique_case_ids - REQUIRED_SCENARIO_IDS)
    case_dirs = {path.name for path in Path("scenarios/cases").iterdir() if path.is_dir()}
    unexpected_case_dirs = sorted(case_dirs - REQUIRED_SCENARIO_IDS)
    missing_case_dirs = sorted(REQUIRED_SCENARIO_IDS - case_dirs)
    passed = (
        len(cases) == len(REQUIRED_SCENARIO_IDS)
        and len(unique_case_ids) == len(cases)
        and not missing_files
        and not missing_required
        and not extra_cases
        and not unexpected_case_dirs
        and not missing_case_dirs
    )
    detail = (
        f"{len(cases)} frozen showcase scenarios with required files"
        if passed
        else (
            f"case_count={len(cases)} unique={len(unique_case_ids)} "
            f"missing_required={missing_required} extra_cases={extra_cases} "
            f"missing_case_dirs={missing_case_dirs} unexpected_case_dirs={unexpected_case_dirs} "
            f"missing_files={missing_files}"
        )
    )
    return AuditCheck("scenario_manifest", passed, detail)


def _check_frontend_contract() -> AuditCheck:
    required = {"latency_ms", "benchmark_tags", "confidence_notes", "gemma_visible_summary"}
    fields = set(FrontEndPayload.model_fields)
    missing = sorted(required - fields)
    return AuditCheck(
        "frontend_contract",
        not missing,
        "FrontEndPayload exposes demo diagnostics" if not missing else f"missing={missing}",
    )


def _check_streamlit_demo() -> AuditCheck:
    source = "\n".join(
        Path(path).read_text(encoding="utf-8")
        for path in (
            "app/ui/streamlit_app.py",
            "app/ui/ui_runner.py",
            "app/ui/components/audit_panel.py",
        )
    )
    required_tokens = ("DecisionOrchestrator", "selectbox", "run_decision", "operator_actions")
    missing = [token for token in required_tokens if token not in source]
    shell_markers = ("intentionally thin", "must be wired")
    stale = [token for token in shell_markers if token in source]
    passed = not missing and not stale
    return AuditCheck(
        "streamlit_demo",
        passed,
        "UI runs a real scenario payload" if passed else f"missing={missing} stale={stale}",
    )


def _check_benchmark_cli() -> AuditCheck:
    source = Path("app/cli/run_benchmark.py").read_text(encoding="utf-8") + Path(
        "bench/metrics.py"
    ).read_text(encoding="utf-8")
    required_tokens = (
        "variant_metrics",
        "decision_match_at_1",
        "constraint_violation_rate",
        "ticket_field_accuracy",
        "exception_f1",
        "fifo_break_justified_precision",
        "audit_completeness",
        "latency_p50",
        "latency_p95",
    )
    missing = [token for token in required_tokens if token not in source]
    return AuditCheck(
        "benchmark_metrics",
        not missing,
        "benchmark exports submission metrics" if not missing else f"missing={missing}",
    )


def _check_fail_closed_docs() -> AuditCheck:
    paths = (Path("technical_blueprint.md"), Path("docs/technical_blueprint.md"))
    findings = []
    for path in paths:
        if not path.exists():
            findings.append(f"{path}:missing")
            continue
        source = path.read_text(encoding="utf-8")
        for phrase in DEPRECATED_BLUEPRINT_PHRASES:
            if phrase in source:
                findings.append(f"{path}:{phrase}")
    return AuditCheck(
        "fail_closed_blueprint_docs",
        not findings,
        (
            "blueprint docs do not promise operational fallback"
            if not findings
            else f"findings={findings[:12]}"
        ),
    )


def _check_blueprint_bridge() -> AuditCheck:
    canonical = Path("technical_blueprint.md")
    bridge = Path("docs/technical_blueprint.md")
    findings = []
    if not canonical.exists():
        findings.append("technical_blueprint.md:missing")
    if not bridge.exists():
        findings.append("docs/technical_blueprint.md:missing")
    else:
        source = bridge.read_text(encoding="utf-8")
        if "../technical_blueprint.md" not in source:
            findings.append("docs/technical_blueprint.md:missing canonical link")
        if len(source.splitlines()) > 80:
            findings.append("docs/technical_blueprint.md:should remain a short bridge")
    return AuditCheck(
        "blueprint_bridge",
        not findings,
        (
            "docs blueprint is a short bridge to root canonical blueprint"
            if not findings
            else f"findings={findings}"
        ),
    )


def _check_root_env_absent() -> AuditCheck:
    forbidden = [".env", ".venv"]
    findings = [path for path in forbidden if Path(path).exists()]
    findings.extend(str(path) for path in Path(".").glob(".env.*"))
    return AuditCheck(
        "root_env_absent",
        not findings,
        "no root env or venv files" if not findings else f"found={sorted(findings)}",
    )


if __name__ == "__main__":
    main()
