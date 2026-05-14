from __future__ import annotations

import json
from pathlib import Path

from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.orchestration.orchestrator import DecisionOrchestrator
from app.ui.scenario_loader import build_request_from_inputs
from app.ui.scenario_loader import load_case_defaults


def test_ui_scenario_pack_builds_request_and_runs_e4b_compatible_contract() -> None:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    case = next(
        item for item in manifest["cases"] if item["scenario_id"] == "S10_FIFO_BREAK_JUSTIFIED"
    )
    inputs = load_case_defaults(case)
    inputs["uploaded_ticket"] = None

    request, error = build_request_from_inputs(
        inputs,
        scenario_id=case["scenario_id"],
        variant="full",
    )
    assert error is None
    assert request is not None

    payload = DecisionOrchestrator(
        gemma_adapter=GemmaAdapter(runtime=TextTicketRuntime())
    ).run_decision(request)

    assert payload.scenario_id == "S10_FIFO_BREAK_JUSTIFIED"
    assert payload.decision_status == "PREVIEW_READY"
    assert payload.audit_record is not None
    assert payload.audit_record.tool_calls
    assert "truck_id" in payload.gemma_visible_summary.parsed_fields
    assert payload.gemma_visible_summary.exception_label
