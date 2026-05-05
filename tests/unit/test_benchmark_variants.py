from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.domain.errors import PequiFluxError
from app.domain.models import DecisionRequest
from app.gemma.adapter import GemmaAdapter
from app.orchestration.orchestrator import DecisionOrchestrator


class RuntimeThatMustNotRun:
    def generate_structured(self, **kwargs):
        raise AssertionError("Gemma runtime should not be called for this benchmark variant.")

    def summarize(self, **kwargs) -> str:
        raise AssertionError("Gemma runtime should not be called for this benchmark variant.")


class RuntimeThatFails:
    def generate_structured(self, **kwargs):
        raise PequiFluxError("TEST_GEMMA_CALLED", "Gemma runtime was called.")

    def summarize(self, **kwargs) -> str:
        raise PequiFluxError("TEST_GEMMA_CALLED", "Gemma runtime was called.")


def _request(variant: str, scenario_id: str = "S03_WET_LOAD") -> DecisionRequest:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["scenario_id"] == scenario_id)
    return DecisionRequest.model_validate(case["request"]).model_copy(update={"variant": variant})


def test_fifo_variant_does_not_call_gemma_or_parse_ticket() -> None:
    orchestrator = DecisionOrchestrator(gemma_adapter=GemmaAdapter(runtime=RuntimeThatMustNotRun()))

    payload = orchestrator.run_decision(_request("fifo"))

    assert "parse_ticket_document" not in payload.latency_ms
    assert payload.benchmark_observed["parsed_ticket"]["ticket_id"] is None


def test_heuristic_variant_uses_structured_parser_without_gemma() -> None:
    orchestrator = DecisionOrchestrator(gemma_adapter=GemmaAdapter(runtime=RuntimeThatMustNotRun()))

    payload = orchestrator.run_decision(_request("heuristic", scenario_id="S10_FIFO_BREAK_JUSTIFIED"))

    assert "parse_structured_ticket_document" in payload.latency_ms
    assert "parse_ticket_document" not in payload.latency_ms
    assert payload.benchmark_observed["parsed_ticket"]["ticket_id"] == "TCK-S10-005"


def test_heuristic_variant_fails_closed_on_multimodal_ticket_without_text() -> None:
    orchestrator = DecisionOrchestrator(gemma_adapter=GemmaAdapter(runtime=RuntimeThatMustNotRun()))

    payload = orchestrator.run_decision(_request("heuristic", scenario_id="S03_WET_LOAD"))

    assert payload.decision_status == "BLOCKED"
    assert payload.benchmark_observed["parsed_ticket"]["ticket_id"] is None


def test_full_variant_uses_configured_gemma_runtime() -> None:
    orchestrator = DecisionOrchestrator(gemma_adapter=GemmaAdapter(runtime=RuntimeThatFails()))

    payload = orchestrator.run_decision(_request("full", scenario_id="S10_FIFO_BREAK_JUSTIFIED"))

    assert payload.decision_status == "BLOCKED"
    assert "Gemma runtime was called." in payload.reason_summary
