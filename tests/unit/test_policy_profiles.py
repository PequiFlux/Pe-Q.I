from __future__ import annotations

import json
from pathlib import Path

from app.domain.enums import PolicyRule
from app.domain.models import DecisionRequest, PolicyProfile
from app.gemma.adapter import GemmaAdapter
from app.gemma.text_runtime import TextTicketRuntime
from app.orchestration.orchestrator import DecisionOrchestrator


def _request() -> DecisionRequest:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["scenario_id"] == "S01_BASELINE")
    return DecisionRequest.model_validate(case["request"])


def _profile(version: str, *, min_operational_capacity_pct: int = 20) -> PolicyProfile:
    return PolicyProfile(
        version=version,
        min_operational_capacity_pct=min_operational_capacity_pct,
        comfort_capacity_pct=50,
        weights={
            "fifo_position": 40,
            "contract_priority": 30,
            "resource_fit": 15,
            "capacity_headroom": 10,
            "wait_sla_pressure": 5,
        },
        tie_breakers=[
            "higher_score",
            "lower_queue_position",
            "earlier_arrival_ts",
            "lexicographic_truck_id",
            "lexicographic_destination_id",
        ],
    )


def test_orchestrator_uses_requested_policy_profile_version() -> None:
    request = _request().model_copy(update={"policy_profile_version": "v-strict"})
    orchestrator = DecisionOrchestrator(
        gemma_adapter=GemmaAdapter(runtime=TextTicketRuntime()),
        policy_profiles={"v-strict": _profile("v-strict", min_operational_capacity_pct=95)},
    )

    payload = orchestrator.run_decision(request)

    assert payload.decision_status == "BLOCKED"
    assert "No eligible candidate" in payload.reason_summary
    assert payload.audit_record is not None
    assert PolicyRule.NO_VALID_PAIR_BLOCKS_AUTODISPATCH in payload.audit_record.fired_rules


def test_orchestrator_fails_closed_for_unknown_policy_profile_version() -> None:
    request = _request().model_copy(update={"policy_profile_version": "missing-policy"})
    orchestrator = DecisionOrchestrator(
        gemma_adapter=GemmaAdapter(runtime=TextTicketRuntime()),
        policy_profiles={"v-test": _profile("v-test")},
    )

    payload = orchestrator.run_decision(request)

    assert payload.decision_status == "BLOCKED"
    assert "Unknown policy profile version: missing-policy" in payload.reason_summary
