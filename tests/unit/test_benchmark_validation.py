from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.models import DecisionRequest
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.orchestration.orchestrator import DecisionOrchestrator
from bench.validation import validate_payload


def _case(scenario_id: str) -> dict:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    return next(item for item in manifest["cases"] if item["scenario_id"] == scenario_id)


def _request(scenario_id: str, variant: str) -> DecisionRequest:
    return DecisionRequest.model_validate(_case(scenario_id)["request"]).model_copy(
        update={"variant": variant}
    )


def _expected(scenario_id: str) -> dict:
    return json.loads(Path(_case(scenario_id)["files"]["expected_decision"]).read_text())


def _orchestrator() -> DecisionOrchestrator:
    return DecisionOrchestrator(gemma_adapter=GemmaAdapter(runtime=TextTicketRuntime()))


def test_benchmark_validation_requires_full_preview_ready_tool_path() -> None:
    payload = _orchestrator().run_decision(_request("S10_FIFO_BREAK_JUSTIFIED", "full"))
    assert payload.audit_record is not None
    payload_without_ranking_tool = payload.model_copy(
        update={
            "audit_record": payload.audit_record.model_copy(
                update={
                    "tool_calls": [
                        record
                        for record in payload.audit_record.tool_calls
                        if record.tool_name != "rank_candidates"
                    ]
                }
            )
        }
    )

    with pytest.raises(SystemExit, match="missing full tool calls=\\['rank_candidates'\\]"):
        validate_payload(payload_without_ranking_tool, _expected("S10_FIFO_BREAK_JUSTIFIED"))


def test_benchmark_validation_requires_review_required_audit_tool() -> None:
    payload = _orchestrator().run_decision(_request("S03_WET_LOAD", "full"))
    assert payload.audit_record is not None
    payload_without_audit_tool = payload.model_copy(
        update={"audit_record": payload.audit_record.model_copy(update={"tool_calls": []})}
    )

    with pytest.raises(
        SystemExit,
        match="missing full tool calls=\\['generate_audit_payload'\\]",
    ):
        validate_payload(payload_without_audit_tool, _expected("S03_WET_LOAD"))


def test_benchmark_validation_does_not_require_tool_calls_for_technical_variants() -> None:
    payload = _orchestrator().run_decision(_request("S10_FIFO_BREAK_JUSTIFIED", "heuristic"))
    assert payload.audit_record is not None
    assert payload.audit_record.tool_calls == []

    validate_payload(payload, _expected("S10_FIFO_BREAK_JUSTIFIED"))
