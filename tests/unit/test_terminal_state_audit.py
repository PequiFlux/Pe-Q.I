from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.domain.enums import DecisionStatus
from app.domain.models import DecisionRequest
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.orchestration.orchestrator import DecisionOrchestrator
from app.storage.jsonl_logger import JsonlLogger
from app.storage.sqlite_store import SQLiteStore


def _make_orchestrator_with_storage(tmp_path: Path) -> DecisionOrchestrator:
    db_path = str(tmp_path / "pequiflux.db")
    log_path = str(tmp_path / "events.jsonl")
    return DecisionOrchestrator(
        gemma_adapter=GemmaAdapter(runtime=TextTicketRuntime()),
        sqlite_store=SQLiteStore(path=db_path),
        jsonl_logger=JsonlLogger(path=log_path),
    )


def _load_request(scenario_id: str) -> DecisionRequest:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["scenario_id"] == scenario_id)
    return DecisionRequest.model_validate(case["request"])


def test_review_required_has_audit_record_and_persistence(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator_with_storage(tmp_path)
    request = _load_request("S03_WET_LOAD")
    payload = orchestrator.run_decision(request)

    assert payload.decision_status == DecisionStatus.REVIEW_REQUIRED
    assert payload.audit_record is not None
    assert payload.audit_record.decision_id
    assert payload.audit_record.source_hashes
    assert payload.audit_record.latencies_ms

    db_path = tmp_path / "pequiflux.db"
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT decision_id, decision_status FROM decision_records WHERE request_id = ?",
            (request.request_id,),
        ).fetchone()
        assert row is not None
        assert row[1] == "REVIEW_REQUIRED"

        audit_row = connection.execute(
            "SELECT audit_json FROM audit_records WHERE decision_id = ?",
            (row[0],),
        ).fetchone()
        assert audit_row is not None
        audit_data = json.loads(audit_row[0])
        assert audit_data["decision_id"] == row[0]

    log_path = tmp_path / "events.jsonl"
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["state"] == "REVIEW_REQUIRED"
    assert entry["request_id"] == request.request_id


def test_blocked_path_has_audit_record_and_persistence(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator_with_storage(tmp_path)
    request = _load_request("S01_BASELINE")
    request = request.model_copy(update={"policy_profile_version": "nonexistent_v999"})

    payload = orchestrator.run_decision(request)

    assert payload.decision_status == DecisionStatus.BLOCKED
    assert payload.audit_record is not None
    assert payload.audit_record.decision_id
    assert payload.audit_record.source_hashes

    db_path = tmp_path / "pequiflux.db"
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT decision_id, decision_status FROM decision_records WHERE request_id = ?",
            (request.request_id,),
        ).fetchone()
        assert row is not None
        assert row[1] == "BLOCKED"

        audit_row = connection.execute(
            "SELECT audit_json FROM audit_records WHERE decision_id = ?",
            (row[0],),
        ).fetchone()
        assert audit_row is not None
        audit_data = json.loads(audit_row[0])
        assert audit_data["decision_id"] == row[0]

    log_path = tmp_path / "events.jsonl"
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["state"] == "BLOCKED"
    assert entry["request_id"] == request.request_id


def test_preview_ready_still_has_audit_record_and_persistence(tmp_path: Path) -> None:
    orchestrator = _make_orchestrator_with_storage(tmp_path)
    request = _load_request("S01_BASELINE")
    payload = orchestrator.run_decision(request)

    assert payload.decision_status == DecisionStatus.PREVIEW_READY
    assert payload.audit_record is not None

    db_path = tmp_path / "pequiflux.db"
    with sqlite3.connect(db_path) as connection:
        row = connection.execute(
            "SELECT decision_id, decision_status FROM decision_records WHERE request_id = ?",
            (request.request_id,),
        ).fetchone()
        assert row is not None
        assert row[1] == "PREVIEW_READY"

    log_path = tmp_path / "events.jsonl"
    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) >= 1
    entry = json.loads(lines[-1])
    assert entry["state"] == "PREVIEW_READY"
