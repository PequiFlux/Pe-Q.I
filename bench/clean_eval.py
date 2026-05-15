from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from bench.provenance import command_string


EVALUATION_SPLIT_NAMES = {"public_dev", "public_test_frozen", "private_holdout"}
MULTIMODAL_CONTENT_TYPES = {"application/pdf", "image/png", "image/jpeg", "image/jpg"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Run clean benchmark evaluation guards.")
    parser.add_argument("--variant", default="full")
    parser.add_argument("--runtime", default="text")
    parser.add_argument("--scenario-dir", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--manifest", default=None)
    parser.add_argument("--fail-on-leakage", action="store_true")
    args = parser.parse_args()

    scenario_dir = Path(args.scenario_dir)
    manifest_path = Path(args.manifest) if args.manifest else scenario_dir / "manifest.json"
    if args.fail_on_leakage:
        violations = expected_ticket_leakage_violations(
            manifest_path=manifest_path,
            scenario_dir=scenario_dir,
            variant=args.variant,
        )
        if violations:
            joined = "; ".join(violations)
            raise SystemExit(f"expected_ticket leakage detected: {joined}")

    env = _runtime_env(args.runtime)
    output_dir = Path(args.output)
    log_path = output_dir / "run.log"
    command = [
        sys.executable,
        "-m",
        "app.cli.run_benchmark",
        "--variant",
        args.variant,
        "--manifest",
        str(manifest_path),
        "--output-dir",
        args.output,
    ]
    env["PEQUIFLUX_EVAL_COMMAND"] = command_string(
        [sys.executable, "-m", "bench.clean_eval", *sys.argv[1:]]
    )
    env["PEQUIFLUX_DELEGATED_COMMAND"] = command_string(command)
    env["PEQUIFLUX_RUN_LOG_PATH"] = str(log_path)

    completed = subprocess.run(
        command,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "\n".join(
            [
                f"command={env['PEQUIFLUX_EVAL_COMMAND']}",
                f"delegated_command={env['PEQUIFLUX_DELEGATED_COMMAND']}",
                f"returncode={completed.returncode}",
                "",
                "stdout:",
                completed.stdout or "",
                "",
                "stderr:",
                completed.stderr or "",
            ]
        ),
        encoding="utf-8",
    )
    if completed.stdout:
        print(completed.stdout, end="")
    if completed.stderr:
        print(completed.stderr, end="", file=sys.stderr)
    raise SystemExit(completed.returncode)


def expected_ticket_leakage_violations(
    *,
    manifest_path: Path,
    scenario_dir: Path,
    variant: str,
) -> list[str]:
    if variant != "full" or not _is_evaluation_split(scenario_dir):
        return []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    violations: list[str] = []
    for case in manifest.get("cases", []):
        request = case.get("request", {})
        content_type = str(request.get("ticket_content_type", ""))
        if content_type not in MULTIMODAL_CONTENT_TYPES:
            continue
        ticket_ref = request.get("ticket_ref")
        if not ticket_ref:
            continue
        sidecar_path = _resolve_ref(Path(ticket_ref), manifest_path.parent).with_name(
            "expected_ticket.json"
        )
        if sidecar_path.exists():
            scenario_id = str(case.get("scenario_id") or request.get("scenario_id") or "unknown")
            violations.append(f"{scenario_id}:{sidecar_path}")
    return violations


def _resolve_ref(path: Path, base_dir: Path) -> Path:
    if path.is_absolute():
        return path
    repo_relative = Path.cwd() / path
    if repo_relative.exists():
        return repo_relative
    return base_dir / path


def _is_evaluation_split(scenario_dir: Path) -> bool:
    return any(part in EVALUATION_SPLIT_NAMES for part in scenario_dir.parts)


def _runtime_env(runtime: str) -> dict[str, str]:
    env = os.environ.copy()
    normalized = runtime.strip().lower()
    if normalized.startswith("gemma4"):
        env["PEQUIFLUX_GEMMA_RUNTIME"] = "ollama"
        env["GEMMA_MODEL"] = runtime
    else:
        env["PEQUIFLUX_GEMMA_RUNTIME"] = normalized
    return env


if __name__ == "__main__":
    main()
