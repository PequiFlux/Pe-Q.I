from __future__ import annotations

from app.ui import input_state
from app.ui.input_state import (
    clear_input_state,
    load_case_into_state,
    queue_preview_html,
    queue_source_note,
    reset_result_state,
    split_ids,
    ticket_source_note,
    ticket_source_note_with_fixture,
    ui_autorun_enabled,
)


def test_queue_preview_html_counts_waiting_and_priority_rows() -> None:
    html = queue_preview_html(
        "\n".join(
            [
                "truck_id,arrival_ts,status,contract_priority_flag",
                "TRK-001,2026-05-09T10:00:00+00:00,waiting,false",
                "TRK-002,2026-05-09T10:01:00+00:00,called,true",
                "TRK-003,2026-05-09T10:02:00+00:00,waiting,true",
            ]
        )
    )

    assert ">3<" in html
    assert ">2<" in html


def test_queue_preview_html_can_render_english_labels() -> None:
    html = queue_preview_html("truck_id,arrival_ts,status\nTRK-001,now,waiting\n", lang="en")

    assert "rows" in html
    assert "waiting" in html
    assert "linhas" not in html


def test_source_notes_describe_fixture_vs_upload() -> None:
    fixture_queue = queue_source_note(None, "truck_id,arrival_ts\n")
    fixture_ticket = ticket_source_note(None, "ticket_id: TCK-001")
    multimodal_ticket = ticket_source_note_with_fixture(
        None,
        "",
        "scenarios/cases/S03_WET_LOAD/ticket.png",
    )

    assert "Exemplo versionado" in fixture_queue
    assert "Exemplo versionado" in fixture_ticket
    assert "fixture PNG" in multimodal_ticket


def test_source_notes_can_render_english() -> None:
    fixture_queue = queue_source_note(None, "truck_id,arrival_ts\n", lang="en")
    fixture_ticket = ticket_source_note(None, "ticket_id: TCK-001", lang="en")
    multimodal_ticket = ticket_source_note_with_fixture(
        None,
        "",
        "scenarios/cases/S03_WET_LOAD/ticket.png",
        lang="en",
    )

    assert "Versioned example" in fixture_queue
    assert "fixture TXT ticket" in fixture_ticket
    assert "PNG fixture" in multimodal_ticket


def test_split_ids_trims_empty_values() -> None:
    assert split_ids(" DST-COV-01, ,DST-COV-02 ") == ["DST-COV-01", "DST-COV-02"]


def test_ui_autorun_enabled_reads_truthy_env(monkeypatch) -> None:
    monkeypatch.setenv("PEQUIFLUX_UI_AUTORUN", "true")

    assert ui_autorun_enabled() is True


def test_reset_result_state_clears_operator_artifacts(monkeypatch) -> None:
    session_state = {
        "last_payload": {"status": "old"},
        "last_request": {"request_id": "REQ-OLD"},
        "operator_finalization": {"final_status": "APPROVED"},
        "operator_audit_update": {"reason": "old"},
    }
    monkeypatch.setattr(input_state.st, "session_state", session_state)

    reset_result_state()

    assert session_state == {}


def test_clear_input_state_preserves_selected_case(monkeypatch) -> None:
    input_keys = {
        "queue_csv": "yard_queue_csv",
        "ticket_text": "yard_ticket_text",
        "fixture_ticket_path": "yard_fixture_ticket_path",
        "fixture_ticket_content_type": "yard_fixture_ticket_content_type",
        "operator_note": "yard_operator_note",
        "weather_json": "yard_weather_json",
        "resource_json": "yard_resource_json",
        "queue_upload": "yard_queue_upload",
        "ticket_upload": "yard_ticket_upload",
        "upload_generation": "yard_upload_generation",
        "weather_mode": "yard_weather_mode",
        "resource_mode": "yard_resource_mode",
        "weather_precipitation": "yard_weather_precipitation",
        "weather_severity": "yard_weather_severity",
        "resource_available": "yard_resource_available",
        "resource_blocked": "yard_resource_blocked",
        "resource_wet": "yard_resource_wet",
        "selected_case": "yard_selected_case",
    }
    session_state = {
        "yard_queue_csv": "truck_id,arrival_ts\n",
        "yard_selected_case": "S03_WET_LOAD",
        "active_case": "S03_WET_LOAD",
        "last_payload": {"status": "old"},
    }
    monkeypatch.setattr(input_state.st, "session_state", session_state)

    clear_input_state(input_keys)

    assert session_state["yard_selected_case"] == "S03_WET_LOAD"
    assert session_state["yard_queue_csv"] == ""
    assert "active_case" not in session_state
    assert "last_payload" not in session_state


def test_load_case_into_state_populates_visual_weather_and_resource_controls(
    monkeypatch,
) -> None:
    input_keys = {
        "queue_csv": "yard_queue_csv",
        "ticket_text": "yard_ticket_text",
        "fixture_ticket_path": "yard_fixture_ticket_path",
        "fixture_ticket_content_type": "yard_fixture_ticket_content_type",
        "operator_note": "yard_operator_note",
        "weather_json": "yard_weather_json",
        "resource_json": "yard_resource_json",
        "queue_upload": "yard_queue_upload",
        "ticket_upload": "yard_ticket_upload",
        "upload_generation": "yard_upload_generation",
        "weather_mode": "yard_weather_mode",
        "resource_mode": "yard_resource_mode",
        "weather_precipitation": "yard_weather_precipitation",
        "weather_severity": "yard_weather_severity",
        "resource_available": "yard_resource_available",
        "resource_blocked": "yard_resource_blocked",
        "resource_wet": "yard_resource_wet",
    }
    session_state = {"yard_upload_generation": 0}
    monkeypatch.setattr(input_state.st, "session_state", session_state)
    monkeypatch.setattr(
        input_state,
        "load_case_defaults",
        lambda case: {
            "queue_csv": "truck_id,arrival_ts\nTRK-001,2026-05-09T10:00:00+00:00\n",
            "ticket_text": "ticket_id: TCK-001",
            "fixture_ticket_path": "scenarios/cases/S10_FIFO_BREAK_JUSTIFIED/ticket.txt",
            "fixture_ticket_content_type": "text/plain",
            "operator_note": "Carga umida confirmada.",
            "weather_json": '{"precipitation": "rain", "severity": "medium"}',
            "resource_json": (
                "["
                '{"resource_id":"DST-COV-01","status":"available",'
                '"supported_load_conditions":["dry","wet"]},'
                '{"resource_id":"DST-OPEN-01","status":"blocked",'
                '"supported_load_conditions":["dry"]}'
                "]"
            ),
        },
    )

    load_case_into_state(input_keys, {"scenario_id": "S10_FIFO_BREAK_JUSTIFIED"})

    assert session_state["yard_weather_mode"] == "formulário"
    assert session_state["yard_resource_mode"] == "formulário"
    assert session_state["yard_weather_precipitation"] == "rain"
    assert session_state["yard_weather_severity"] == "medium"
    assert session_state["yard_resource_available"] == "DST-COV-01"
    assert session_state["yard_resource_blocked"] == "DST-OPEN-01"
    assert session_state["yard_resource_wet"] == "DST-COV-01"
