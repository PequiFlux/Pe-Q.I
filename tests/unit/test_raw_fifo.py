from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import DecisionRequest
from app.services.raw_fifo import raw_fifo_call


def _request(scenario_id: str) -> DecisionRequest:
    manifest = json.loads(Path("scenarios/manifest.json").read_text(encoding="utf-8"))
    case = next(item for item in manifest["cases"] if item["scenario_id"] == scenario_id)
    return DecisionRequest.model_validate(case["request"])


def test_raw_fifo_uses_first_waiting_row_and_declared_destination() -> None:
    truck_id, destination_id = raw_fifo_call(_request("S10_FIFO_BREAK_JUSTIFIED"))

    assert truck_id == "TRK-001"
    assert destination_id == "DST-OPEN-01"
