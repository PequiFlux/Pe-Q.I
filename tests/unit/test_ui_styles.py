from __future__ import annotations

from app.ui.styles import inject_styles


def test_inject_styles_loads_combined_stylesheet(monkeypatch) -> None:
    calls: list[tuple[str, bool]] = []

    def fake_markdown(value: str, *, unsafe_allow_html: bool) -> None:
        calls.append((value, unsafe_allow_html))

    monkeypatch.setattr("app.ui.styles.st.markdown", fake_markdown)

    inject_styles()

    assert len(calls) == 1
    payload, unsafe = calls[0]
    assert unsafe is True
    assert payload.startswith("<style>")
    assert ".hero" in payload
    assert ".yc-hero" in payload
    assert ".yc-bancada" in payload
    assert ".yc-upload-block" in payload
    assert ".tool-grid" in payload
    assert ".scenario-note" in payload
    assert ".prep-card" in payload
    assert ".field-status" in payload
    assert ".resource-meter" in payload
    assert 'div[data-testid="stSidebarCollapsedControl"]' in payload
    assert 'div[data-testid="stFileUploader"]' in payload
    assert 'header[data-testid="stHeader"]' in payload
    assert 'header[data-testid="stHeader"],' not in payload
