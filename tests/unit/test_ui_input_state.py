from __future__ import annotations

from app.ui import input_state
from app.ui.input_state import (
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


def test_source_notes_describe_fixture_vs_upload() -> None:
    fixture_queue = queue_source_note(None, "truck_id,arrival_ts\n")
    fixture_ticket = ticket_source_note(None, "ticket_id: TCK-001")
    multimodal_ticket = ticket_source_note_with_fixture(
        None,
        "",
        "scenarios/cases/S03_WET_LOAD/ticket.png",
    )

    assert "Caso versionado" in fixture_queue
    assert "Caso versionado" in fixture_ticket
    assert "fixture PNG" in multimodal_ticket


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
