from __future__ import annotations

import json
from pathlib import Path

from app.ui.components.scenario_catalog import scenario_label
from app.ui import scenario_loader


class UploadedFileStub:
    def __init__(self, name: str, content: bytes) -> None:
        self.name = name
        self._content = content

    def getvalue(self) -> bytes:
        return self._content


def _inputs(**overrides) -> dict[str, object]:
    data: dict[str, object] = {
        "queue_csv": "truck_id,arrival_ts\nTRK-001,2026-05-09T10:00:00+00:00\n",
        "uploaded_ticket": None,
        "ticket_text": "ticket_id: TCK-001\ntruck_id: TRK-001\n",
        "operator_note": "Operacao nominal.",
        "weather_json": '{"precipitation":"none","severity":"none"}',
        "resource_json": (
            '[{"resource_id":"DST-COV-01","status":"available","capacity_pct":85,'
            '"resource_type":"covered_hopper","exposure":"covered",'
            '"allowed_vehicle_types":["truck"],'
            '"supported_load_conditions":["dry"]}]'
        ),
    }
    data.update(overrides)
    return data


def test_validate_ui_inputs_requires_queue_csv() -> None:
    error = scenario_loader.validate_ui_inputs(_inputs(queue_csv=""))

    assert error == "Fila CSV obrigatória."


def test_validate_ui_inputs_rejects_non_text_upload_in_text_runtime(monkeypatch) -> None:
    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", "text")

    error = scenario_loader.validate_ui_inputs(
        _inputs(uploaded_ticket=UploadedFileStub("ticket.png", b"fake-image"), ticket_text="")
    )

    assert error is not None
    assert "Modo teste aceita upload apenas TXT" in error


def test_validate_ui_inputs_rejects_multimodal_fixture_without_sidecar(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", "text")
    fixture_ticket = tmp_path / "ticket.png"
    fixture_ticket.write_bytes(b"fake-image")

    error = scenario_loader.validate_ui_inputs(
        _inputs(ticket_text="", fixture_ticket_path=str(fixture_ticket))
    )

    assert error is not None
    assert "expected_ticket.json" in error


def test_build_request_from_inputs_accepts_txt_upload_in_text_runtime(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", "text")
    monkeypatch.setattr(scenario_loader, "UI_WORK_DIR", tmp_path / "ui")

    request, error = scenario_loader.build_request_from_inputs(
        _inputs(uploaded_ticket=UploadedFileStub("ticket.txt", b"ticket_id: TCK-001\n")),
        "S01_BASELINE",
        "full",
    )

    assert error is None
    assert request is not None
    assert request.ticket_content_type == "text/plain"
    assert Path(request.ticket_ref).exists()


def test_build_request_from_inputs_accepts_multimodal_fixture_in_text_runtime(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", "text")
    monkeypatch.setattr(scenario_loader, "UI_WORK_DIR", tmp_path / "ui")
    fixture_dir = tmp_path / "fixture"
    fixture_dir.mkdir()
    fixture_ticket = fixture_dir / "ticket.png"
    fixture_ticket.write_bytes(b"fake-image")
    (fixture_dir / "expected_ticket.json").write_text(
        json.dumps(
            {
                "ticket_id": "TCK-001",
                "truck_id": "TRK-001",
                "vehicle_type": "truck",
                "document_status": "ok",
                "document_block_flags": [],
                "load_condition": "wet",
                "contract_priority_flag": False,
                "destination_constraints": [],
                "parse_confidence": 0.91,
                "ambiguities": [],
                "evidence_refs": [],
            }
        ),
        encoding="utf-8",
    )

    request, error = scenario_loader.build_request_from_inputs(
        _inputs(ticket_text="", fixture_ticket_path=str(fixture_ticket)),
        "S03_WET_LOAD",
        "full",
    )

    assert error is None
    assert request is not None
    assert request.ticket_content_type == "image/png"
    assert Path(request.ticket_ref).exists()
    assert Path(request.ticket_ref).with_name("expected_ticket.json").exists()


def test_build_request_from_inputs_generates_unique_request_ids(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(scenario_loader, "UI_WORK_DIR", tmp_path / "ui")

    first, first_error = scenario_loader.build_request_from_inputs(
        _inputs(),
        "S01_BASELINE",
        "full",
    )
    second, second_error = scenario_loader.build_request_from_inputs(
        _inputs(),
        "S01_BASELINE",
        "full",
    )

    assert first_error is None
    assert second_error is None
    assert first is not None
    assert second is not None
    assert first.request_id != second.request_id
    assert Path(first.ticket_ref).parent != Path(second.ticket_ref).parent


def test_scenario_label_includes_id_and_description() -> None:
    label = scenario_label(
        {
            "scenario_id": "S10_FIFO_BREAK_JUSTIFIED",
            "description": "Ranking must justify breaking pure FIFO.",
        }
    )

    assert label == "S10_FIFO_BREAK_JUSTIFIED · Ranking must justify breaking pure FIFO."
