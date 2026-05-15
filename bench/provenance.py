from __future__ import annotations

import os
import platform
import shlex
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_RANDOM_SEED = 42
DEFAULT_GITHUB_ACTIONS_ARTIFACT = "clean-gemma-eval"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def command_string(argv: list[str]) -> str:
    return shlex.join(argv)


def git_commit_sha() -> str:
    return _git_value("rev-parse", "HEAD")


def git_branch_name() -> str:
    branch = _git_value("branch", "--show-current")
    if branch != "unknown":
        return branch
    return _git_value("rev-parse", "--abbrev-ref", "HEAD")


def git_dirty() -> bool:
    result = _run(["git", "status", "--porcelain"])
    return bool(result.stdout.strip()) if result.returncode == 0 else False


def random_seed_from_env() -> int:
    raw_value = os.getenv("PEQUIFLUX_RANDOM_SEED", str(DEFAULT_RANDOM_SEED))
    try:
        return int(raw_value)
    except ValueError:
        return DEFAULT_RANDOM_SEED


def model_name(runtime: str) -> str:
    if runtime == "ollama":
        return os.getenv("GEMMA_MODEL", "gemma4:e2b")
    if runtime == "text":
        return "text-runtime"
    return os.getenv("GEMMA_MODEL", runtime)


def hardware_metadata() -> dict[str, Any]:
    metadata: dict[str, Any] = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": platform.processor() or _cpu_model(),
        "cpu_count": os.cpu_count(),
        "memory_gib": _memory_gib(),
    }
    gpu = _gpu_name()
    if gpu:
        metadata["gpu"] = gpu
    return metadata


def github_actions_metadata() -> dict[str, Any]:
    repository = os.getenv("GITHUB_REPOSITORY", "")
    server_url = os.getenv("GITHUB_SERVER_URL", "https://github.com")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    artifact_name = os.getenv(
        "PEQUIFLUX_GITHUB_ACTIONS_ARTIFACT_NAME",
        DEFAULT_GITHUB_ACTIONS_ARTIFACT,
    )
    metadata: dict[str, Any] = {
        "available": os.getenv("GITHUB_ACTIONS", "").lower() == "true",
        "artifact_name": artifact_name,
        "artifact_path": os.getenv("PEQUIFLUX_GITHUB_ACTIONS_ARTIFACT_PATH", "artifacts/latest"),
        "workflow": os.getenv("GITHUB_WORKFLOW", ""),
        "job": os.getenv("GITHUB_JOB", ""),
        "run_id": run_id,
        "run_number": os.getenv("GITHUB_RUN_NUMBER", ""),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", ""),
        "repository": repository,
        "ref_name": os.getenv("GITHUB_REF_NAME", ""),
        "sha": os.getenv("GITHUB_SHA", ""),
    }
    if repository and run_id:
        metadata["run_url"] = f"{server_url}/{repository}/actions/runs/{run_id}"
    return metadata


def benchmark_provenance(*, runtime: str, argv: list[str], output_dir: Path) -> dict[str, Any]:
    log_path = os.getenv("PEQUIFLUX_RUN_LOG_PATH", str(output_dir / "run.log"))
    clean_eval_command = os.getenv("PEQUIFLUX_EVAL_COMMAND", "")
    delegated_command = os.getenv("PEQUIFLUX_DELEGATED_COMMAND", "")
    return {
        "commit": git_commit_sha(),
        "branch": git_branch_name(),
        "git_dirty": git_dirty(),
        "timestamp_utc": utc_timestamp(),
        "runtime": runtime,
        "model": model_name(runtime),
        "seed": random_seed_from_env(),
        "command": clean_eval_command or command_string(argv),
        "delegated_command": delegated_command,
        "hardware": hardware_metadata(),
        "logs": {
            "run_log": log_path,
            "stdout_stderr": log_path,
        },
        "github_actions": github_actions_metadata(),
    }


def normalize_provenance_fields(artifact: dict[str, Any]) -> dict[str, Any]:
    run_metadata = artifact.get("run_metadata", {})
    normalized = dict(artifact)
    for key in (
        "commit",
        "branch",
        "timestamp_utc",
        "runtime",
        "model",
        "seed",
        "command",
        "delegated_command",
        "hardware",
        "logs",
        "github_actions",
        "git_dirty",
    ):
        if key in normalized and not _is_missing(normalized[key]):
            continue
        if isinstance(run_metadata, dict) and key in run_metadata:
            normalized[key] = run_metadata[key]
    if _is_missing(normalized.get("commit")):
        normalized["commit"] = git_commit_sha()
    if _is_missing(normalized.get("branch")):
        normalized["branch"] = git_branch_name()
    if _is_missing(normalized.get("timestamp_utc")):
        normalized["timestamp_utc"] = utc_timestamp()
    runtime = str(normalized.get("runtime") or run_metadata.get("runtime", "unknown"))
    normalized["runtime"] = runtime
    if _is_missing(normalized.get("model")):
        normalized["model"] = model_name(runtime)
    if _is_missing(normalized.get("seed")):
        normalized["seed"] = random_seed_from_env()
    if _is_missing(normalized.get("command")):
        normalized["command"] = ""
    if _is_missing(normalized.get("delegated_command")):
        normalized["delegated_command"] = ""
    if _is_missing(normalized.get("hardware")):
        normalized["hardware"] = hardware_metadata()
    if _is_missing(normalized.get("logs")):
        normalized["logs"] = {}
    if _is_missing(normalized.get("github_actions")):
        normalized["github_actions"] = github_actions_metadata()
    if _is_missing(normalized.get("git_dirty")):
        normalized["git_dirty"] = git_dirty()
    return normalized


def _is_missing(value: Any) -> bool:
    return value in (None, "", "unknown") or value == {}


def _git_value(*args: str) -> str:
    result = _run(["git", *args])
    if result.returncode != 0:
        return "unknown"
    return result.stdout.strip() or "unknown"


def _run(command: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(command, 127, stdout="", stderr="")


def _cpu_model() -> str:
    cpuinfo = Path("/proc/cpuinfo")
    if not cpuinfo.exists():
        return ""
    for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.lower().startswith("model name"):
            return line.split(":", 1)[1].strip()
    return ""


def _memory_gib() -> float | None:
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        return None
    for line in meminfo.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("MemTotal:"):
            kib = int(line.split()[1])
            return round(kib / 1024 / 1024, 2)
    return None


def _gpu_name() -> str:
    if not shutil.which("nvidia-smi"):
        return ""
    result = _run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"])
    if result.returncode != 0:
        return ""
    return ", ".join(line.strip() for line in result.stdout.splitlines() if line.strip())
