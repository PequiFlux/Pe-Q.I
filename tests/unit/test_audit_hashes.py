from __future__ import annotations

import json
import re
from pathlib import Path

from app.domain.models import DecisionRequest
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.orchestration.orchestrator import DecisionOrchestrator


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def test_audit_source_hashes_are_sha256_not_raw_paths_or_notes() -> None:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["scenario_id"] == "S01_BASELINE")
    request = DecisionRequest.model_validate(case["request"])
    orchestrator = DecisionOrchestrator(gemma_adapter=GemmaAdapter(runtime=TextTicketRuntime()))

    payload = orchestrator.run_decision(request)

    assert payload.audit_record is not None
    hashes = payload.audit_record.source_hashes
    assert set(hashes) == {
        "queue_csv_ref",
        "ticket_ref",
        "operator_note",
        "weather_state",
        "resource_state",
    }
    assert all(SHA256_RE.match(value) for value in hashes.values())
    assert hashes["queue_csv_ref"] != request.queue_csv_ref
    assert hashes["ticket_ref"] != request.ticket_ref
    assert request.operator_note not in hashes.values()
