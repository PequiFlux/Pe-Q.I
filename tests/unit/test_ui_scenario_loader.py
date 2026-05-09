from __future__ import annotations

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


def test_scenario_label_includes_id_and_description() -> None:
    label = scenario_label(
        {
            "scenario_id": "S10_FIFO_BREAK_JUSTIFIED",
            "description": "Ranking must justify breaking pure FIFO.",
        }
    )

    assert label == "S10_FIFO_BREAK_JUSTIFIED · Ranking must justify breaking pure FIFO."
