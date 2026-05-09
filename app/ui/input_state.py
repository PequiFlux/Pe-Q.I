from __future__ import annotations

import csv
import os
from typing import Any

import streamlit as st

from app.ui.components.common import escape
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


def queue_source_note(uploaded_queue: Any, queue_csv: str) -> str:
    if uploaded_queue is not None:
        source = f"Arquivo carregado: {uploaded_queue.name}"
    elif queue_csv:
        source = "Caso versionado carregado como CSV de fixture."
    else:
        source = "Nenhuma fila carregada."
    return f'<div class="source-note">{escape(source)}</div>'


def ticket_source_note(uploaded_ticket: Any, ticket_text: str) -> str:
    if uploaded_ticket is not None:
        source = f"Arquivo carregado: {uploaded_ticket.name}"
    elif ticket_text:
        source = "Caso versionado carregado como ticket TXT de fixture."
    else:
        source = "Nenhum ticket carregado."
    return f'<div class="source-note">{escape(source)}</div>'


def split_ids(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def queue_preview_html(queue_csv: str) -> str:
    try:
        rows = list(csv.DictReader(queue_csv.splitlines()))
    except csv.Error:
        rows = []
    waiting = sum(1 for row in rows if (row.get("status") or "waiting").lower() == "waiting")
    priority = sum(1 for row in rows if (row.get("contract_priority_flag") or "").lower() == "true")
    return f"""
    <div class="input-summary">
      <div><strong>{len(rows)}</strong><span>linhas</span></div>
      <div><strong>{waiting}</strong><span>aguardando</span></div>
      <div><strong>{priority}</strong><span>prioridade</span></div>
    </div>
    """


def empty_defaults() -> dict[str, Any]:
    return {
        "queue_csv": "",
        "ticket_text": "",
        "operator_note": "",
        "weather_json": '{\n  "precipitation": "none",\n  "severity": "none"\n}',
        "resource_json": "[]",
        "weather_mode": "JSON",
        "resource_mode": "JSON",
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
    for key in list(st.session_state.keys()):
        if key in input_keys.values() or is_upload_widget_key(input_keys, key):
            st.session_state.pop(key, None)
    st.session_state.pop("active_case", None)
    st.session_state.pop("last_payload", None)
    st.session_state.pop("last_request", None)
    defaults = empty_defaults()
    for field, value in defaults.items():
        st.session_state.setdefault(input_keys[field], value)


def state_defaults(input_keys: dict[str, str]) -> dict[str, str]:
    ensure_input_state(input_keys)
    return {
        field: st.session_state[input_keys[field]]
        for field in ("queue_csv", "ticket_text", "operator_note", "weather_json", "resource_json")
    }


def load_case_into_state(input_keys: dict[str, str], case: dict[str, Any]) -> None:
    reset_uploaders(input_keys)
    defaults = load_case_defaults(case)
    for field in ("queue_csv", "ticket_text", "operator_note", "weather_json", "resource_json"):
        st.session_state[input_keys[field]] = defaults[field]
    st.session_state[input_keys["weather_mode"]] = "JSON"
    st.session_state[input_keys["resource_mode"]] = "JSON"
    st.session_state.pop("last_payload", None)
    st.session_state.pop("last_request", None)


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
