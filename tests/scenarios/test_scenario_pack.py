from __future__ import annotations

import json
from pathlib import Path

from app.adapters.csv_adapter import load_queue_rows, normalize_queue_snapshot
from app.adapters.document_adapter import build_document_bundle
from app.adapters.state_adapter import load_resource_state, load_weather_state
from app.domain.models import DecisionRequest
from app.services.structured_ticket_parser import load_expected_ticket_fixture


REQUIRED_CASES = {
    "S01_BASELINE",
    "S02_RAIN_OPEN",
    "S03_WET_LOAD",
    "S04_CONVEYOR_DOWN",
    "S05_CONTRACT_PRIORITY",
    "S06_DOCUMENT_BLOCK",
    "S07_VEHICLE_INCOMPAT",
    "S08_REDUCED_CAPACITY",
    "S09_HUMAN_OVERRIDE",
    "S10_FIFO_BREAK_JUSTIFIED",
    "S11_IMAGE_ROTATED_WET_LOAD",
    "S12_PDF_SCANNED_DOCUMENT_BLOCK",
    "S13_TRUCK_ID_NOT_IN_QUEUE",
    "S14_NOTE_RAIN_WEATHER_NONE_CONFLICT",
    "S15_UNKNOWN_DESTINATION_IN_TICKET",
    "S16_ALL_DESTINATIONS_BLOCKED",
    "S17_OVERRIDE_INELIGIBLE_PAIR",
    "S18_OVERRIDE_ELIGIBLE_NON_TOP_PAIR",
    "S19_TIE_BREAK_EQUAL_SCORE",
    "S20_LARGE_QUEUE_100_TRUCKS",
}


def test_scenario_pack_v0_is_complete_and_loadable() -> None:
    manifest_path = Path("scenarios/manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    cases = manifest["cases"]
    case_dirs = {path.name for path in Path("scenarios/cases").iterdir() if path.is_dir()}
    assert case_dirs == REQUIRED_CASES
    assert {case["scenario_id"] for case in cases} == REQUIRED_CASES

    for case in cases:
        files = case["files"]
        for file_ref in files.values():
            assert Path(file_ref).exists(), file_ref

        request = DecisionRequest.model_validate(case["request"])
        assert request.scenario_id == case["scenario_id"]

        queue_rows = load_queue_rows(request.queue_csv_ref)
        snapshot = normalize_queue_snapshot(
            request_id=request.request_id,
            rows=queue_rows,
            reference_time=request.received_at,
        )
        assert snapshot.waiting_rows

        bundle = build_document_bundle(
            request_id=request.request_id,
            document_ref=request.ticket_ref,
            content_type=request.ticket_content_type,
            candidate_truck_ids=[row.truck_id for row in snapshot.waiting_rows],
        )
        assert bundle.sha256
        if request.ticket_content_type == "text/plain":
            assert bundle.extracted_text
        else:
            assert bundle.rendered_pages
            assert load_expected_ticket_fixture(request.ticket_ref) is not None

        weather = load_weather_state(files["weather_state"])
        resources = load_resource_state(files["resource_state"])
        expected = json.loads(Path(files["expected_decision"]).read_text(encoding="utf-8"))

        assert request.weather_state == weather
        assert request.resource_state == resources
        assert expected["expected_status"] in {"PREVIEW_READY", "REVIEW_REQUIRED", "BLOCKED"}
        assert isinstance(expected["acceptable_trucks"], list)
        assert isinstance(expected["acceptable_destinations"], list)
        assert isinstance(expected["required_constraints"], list)
        assert isinstance(expected["fifo_break_expected"], bool)
