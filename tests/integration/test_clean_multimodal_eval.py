from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from bench.clean_eval import expected_ticket_leakage_violations
from bench.clean_eval import main


def test_clean_multimodal_eval_split_delegates_after_leakage_preflight(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario_dir = Path("scenarios/extended/public_test_frozen")
    manifest_path = scenario_dir / "manifest.json"
    calls: list[dict] = []

    def fake_run(command, *, env, check, **kwargs):
        calls.append({"command": command, "env": env, "check": check})
        return subprocess.CompletedProcess(command, 0, stdout="ok\n", stderr="")

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setattr(
        "sys.argv",
        [
            "clean_eval",
            "--variant",
            "full",
            "--runtime",
            "gemma4:e4b",
            "--scenario-dir",
            str(scenario_dir),
            "--output",
            str(tmp_path / "clean_public_test"),
            "--fail-on-leakage",
        ],
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert exc.value.code == 0
    assert (
        expected_ticket_leakage_violations(
            manifest_path=manifest_path,
            scenario_dir=scenario_dir,
            variant="full",
        )
        == []
    )
    assert calls[0]["command"][-6:] == [
        "--variant",
        "full",
        "--manifest",
        str(manifest_path),
        "--output-dir",
        str(tmp_path / "clean_public_test"),
    ]
    assert calls[0]["env"]["PEQUIFLUX_GEMMA_RUNTIME"] == "ollama"
    assert calls[0]["env"]["GEMMA_MODEL"] == "gemma4:e4b"
    assert calls[0]["env"]["PEQUIFLUX_RUN_LOG_PATH"] == str(
        tmp_path / "clean_public_test" / "run.log"
    )
    assert "bench.clean_eval" in calls[0]["env"]["PEQUIFLUX_EVAL_COMMAND"]
    assert "app.cli.run_benchmark" in calls[0]["env"]["PEQUIFLUX_DELEGATED_COMMAND"]
    assert (tmp_path / "clean_public_test" / "run.log").exists()
