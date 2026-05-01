from __future__ import annotations

from pathlib import Path

from app.cli.blueprint_audit import run_audit


def test_blueprint_audit_passes() -> None:
    checks = run_audit(Path("scenarios/manifest.json"))

    assert all(check.passed for check in checks), [check for check in checks if not check.passed]
