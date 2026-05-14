from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.clean_eval import main
from bench.clean_eval import expected_ticket_leakage_violations


def test_full_multimodal_eval_split_rejects_expected_ticket_sidecar(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "scenarios" / "extended" / "public_test_frozen"
    case_dir = scenario_dir / "S_LEAK"
    case_dir.mkdir(parents=True)
    ticket_path = case_dir / "ticket.png"
    ticket_path.write_bytes(b"not-a-real-image")
    (case_dir / "expected_ticket.json").write_text("{}", encoding="utf-8")
    manifest_path = scenario_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "scenario_id": "S_LEAK",
                        "request": {
                            "scenario_id": "S_LEAK",
                            "ticket_ref": str(ticket_path),
                            "ticket_content_type": "image/png",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    violations = expected_ticket_leakage_violations(
        manifest_path=manifest_path,
        scenario_dir=scenario_dir,
        variant="full",
    )

    assert violations == [f"S_LEAK:{case_dir / 'expected_ticket.json'}"]


def test_clean_eval_cli_fails_before_running_leaky_split(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario_dir = tmp_path / "scenarios" / "extended" / "public_test_frozen"
    case_dir = scenario_dir / "S_LEAK"
    case_dir.mkdir(parents=True)
    ticket_path = case_dir / "ticket.png"
    ticket_path.write_bytes(b"not-a-real-image")
    (case_dir / "expected_ticket.json").write_text("{}", encoding="utf-8")
    manifest_path = scenario_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "scenario_id": "S_LEAK",
                        "request": {
                            "scenario_id": "S_LEAK",
                            "ticket_ref": str(ticket_path),
                            "ticket_content_type": "image/png",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "clean_eval",
            "--variant",
            "full",
            "--runtime",
            "text",
            "--scenario-dir",
            str(scenario_dir),
            "--output",
            str(tmp_path / "out"),
            "--fail-on-leakage",
        ],
    )

    with pytest.raises(SystemExit, match="expected_ticket leakage detected"):
        main()


def test_text_fixture_sidecar_is_allowed_outside_clean_eval_split(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "scenarios" / "cases"
    case_dir = scenario_dir / "S_B0"
    case_dir.mkdir(parents=True)
    ticket_path = case_dir / "ticket.png"
    ticket_path.write_bytes(b"not-a-real-image")
    (case_dir / "expected_ticket.json").write_text("{}", encoding="utf-8")
    manifest_path = scenario_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "cases": [
                    {
                        "scenario_id": "S_B0",
                        "request": {
                            "scenario_id": "S_B0",
                            "ticket_ref": str(ticket_path),
                            "ticket_content_type": "image/png",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    assert (
        expected_ticket_leakage_violations(
            manifest_path=manifest_path,
            scenario_dir=scenario_dir,
            variant="full",
        )
        == []
    )
