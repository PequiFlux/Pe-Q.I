from __future__ import annotations

import json
import os
from contextlib import nullcontext
from typing import Any

import streamlit as st

from app.domain.models import DecisionRequest, FrontEndPayload
from app.ui.components.audit_panel import (
    copilot_timeline_card,
    render_audit,
    render_driver_message,
    render_gemma_context,
    render_input_evidence,
    render_operator_action,
    render_status_bar,
    tool_badges_card,
)
from app.ui.components.common import escape, runtime_label
from app.ui.components.decision_card import (
    blocked_constraints_card,
    gemma_extraction_card,
    queue_stack_card,
    recommended_decision_card,
)
from app.ui.components.scenario_catalog import scenario_label, scenario_note
from app.ui.components.validation_matrix import render_validation_matrix
from app.ui.input_state import (
    clear_input_state,
    ensure_input_state,
    load_case_into_state,
    queue_csv_value,
    queue_preview_html,
    queue_source_note,
    reset_result_state,
    split_ids,
    state_defaults,
    ticket_source_note_with_fixture,
    ticket_text_value,
    ui_autorun_enabled,
    upload_key,
)
from app.ui.i18n import LANGUAGE_KEY, Language, language_label, t
from app.ui.scenario_loader import (
    build_request_from_inputs,
    load_manifest,
)
from app.ui.styles import inject_styles
from app.ui.ui_runner import run_payload

EXAMPLE_SCENARIO_ID = "S10_FIFO_BREAK_JUSTIFIED"
INPUT_KEYS = {
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
    "analyze_example": "yard_analyze_example",
    "selected_case": "yard_selected_case",
}


def main() -> None:
    st.set_page_config(
        page_title="PequiFlux Yard Copilot",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    inject_styles()

    manifest = load_manifest()
    case_by_id = {case["scenario_id"]: case for case in manifest["cases"]}
    st.session_state.setdefault(INPUT_KEYS["selected_case"], EXAMPLE_SCENARIO_ID)
    selected_case_id = st.session_state[INPUT_KEYS["selected_case"]]
    if selected_case_id not in case_by_id:
        selected_case_id = EXAMPLE_SCENARIO_ID
        st.session_state[INPUT_KEYS["selected_case"]] = selected_case_id
    selected_case = case_by_id[selected_case_id]

    lang = _current_language()
    with st.sidebar:
        st.markdown(_brand_block(lang), unsafe_allow_html=True)
        lang = _render_language_picker()
        st.markdown(_sidebar_runtime_block(lang), unsafe_allow_html=True)
        _render_sidebar_case_picker(manifest["cases"], lang)

    _render_intro(lang)
    ensure_input_state(INPUT_KEYS)
    if payload := st.session_state.get("last_payload"):
        request = st.session_state.get("last_request")
    elif ui_autorun_enabled():
        load_case_into_state(INPUT_KEYS, case_by_id[EXAMPLE_SCENARIO_ID])
        st.session_state["active_case"] = EXAMPLE_SCENARIO_ID
        request, error = build_request_from_inputs(
            {**state_defaults(INPUT_KEYS), "uploaded_ticket": None},
            EXAMPLE_SCENARIO_ID,
            "full",
        )
        if error:
            _render_error(error, lang)
            return
        assert request is not None
        payload = run_payload(request)
        st.session_state["last_payload"] = payload
        st.session_state["last_request"] = request
    else:
        payload = None
        request = None

    active_case_id = st.session_state.get("active_case", "UI_INTERACTIVE")
    inputs = _render_operator_input(
        selected_case=selected_case,
        lang=lang,
        expanded=True,
        use_expander=False,
    )

    if inputs["submitted"]:
        scenario_id = active_case_id if active_case_id in case_by_id else "UI_INTERACTIVE"
        request, error = build_request_from_inputs(inputs, scenario_id, "full")
        if error:
            _render_error(error, lang)
            return
        assert request is not None
        reset_result_state()
        payload = run_payload(request)
        st.session_state["last_payload"] = payload
        st.session_state["last_request"] = request

    if payload is None or request is None:
        _render_empty_state(lang)
        return

    case = case_by_id.get(request.scenario_id, {"scenario_id": request.scenario_id})
    _render_outputs(payload, request, case, lang)


def _render_intro(lang: Language) -> None:
    st.markdown(
        f"""
        <div class="yc-root">
          <div class="yc-hero">
            <div class="yc-hero-inner">
              <div>
                <div class="yc-brand">{escape(t("hero.eyebrow", lang))}</div>
                <h1 class="yc-hero-title">{t("hero.title.html", lang)}</h1>
                <p class="yc-hero-desc">{escape(t("hero.copy", lang))}</p>
              </div>
              <div class="yc-steps">
                <div class="yc-step active">
                  <div class="yc-step-num">1</div>
                  <div class="yc-step-label">{escape(t("hero.step1", lang))}</div>
                </div>
                <div class="yc-step pending">
                  <div class="yc-step-num">2</div>
                  <div class="yc-step-label">{escape(t("hero.step2", lang))}</div>
                </div>
                <div class="yc-step pending">
                  <div class="yc-step-num">3</div>
                  <div class="yc-step-label">{escape(t("hero.step3", lang))}</div>
                </div>
              </div>
            </div>
            <div class="yc-hero-bar"><div class="yc-hero-bar-fill"></div></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_empty_state(lang: Language) -> None:
    st.markdown(
        f"""
        <article class="empty-state">
          <strong>{escape(t("empty.title", lang))}</strong>
          <p>{escape(t("empty.copy", lang, button=_analyze_button_label(lang)))}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _render_operator_input(
    *,
    selected_case: dict[str, Any],
    lang: Language,
    expanded: bool,
    use_expander: bool = True,
) -> dict[str, Any]:
    wrapper = (
        st.expander(t("input.title", lang), expanded=expanded)
        if use_expander
        else nullcontext()
    )
    with wrapper:
        st.markdown(
            f"""
            <p class="yc-section-label"><span>{escape(t("input.step", lang))}</span> {escape(t("input.title.short", lang))}</p>
            <p class="yc-section-desc">{escape(t("input.copy", lang))}</p>
            """,
            unsafe_allow_html=True,
        )
        submitted = bool(st.session_state.pop(INPUT_KEYS["analyze_example"], False))
        with st.container():
            overview_left, overview_right = st.columns([1.15, 0.85], gap="large")
            with overview_left:
                _render_input_actions(selected_case, lang)
            with overview_right:
                st.markdown(_preparation_panel(selected_case, lang), unsafe_allow_html=True)

            st.markdown(
                f"""
                <div class="yc-divider-section">
                  <span class="yc-divider-text">{escape(t("inputs.divider", lang))}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            top_a, top_b = st.columns([1.08, 0.92], gap="large")
            with top_a:
                st.markdown(
                    f"""
                    <div class="yc-upload-block">
                      <div class="yc-upload-header">
                        <span class="yc-upload-num">{escape(t("queue.title", lang))}</span>
                      </div>
                      <div class="yc-upload-body">
                    """,
                    unsafe_allow_html=True,
                )
                uploaded_queue = st.file_uploader(
                    t("queue.upload", lang),
                    type=["csv"],
                    key=upload_key(INPUT_KEYS, "queue_upload"),
                    help=t("queue.help", lang),
                )
                queue_csv = queue_csv_value(INPUT_KEYS, uploaded_queue)
                st.markdown(
                    queue_source_note(uploaded_queue, queue_csv, lang),
                    unsafe_allow_html=True,
                )
                st.markdown(queue_preview_html(queue_csv, lang), unsafe_allow_html=True)
                st.markdown("</div></div>", unsafe_allow_html=True)

            with top_b:
                st.markdown(
                    f"""
                    <div class="yc-upload-block">
                      <div class="yc-upload-header">
                        <span class="yc-upload-num">{escape(t("ticket.title", lang))}</span>
                      </div>
                      <div class="yc-upload-body">
                    """,
                    unsafe_allow_html=True,
                )
                uploaded_ticket = st.file_uploader(
                    t("ticket.upload", lang),
                    type=["txt", "pdf", "png", "jpg", "jpeg"],
                    key=upload_key(INPUT_KEYS, "ticket_upload"),
                    help=t("ticket.help", lang),
                )
                ticket_text = ticket_text_value(INPUT_KEYS, uploaded_ticket)
                st.markdown(
                    ticket_source_note_with_fixture(
                        uploaded_ticket,
                        ticket_text,
                        st.session_state.get(INPUT_KEYS["fixture_ticket_path"], ""),
                        lang,
                    ),
                    unsafe_allow_html=True,
                )
                st.markdown("</div></div>", unsafe_allow_html=True)

            step_two_enabled = _step_two_enabled(queue_csv)
            lower_a, lower_b = st.columns([1, 1], gap="large")
            with lower_a:
                st.markdown(
                    _yc_block_open(t("weather.title", lang), t("input.step2", lang)),
                    unsafe_allow_html=True,
                )
                if not step_two_enabled:
                    st.markdown(
                        _locked_step_copy(
                            title=t("weather.locked.title", lang),
                            spec=t("weather.locked.spec", lang),
                        ),
                        unsafe_allow_html=True,
                    )
                weather_json = _render_weather_input(lang, disabled=not step_two_enabled)
                st.markdown("</div></div>", unsafe_allow_html=True)
            with lower_b:
                st.markdown(
                    _yc_block_open(t("resources.title", lang), t("input.step2", lang)),
                    unsafe_allow_html=True,
                )
                if not step_two_enabled:
                    st.markdown(
                        _locked_step_copy(
                            title=t("resources.locked.title", lang),
                            spec=t("resources.locked.spec", lang),
                        ),
                        unsafe_allow_html=True,
                    )
                resource_json = _render_resource_input(lang, disabled=not step_two_enabled)
                st.markdown("</div></div>", unsafe_allow_html=True)

            operator_note = _render_optional_operator_note(lang)
            st.markdown(
                _execution_strip(
                    queue_csv=queue_csv,
                    ticket_text=ticket_text,
                    fixture_ticket_path=st.session_state.get(
                        INPUT_KEYS["fixture_ticket_path"], ""
                    ),
                    operator_note=operator_note,
                    weather_json=weather_json,
                    resource_json=resource_json,
                    lang=lang,
                ),
                unsafe_allow_html=True,
            )
            submitted = (
                st.button(_analyze_button_label(lang), type="primary", width="stretch")
                or submitted
            )

    return {
        "submitted": submitted,
        "queue_csv": queue_csv,
        "uploaded_ticket": uploaded_ticket,
        "ticket_text": ticket_text,
        "operator_note": operator_note,
        "weather_json": weather_json,
        "resource_json": resource_json,
    }


def _render_operator_note_input(lang: Language) -> str:
    note = st.text_area(
        t("operator.label", lang),
        height=116,
        key=INPUT_KEYS["operator_note"],
        placeholder=t("operator.placeholder", lang),
    )
    state = t("operator.registered", lang) if note.strip() else t("operator.optional", lang)
    st.markdown(
        f"""
        <div class="field-status neutral">
          <strong>{escape(t("operator.status", lang, state=state))}</strong>
          <span>{escape(t("operator.characters", lang, count=len(note.strip())))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return note


def _render_optional_operator_note(lang: Language) -> str:
    st.markdown(
        f"""
        <div class="yc-inline-note-head">
          <strong>{escape(t("operator.optional.title", lang))}</strong>
          <span>{escape(t("operator.optional.copy", lang))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return _render_operator_note_input(lang)


def _yc_block_open(title: str, badge: str) -> str:
    badge_html = (
        f'<span class="yc-badge yc-badge-amber" style="margin-left:auto;">{escape(badge)}</span>'
        if badge
        else ""
    )
    return f"""
    <div class="yc-upload-block">
      <div class="yc-upload-header">
        <span class="yc-upload-num">{escape(title)}</span>
        {badge_html}
      </div>
      <div class="yc-upload-body">
    """


def _step_two_enabled(queue_csv: str) -> bool:
    return bool(queue_csv.strip())


def _locked_step_copy(*, title: str, spec: str) -> str:
    return f"""
    <div class="yc-locked-note">
      <strong>{escape(title)}</strong>
      <span>{escape(spec)}</span>
    </div>
    """


def _render_weather_input(lang: Language, *, disabled: bool = False) -> str:
    current_precipitation = st.session_state.get(INPUT_KEYS["weather_precipitation"], "none")
    current_severity = st.session_state.get(INPUT_KEYS["weather_severity"], "none")
    st.markdown(
        _weather_summary(str(current_precipitation), str(current_severity), lang),
        unsafe_allow_html=True,
    )
    mode = st.radio(
        t("weather.mode", lang),
        ["formulário", "JSON"],
        horizontal=True,
        key=INPUT_KEYS["weather_mode"],
        disabled=disabled,
        format_func=lambda value: t("mode.form", lang) if value == "formulário" else value,
    )
    if mode == "JSON":
        return st.text_area(
            t("weather.json", lang),
            height=116,
            key=INPUT_KEYS["weather_json"],
            disabled=disabled,
        )
    precipitation = st.selectbox(
        t("weather.precipitation", lang),
        ["none", "rain"],
        key=INPUT_KEYS["weather_precipitation"],
        disabled=disabled,
        format_func=lambda value: {
            "none": t("weather.none", lang),
            "rain": t("weather.rain", lang),
        }.get(value, value),
    )
    severity = st.selectbox(
        t("weather.severity", lang),
        ["none", "low", "medium", "high"],
        key=INPUT_KEYS["weather_severity"],
        disabled=disabled,
        format_func=lambda value: {
            "none": t("weather.severity.none", lang),
            "low": t("weather.severity.low", lang),
            "medium": t("weather.severity.medium", lang),
            "high": t("weather.severity.high", lang),
        }.get(value, value),
    )
    return json.dumps({"precipitation": precipitation, "severity": severity})


def _render_resource_input(lang: Language, *, disabled: bool = False) -> str:
    available_count = len(split_ids(st.session_state.get(INPUT_KEYS["resource_available"], "")))
    blocked_count = len(split_ids(st.session_state.get(INPUT_KEYS["resource_blocked"], "")))
    wet_count = len(split_ids(st.session_state.get(INPUT_KEYS["resource_wet"], "")))
    st.markdown(
        _resource_summary(available_count, blocked_count, wet_count, lang),
        unsafe_allow_html=True,
    )
    mode = st.radio(
        t("resources.mode", lang),
        ["formulário", "JSON"],
        horizontal=True,
        key=INPUT_KEYS["resource_mode"],
        disabled=disabled,
        format_func=lambda value: t("mode.form", lang) if value == "formulário" else value,
    )
    if mode == "JSON":
        return st.text_area(
            t("resources.json", lang),
            height=116,
            key=INPUT_KEYS["resource_json"],
            disabled=disabled,
        )
    available = st.text_input(
        t("resources.available", lang),
        key=INPUT_KEYS["resource_available"],
        placeholder="DST-COV-01, DST-COV-02",
        help=t("resources.help.ids", lang),
        disabled=disabled,
    )
    blocked = st.text_input(
        t("resources.blocked", lang),
        key=INPUT_KEYS["resource_blocked"],
        placeholder="DST-OPEN-01",
        help=t("resources.help.ids", lang),
        disabled=disabled,
    )
    wet_destinations = st.text_input(
        t("resources.wet", lang),
        key=INPUT_KEYS["resource_wet"],
        placeholder="DST-COV-01",
        help=t("resources.help.wet", lang),
        disabled=disabled,
    )
    wet_ids = set(split_ids(wet_destinations))
    available_ids = list(dict.fromkeys([*split_ids(available), *wet_ids]))
    resources = [
        {
            "resource_id": item,
            "status": "available",
            "capacity_pct": 85,
            "resource_type": "covered_hopper",
            "exposure": "covered",
            "allowed_vehicle_types": ["truck", "bitrem"],
            "supported_load_conditions": ["dry", "wet"] if item in wet_ids else ["dry"],
        }
        for item in available_ids
    ]
    resources.extend(
        {
            "resource_id": item,
            "status": "blocked",
            "capacity_pct": 100,
            "resource_type": "open_hopper",
            "exposure": "open",
            "allowed_vehicle_types": ["truck", "bitrem"],
            "supported_load_conditions": ["dry"],
        }
        for item in split_ids(blocked)
    )
    return json.dumps(resources)


def _weather_summary(precipitation: str, severity: str, lang: Language) -> str:
    severity_label = {
        "none": t("weather.summary.severity.none", lang),
        "low": t("weather.summary.severity.low", lang),
        "medium": t("weather.summary.severity.medium", lang),
        "high": t("weather.summary.severity.high", lang),
    }.get(severity, severity)
    if precipitation == "rain":
        state = t("weather.summary.rain", lang, severity=severity_label)
        tone = "warn" if severity in {"medium", "high"} else "neutral"
    else:
        state = t("weather.summary.no_rain", lang)
        tone = "ok"
    return f"""
    <div class="field-status {tone}">
      <strong>{escape(state)}</strong>
      <span>{escape(t("weather.state", lang))}</span>
    </div>
    """


def _resource_summary(
    available_count: int,
    blocked_count: int,
    wet_count: int,
    lang: Language,
) -> str:
    tone = "warn" if blocked_count else "ok"
    return f"""
    <div class="resource-meter {tone}">
      <div><strong>{available_count}</strong><span>{escape(t("resources.metric.available", lang))}</span></div>
      <div><strong>{blocked_count}</strong><span>{escape(t("resources.metric.blocked", lang))}</span></div>
      <div><strong>{wet_count}</strong><span>{escape(t("resources.metric.wet", lang))}</span></div>
    </div>
    """


def _render_input_actions(example_case: dict[str, Any], lang: Language) -> None:
    ticket_path = str(example_case.get("files", {}).get("ticket", ""))
    ticket_kind = ticket_path.rsplit(".", 1)[-1].upper() if "." in ticket_path else "N/A"
    st.markdown(
        f"""
        <div class="yc-fixture-card">
          <div class="yc-fixture-card-head">
            <span class="yc-section-label">{escape(t("case.versioned", lang))}</span>
            <span class="yc-badge yc-badge-teal">{escape(t("case.active", lang))}</span>
          </div>
          <div class="yc-fixture-id">{escape(example_case["scenario_id"])}</div>
          <div class="yc-fixture-desc">{escape(str(example_case.get("description") or t("prep.no_description", lang)))}</div>
          <div class="yc-fixture-meta">
            <span class="yc-badge yc-badge-gray">Fixture · {escape(ticket_kind)}</span>
          </div>
        </div>
        <div class="yc-action-row">
        """,
        unsafe_allow_html=True,
    )
    left, middle, right = st.columns([1, 1.35, 0.7], gap="small")
    with left:
        if st.button(t("button.load", lang), width="stretch"):
            load_case_into_state(INPUT_KEYS, example_case)
            st.session_state["active_case"] = example_case["scenario_id"]
            st.rerun()
    with middle:
        if st.button(t("button.load_analyze", lang), width="stretch"):
            load_case_into_state(INPUT_KEYS, example_case)
            st.session_state["active_case"] = example_case["scenario_id"]
            st.session_state[INPUT_KEYS["analyze_example"]] = True
            st.rerun()
    with right:
        if st.button(t("button.clear", lang), width="stretch"):
            clear_input_state(INPUT_KEYS)
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _preparation_panel(selected_case: dict[str, Any], lang: Language) -> str:
    description = str(selected_case.get("description") or t("prep.no_description", lang))
    return f"""
    <div class="yc-bancada">
      <div class="yc-bancada-header">
        <div>
          <div class="yc-bancada-title">{escape(selected_case["scenario_id"])}</div>
          <div class="yc-bancada-subtitle">{escape(description)}</div>
        </div>
      </div>
      <div class="yc-runtime-strip">
        <div class="yc-runtime-pill">
          <div style="display:flex;align-items:center;gap:6px;"><span class="yc-status-dot"></span><span class="yc-runtime-val">{escape(runtime_label())}</span></div>
          <div class="yc-runtime-key">{escape(t("prep.runtime", lang))}</div>
        </div>
        <div class="yc-runtime-pill">
          <div class="yc-runtime-val" style="color:var(--color-text-secondary);">{escape(t("prep.no_fallback.value", lang))}</div>
          <div class="yc-runtime-key">{escape(t("prep.no_fallback.label", lang))}</div>
        </div>
      </div>
      <div class="yc-bancada-body">
        <div class="yc-guide-row">
          <div class="yc-guide-key">{escape(t("prep.load", lang))}</div>
          <div class="yc-guide-val">{escape(t("prep.load.copy", lang))}</div>
        </div>
        <div class="yc-guide-row">
          <div class="yc-guide-key">{escape(t("prep.complete", lang))}</div>
          <div class="yc-guide-val">{escape(t("prep.complete.copy", lang))}</div>
        </div>
        <div class="yc-guide-row">
          <div class="yc-guide-key">{escape(t("prep.confirm", lang))}</div>
          <div class="yc-guide-val">{escape(t("prep.confirm.copy", lang))}</div>
        </div>
      </div>
    </div>
    """


def _analysis_console(
    *,
    queue_csv: str,
    ticket_text: str,
    fixture_ticket_path: str,
    operator_note: str,
    weather_json: str,
    resource_json: str,
    lang: Language,
) -> str:
    checks = [
        (
            t("ready.queue", lang),
            bool(queue_csv.strip()),
            t("ready.queue.ok", lang) if queue_csv.strip() else t("ready.queue.pending", lang),
        ),
        (
            t("ready.doc", lang),
            bool(ticket_text.strip() or fixture_ticket_path.strip()),
            (
                t("ready.doc.ok", lang)
                if ticket_text.strip() or fixture_ticket_path.strip()
                else t("ready.doc.pending", lang)
            ),
        ),
        (
            t("ready.weather", lang),
            bool(weather_json.strip()),
            t("ready.weather.ok", lang)
            if weather_json.strip()
            else t("ready.weather.pending", lang),
        ),
        (
            t("ready.resources", lang),
            bool(resource_json.strip()),
            t("ready.resources.ok", lang)
            if resource_json.strip()
            else t("ready.resources.pending", lang),
        ),
    ]
    ready_count = sum(1 for _, ready, _ in checks if ready)
    headline = (
        t("ready.headline.ok", lang)
        if ready_count == len(checks)
        else t("ready.headline.pending", lang)
    )
    note_state = (
        t("ready.note.ok", lang) if operator_note.strip() else t("ready.note.optional", lang)
    )
    checklist = "".join(
        _readiness_item(name, ready, detail, lang) for name, ready, detail in checks
    )
    return f"""
    <article class="prep-card action-console">
      <div class="card-head">
        <div>
          <h3>{escape(headline)}</h3>
          <p>{escape(t("ready.summary", lang, ready=ready_count, total=len(checks), note=note_state))}</p>
        </div>
        <span class="chip green">{escape(t("ready.container", lang))}</span>
      </div>
      <div class="readiness-grid">
        {checklist}
      </div>
      <div class="run-strip emphasize">
        <div><strong>{escape(t("run.runtime", lang))}</strong> {escape(runtime_label())}</div>
        <div class="run-note">{t("run.note", lang)}</div>
      </div>
    </article>
    """


def _execution_strip(
    *,
    queue_csv: str,
    ticket_text: str,
    fixture_ticket_path: str,
    operator_note: str,
    weather_json: str,
    resource_json: str,
    lang: Language,
) -> str:
    weather_ready = bool(weather_json.strip()) and weather_json.strip() not in {"{}", ""}
    resource_ready = bool(resource_json.strip()) and resource_json.strip() not in {"[]", ""}
    step_two_active = _step_two_enabled(queue_csv)
    checks = [
        bool(queue_csv.strip()),
        bool(ticket_text.strip() or fixture_ticket_path.strip()),
        step_two_active and weather_ready,
        step_two_active and resource_ready,
    ]
    ready_count = sum(1 for item in checks if item)
    note_state = (
        t("ready.note.ok", lang) if operator_note.strip() else t("ready.note.optional", lang)
    )
    return f"""
    <div class="run-strip emphasize yc-execution-strip">
      <div><strong>{escape(t("run.runtime", lang))}</strong> {escape(runtime_label())}</div>
      <div class="run-note">{escape(t("ready.summary", lang, ready=ready_count, total=len(checks), note=note_state))}</div>
    </div>
    """


def _readiness_item(name: str, ready: bool, detail: str, lang: Language) -> str:
    state_class = "ok" if ready else "pending"
    state_label = t("ready.state.ok", lang) if ready else t("ready.state.pending", lang)
    return f"""
    <div class="readiness-item {state_class}">
      <strong>{escape(name)}</strong>
      <span>{escape(state_label)}</span>
      <p>{escape(detail)}</p>
    </div>
    """


def _render_outputs(
    payload: FrontEndPayload,
    request: DecisionRequest,
    case: dict[str, Any],
    lang: Language,
) -> None:
    st.markdown(
        f"""
        <div class="section-title">
          <div><h2>{escape(t("output.title", lang))}</h2><p>{escape(t("output.copy", lang))}</p></div>
          <span class="chip success">{escape(t("output.badge", lang))}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    render_status_bar(payload, lang=lang)
    st.markdown(recommended_decision_card(payload, lang=lang), unsafe_allow_html=True)
    st.markdown(queue_stack_card(payload, request, lang=lang), unsafe_allow_html=True)
    first_left, first_right = st.columns([1, 1], gap="large")
    with first_left:
        st.markdown(gemma_extraction_card(payload, request, lang=lang), unsafe_allow_html=True)
    with first_right:
        st.markdown(blocked_constraints_card(payload, lang=lang), unsafe_allow_html=True)

    second_left, second_right = st.columns([1, 1], gap="large")
    with second_left:
        render_driver_message(payload, lang=lang)
    with second_right:
        render_operator_action(payload, lang=lang)

    _render_technical_audit_expander(payload, request, case, lang)


def _render_technical_audit_expander(
    payload: FrontEndPayload,
    request: DecisionRequest,
    case: dict[str, Any],
    lang: Language,
) -> None:
    with st.expander(t("audit.expander", lang), expanded=ui_autorun_enabled()):
        render_input_evidence(payload, request, case)
        st.markdown(copilot_timeline_card(payload, request), unsafe_allow_html=True)
        left, right = st.columns([1.15, 0.85], gap="large")
        with left:
            render_validation_matrix(payload)
        with right:
            render_gemma_context(payload, request)
            st.markdown(tool_badges_card(payload), unsafe_allow_html=True)
        render_audit(payload)
        st.json(payload.model_dump(mode="json"))


def _render_error(error: str, lang: Language = "pt") -> None:
    st.markdown(
        f"""
        <article class="error-card">
          <strong>{escape(t("error.title", lang))}</strong>
          <p>{escape(error)}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _current_language() -> Language:
    value = st.session_state.get(LANGUAGE_KEY, "pt")
    return "en" if value == "en" else "pt"


def _render_language_picker() -> Language:
    st.markdown(
        f"""
        <div class="side-card compact">
          <div class="side-kicker">{escape(t("sidebar.language.kicker", _current_language()))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.radio(
        t("sidebar.language.kicker", _current_language()),
        options=["pt", "en"],
        key=LANGUAGE_KEY,
        horizontal=True,
        format_func=lambda value: language_label("en" if value == "en" else "pt"),
        label_visibility="collapsed",
    )
    return _current_language()


def _brand_block(lang: Language) -> str:
    return f"""
    <div class="brand">
      <div class="brand-mark"></div>
      <div>
        <h1>PequiFlux</h1>
        <p>{escape(t("brand.subtitle", lang))}</p>
      </div>
    </div>
    """


def _sidebar_runtime_block(lang: Language) -> str:
    return f"""
    <div class="side-card compact">
      <div class="side-kicker">{escape(t("sidebar.runtime.kicker", lang))}</div>
      <p>{escape(runtime_label())}</p>
      <p>{escape(_runtime_mode_note(lang))}</p>
      <p>{escape(t("sidebar.no_fallback", lang))}</p>
    </div>
    """


def _render_sidebar_case_picker(cases: list[dict[str, Any]], lang: Language) -> None:
    st.markdown(
        f"""
        <div class="side-card compact">
          <div class="side-kicker">{escape(t("sidebar.fixtures.kicker", lang))}</div>
          <p>{escape(t("sidebar.fixtures.copy", lang))}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.selectbox(
        t("sidebar.scenario.label", lang),
        options=[case["scenario_id"] for case in cases],
        key=INPUT_KEYS["selected_case"],
        format_func=lambda scenario_id: scenario_label(
            next(case for case in cases if case["scenario_id"] == scenario_id)
        ),
    )


def _runtime_mode_note(lang: Language) -> str:
    runtime = os.getenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama")
    if runtime == "text":
        return t("runtime.text.note", lang)
    if runtime == "ollama":
        return t("runtime.ollama.note", lang)
    return t("runtime.custom.note", lang, runtime=runtime)


def _analyze_button_label(lang: Language = "pt") -> str:
    if os.getenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama") == "text":
        return t("button.analyze_text", lang)
    return t("button.analyze_gemma", lang)


if __name__ == "__main__":
    main()
