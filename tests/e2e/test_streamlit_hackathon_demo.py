from __future__ import annotations

from collections.abc import Iterable

from streamlit.testing.v1 import AppTest


QUEUE_CSV = b"""truck_id,arrival_ts,status,vehicle_type,contract_priority_flag
TRK-UP-01,2026-05-14T08:00:00Z,waiting,truck,false
"""
TICKET_TXT = b"Ticket TCK-UP-01: truck TRK-UP-01 load dry destination DST-COV-01."


def _app(monkeypatch, tmp_path, runtime: str = "text") -> AppTest:
    monkeypatch.setenv("PEQUIFLUX_GEMMA_RUNTIME", runtime)
    monkeypatch.delenv("PEQUIFLUX_UI_AUTORUN", raising=False)
    monkeypatch.setenv("PEQUIFLUX_JSONL_LOG_PATH", str(tmp_path / "logs" / "events.jsonl"))
    monkeypatch.setenv("PEQUIFLUX_SQLITE_PATH", str(tmp_path / "var" / "pequiflux.db"))
    monkeypatch.setattr("app.ui.scenario_loader.UI_WORK_DIR", tmp_path / "ui_sessions")
    return AppTest.from_file("app/ui/streamlit_app.py", default_timeout=180)


def _markdown_body(at: AppTest) -> str:
    return "\n".join(str(node.value) for node in at.markdown)


def _button_labels(at: AppTest) -> list[str]:
    return [button.label for button in at.button]


def _click_button(at: AppTest, label: str) -> AppTest:
    labels = _button_labels(at)
    assert label in labels
    return at.button[labels.index(label)].click().run()


def _radio_by_label(at: AppTest, labels: Iterable[str]):
    expected = set(labels)
    for radio in at.radio:
        if radio.label in expected:
            return radio
    raise AssertionError([(radio.label, radio.value, radio.options) for radio in at.radio])


def _selectbox_by_label(at: AppTest, labels: Iterable[str]):
    expected = set(labels)
    for selectbox in at.selectbox:
        if selectbox.label in expected:
            return selectbox
    raise AssertionError(
        [(selectbox.label, selectbox.value, selectbox.options) for selectbox in at.selectbox]
    )


def _scenario_selectbox(at: AppTest):
    for selectbox in at.selectbox:
        if selectbox.label in {"Exemplo versionado", "Versioned example"}:
            return selectbox
    raise AssertionError([(selectbox.label, len(selectbox.options)) for selectbox in at.selectbox])


def _radio_options(at: AppTest, label: str) -> list[str]:
    for radio in at.radio:
        if radio.label == label:
            return list(radio.options)
    raise AssertionError([(radio.label, radio.options) for radio in at.radio])


def _assert_all_resource_inputs_disabled(at: AppTest) -> None:
    assert all(getattr(text_input, "disabled", None) for text_input in at.text_input)


def _assert_all_resource_inputs_enabled(at: AppTest) -> None:
    assert not any(getattr(text_input, "disabled", None) for text_input in at.text_input)


def test_hackathon_demo_ui_navigation_and_options(monkeypatch, tmp_path) -> None:
    at = _app(monkeypatch, tmp_path).run()

    assert _button_labels(at) == [
        "Carregar exemplo",
        "Carregar e analisar exemplo",
        "Limpar campos",
        "Analisar em modo teste",
    ]
    assert "Preencha os campos" in _markdown_body(at)
    _assert_all_resource_inputs_disabled(at)

    at = _click_button(at, "Analisar em modo teste")
    assert "Entrada inválida" in _markdown_body(at)

    _radio_by_label(at, {"Idioma", "Language"}).set_value("en").run()
    assert "Load and analyze example" in _button_labels(at)
    assert _selectbox_by_label(at, {"Versioned example"}).value == "S10_FIFO_BREAK_JUSTIFIED"

    _radio_by_label(at, {"Idioma", "Language"}).set_value("pt").run()
    assert "Carregar e analisar exemplo" in _button_labels(at)

    scenario_options = list(_scenario_selectbox(at).options)
    assert len(scenario_options) == 20
    for scenario_label in scenario_options:
        _scenario_selectbox(at).set_value(scenario_label).run()
        at = _click_button(at, "Carregar exemplo")
        scenario_id = scenario_label.split(" · ", 1)[0]
        assert scenario_id in _markdown_body(at)
        _assert_all_resource_inputs_enabled(at)

    _radio_by_label(at, {"Modo de clima", "Weather mode"}).set_value("JSON").run()
    assert any(text_area.label == "Clima JSON" for text_area in at.text_area)
    _radio_by_label(at, {"Modo de recursos", "Resource mode"}).set_value("JSON").run()
    assert any(text_area.label == "Recursos JSON" for text_area in at.text_area)
    _radio_by_label(at, {"Modo de clima", "Weather mode"}).set_value("formulário").run()
    _radio_by_label(at, {"Modo de recursos", "Resource mode"}).set_value("formulário").run()
    assert _selectbox_by_label(at, {"Precipitação", "Precipitation"}).value in {"none", "rain"}

    at = _app(monkeypatch, tmp_path).run()
    at.file_uploader[0].upload("queue.csv", QUEUE_CSV, "text/csv").run()
    at.file_uploader[1].upload("ticket.txt", TICKET_TXT, "text/plain").run()
    _assert_all_resource_inputs_enabled(at)
    at.text_input[0].set_value("DST-COV-01").run()
    at.text_input[2].set_value("DST-COV-01").run()
    at = _app(monkeypatch, tmp_path).run()
    s10_label = next(
        option
        for option in _scenario_selectbox(at).options
        if option.startswith("S10_FIFO_BREAK_JUSTIFIED")
    )
    at = _scenario_selectbox(at).set_value(s10_label).run()
    at = _click_button(at, "Carregar e analisar exemplo")
    body = _markdown_body(at)
    assert "Resultado da análise" in body
    assert "Momento da decisão" in body
    assert "Chamar TRK-" in body
    assert "para DST-COV-01" in body
    assert "Decisão auditável gerada para ação humana" in body
    assert "Modo teste ativo" in body
    assert "TRK-005" in body
    assert "DST-COV-01" in body
    assert "Mensagem ao motorista" in body
    assert "Ação do operador" in body
    assert any(expander.label == "Ver auditoria técnica" for expander in at.expander)
    assert "Prova Gemma 4 para a banca" in body
    assert "PREVIEW_READY" not in body
    assert _radio_options(at, "Ação") == ["aprovar", "bloquear", "sobrescrever"]
    assert any(text_input.label == "Motivo obrigatório" for text_input in at.text_input)
    assert "Registrar ação" in _button_labels(at)
    assert "Nova análise" in _button_labels(at)

    _radio_by_label(at, {"Idioma", "Language"}).set_value("en").run()
    assert "Analysis result" in _markdown_body(at)
    assert "New analysis" in _button_labels(at)

    _radio_by_label(at, {"Idioma", "Language"}).set_value("pt").run()
    at = _click_button(at, "Nova análise")
    body = _markdown_body(at)
    assert "Preencha os campos" in body
    assert "Resultado da análise" not in body
    _assert_all_resource_inputs_disabled(at)


def test_hackathon_demo_gemma_runtime_surface_without_calling_model(monkeypatch, tmp_path) -> None:
    at = _app(monkeypatch, tmp_path, runtime="ollama").run()
    body = _markdown_body(at)

    assert "Analisar com Gemma 4" in _button_labels(at)
    assert "Analisar em modo teste" not in _button_labels(at)
    assert "Gemma 4 ativo via Ollama." in body
    assert "Sem fallback operacional" in body
