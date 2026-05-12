from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import DecisionRequest
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.orchestration.orchestrator import DecisionOrchestrator


def test_unknown_ticket_destination_routes_to_review_without_dispatch() -> None:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    case = next(
        item
        for item in manifest["cases"]
        if item["scenario_id"] == "S15_UNKNOWN_DESTINATION_IN_TICKET"
    )
    request = DecisionRequest.model_validate(case["request"]).model_copy(update={"variant": "full"})

    payload = DecisionOrchestrator(
        gemma_adapter=GemmaAdapter(runtime=TextTicketRuntime())
    ).run_decision(request)

    assert payload.decision_status == "REVIEW_REQUIRED"
    assert payload.recommended_truck is None
    assert payload.recommended_destination is None
    assert payload.benchmark_observed["needs_human_review"] is True
    assert payload.audit_record is not None
    assert any(
        "resource_state prevails because parsed destination constraint is unknown" in item
        for item in payload.audit_record.truth_resolution.material_conflicts
    )
