from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import Any

import streamlit as st

from app.ui.components.common import escape
from app.ui.i18n import Language, t
from app.ui.scenario_loader import load_case_defaults


def queue_csv_value(input_keys: dict[str, str], uploaded_queue: Any) -> str:
    if uploaded_queue is None:
        return st.session_state.get(input_keys["queue_csv"], "")
    try:
        return uploaded_queue.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        return ""


def ticket_text_value(input_keys: dict[str, str], uploaded_ticket: Any) -> str:
    if uploaded_ticket is None:
        return st.session_state.get(input_keys["ticket_text"], "")
    if not uploaded_ticket.name.lower().endswith(".txt"):
        return ""
    try:
        return uploaded_ticket.getvalue().decode("utf-8")
    except UnicodeDecodeError:
        return ""


def queue_source_note(uploaded_queue: Any, queue_csv: str, lang: Language = "pt") -> str:
    if uploaded_queue is not None:
        source = t("queue.source.uploaded", lang, name=uploaded_queue.name)
    elif queue_csv:
        source = t("queue.source.fixture", lang)
    else:
        source = t("queue.source.empty", lang)
    return f'<div class="source-note">{escape(source)}</div>'


def ticket_source_note(uploaded_ticket: Any, ticket_text: str, lang: Language = "pt") -> str:
    if uploaded_ticket is not None:
        source = t("ticket.source.uploaded", lang, name=uploaded_ticket.name)
    elif ticket_text:
        source = t("ticket.source.fixture_text", lang)
    else:
        source = t("ticket.source.empty", lang)
    return f'<div class="source-note">{escape(source)}</div>'


def ticket_source_note_with_fixture(
    uploaded_ticket: Any,
    ticket_text: str,
    fixture_ticket_path: str,
    lang: Language = "pt",
) -> str:
    if uploaded_ticket is not None or ticket_text:
        return ticket_source_note(uploaded_ticket, ticket_text, lang)
    if fixture_ticket_path:
        suffix = Path(fixture_ticket_path).suffix.lower().lstrip(".").upper() or "FILE"
        source = t("ticket.source.fixture_file", lang, suffix=suffix)
        return f'<div class="source-note">{escape(source)}</div>'
    return ticket_source_note(uploaded_ticket, ticket_text, lang)


def split_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def queue_preview_html(queue_csv: str, lang: Language = "pt") -> str:
    try:
        rows = list(csv.DictReader(queue_csv.splitlines()))
    except csv.Error:
        rows = []
    waiting = sum(1 for row in rows if (row.get("status") or "waiting").lower() == "waiting")
    priority = sum(1 for row in rows if (row.get("contract_priority_flag") or "").lower() == "true")
    return f"""
    <div class="input-summary">
      <div><strong>{len(rows)}</strong><span>{escape(t("queue.metric.rows", lang))}</span></div>
      <div><strong>{waiting}</strong><span>{escape(t("queue.metric.waiting", lang))}</span></div>
      <div><strong>{priority}</strong><span>{escape(t("queue.metric.priority", lang))}</span></div>
    </div>
    """


def empty_defaults() -> dict[str, Any]:
    return {
        "queue_csv": "",
        "ticket_text": "",
        "fixture_ticket_path": "",
        "fixture_ticket_content_type": "",
        "operator_note": "",
        "weather_json": '{\n  "precipitation": "none",\n  "severity": "none"\n}',
        "resource_json": "[]",
        "weather_mode": "formulário",
        "resource_mode": "formulário",
        "weather_precipitation": "none",
        "weather_severity": "none",
        "resource_available": "",
        "resource_blocked": "",
        "resource_wet": "",
        "upload_generation": 0,
    }


def ensure_input_state(input_keys: dict[str, str]) -> None:
    defaults = empty_defaults()
    for field, value in defaults.items():
        key = input_keys[field]
        if key in {input_keys["queue_upload"], input_keys["ticket_upload"]}:
            continue
        st.session_state.setdefault(key, value)


def clear_input_state(input_keys: dict[str, str]) -> None:
    selected_case = st.session_state.get(input_keys["selected_case"])
    for key in list(st.session_state.keys()):
        if key in input_keys.values() or is_upload_widget_key(input_keys, key):
            st.session_state.pop(key, None)
    st.session_state.pop("active_case", None)
    reset_result_state()
    defaults = empty_defaults()
    for field, value in defaults.items():
        st.session_state.setdefault(input_keys[field], value)
    if selected_case is not None:
        st.session_state[input_keys["selected_case"]] = selected_case


def state_defaults(input_keys: dict[str, str]) -> dict[str, str]:
    ensure_input_state(input_keys)
    return {
        field: st.session_state[input_keys[field]]
        for field in (
            "queue_csv",
            "ticket_text",
            "fixture_ticket_path",
            "fixture_ticket_content_type",
            "operator_note",
            "weather_json",
            "resource_json",
        )
    }


def load_case_into_state(input_keys: dict[str, str], case: dict[str, Any]) -> None:
    reset_uploaders(input_keys)
    defaults = load_case_defaults(case)
    for field in (
        "queue_csv",
        "ticket_text",
        "fixture_ticket_path",
        "fixture_ticket_content_type",
        "operator_note",
        "weather_json",
        "resource_json",
    ):
        st.session_state[input_keys[field]] = defaults[field]
    _sync_weather_form_state(input_keys, defaults["weather_json"])
    _sync_resource_form_state(input_keys, defaults["resource_json"])
    st.session_state[input_keys["weather_mode"]] = "formulário"
    st.session_state[input_keys["resource_mode"]] = "formulário"
    reset_result_state()


def _sync_weather_form_state(input_keys: dict[str, str], weather_json: str) -> None:
    try:
        weather = json.loads(weather_json)
    except json.JSONDecodeError:
        return
    precipitation = str(weather.get("precipitation") or "none")
    severity = str(weather.get("severity") or "none")
    if precipitation in {"none", "rain"}:
        st.session_state[input_keys["weather_precipitation"]] = precipitation
    if severity in {"none", "low", "medium", "high"}:
        st.session_state[input_keys["weather_severity"]] = severity


def _sync_resource_form_state(input_keys: dict[str, str], resource_json: str) -> None:
    try:
        resources = json.loads(resource_json)
    except json.JSONDecodeError:
        return
    if not isinstance(resources, list):
        return
    available: list[str] = []
    blocked: list[str] = []
    wet: list[str] = []
    for resource in resources:
        if not isinstance(resource, dict):
            continue
        resource_id = str(resource.get("resource_id") or "").strip()
        if not resource_id:
            continue
        if resource.get("status") == "blocked":
            blocked.append(resource_id)
        else:
            available.append(resource_id)
        supported = resource.get("supported_load_conditions") or []
        if isinstance(supported, list) and "wet" in supported:
            wet.append(resource_id)
    st.session_state[input_keys["resource_available"]] = ", ".join(dict.fromkeys(available))
    st.session_state[input_keys["resource_blocked"]] = ", ".join(dict.fromkeys(blocked))
    st.session_state[input_keys["resource_wet"]] = ", ".join(dict.fromkeys(wet))


def upload_key(input_keys: dict[str, str], field: str) -> str:
    generation = st.session_state.get(input_keys["upload_generation"], 0)
    return f"{input_keys[field]}_{generation}"


def reset_uploaders(input_keys: dict[str, str]) -> None:
    generation = int(st.session_state.get(input_keys["upload_generation"], 0)) + 1
    for key in list(st.session_state.keys()):
        if is_upload_widget_key(input_keys, key):
            st.session_state.pop(key, None)
    st.session_state[input_keys["upload_generation"]] = generation


def is_upload_widget_key(input_keys: dict[str, str], key: str) -> bool:
    return key.startswith(f"{input_keys['queue_upload']}_") or key.startswith(
        f"{input_keys['ticket_upload']}_"
    )


def ui_autorun_enabled() -> bool:
    return os.getenv("PEQUIFLUX_UI_AUTORUN", "").strip().lower() in {"1", "true", "yes"}


def reset_result_state() -> None:
    st.session_state.pop("last_payload", None)
    st.session_state.pop("last_request", None)
    st.session_state.pop("operator_finalization", None)
    st.session_state.pop("operator_audit_update", None)
