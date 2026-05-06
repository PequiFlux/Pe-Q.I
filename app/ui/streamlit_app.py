from __future__ import annotations

import csv
import os
from contextlib import nullcontext
from pathlib import Path
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
from app.ui.benchmark_summary import load_benchmark_summary
from app.ui.components.common import escape
from app.ui.components.decision_card import (
    blocked_constraints_card,
    gemma_extraction_card,
    judge_comparison_card,
    queue_stack_card,
    recommended_decision_card,
    why_not_fifo_card,
)
from app.ui.components.validation_matrix import render_validation_matrix
from app.ui.scenario_loader import (
    build_request_from_inputs,
    judge_request,
    load_case_defaults,
    load_manifest,
)
from app.ui.styles import inject_styles
from app.ui.ui_runner import run_payload_pair

BENCHMARK_REPORTS_DIR = Path("bench/reports")
JUDGE_SCENARIOS = [
    {
        "scenario_id": "S10_FIFO_BREAK_JUSTIFIED",
        "title": "Chuva bloqueando moega aberta",
        "story": "A chuva derruba a legitimidade do FIFO puro e a compatibilidade define quem pode ir.",
        "gemma": "Leitura confirma ticket seco, placa e destino esperado.",
        "rule": "HC-01, HC-05",
    },
    {
        "scenario_id": "S03_WET_LOAD",
        "title": "Carga umida exige moega compativel",
        "story": "A fila favorece um destino seco, mas o ticket chega como imagem e sustenta a revisao correta.",
        "gemma": "Leitura extrai carga umida, placa e restricao de destino a partir da imagem.",
        "rule": "HC-02",
    },
    {
        "scenario_id": "S06_DOCUMENT_BLOCK",
        "title": "Documento ambiguo pede revisao humana",
        "story": "O primeiro da fila nao pode ser despachado automaticamente enquanto a nota exige conferencia.",
        "gemma": "Leitura identifica status documental e campos que exigem revisao.",
        "rule": "HC-04",
    },
]


def main() -> None:
    st.set_page_config(page_title="PequiFlux Yard Copilot", layout="wide")
    inject_styles()

    manifest = load_manifest()
    case_by_id = {case["scenario_id"]: case for case in manifest["cases"]}

    with st.sidebar:
        st.markdown(_brand_block(), unsafe_allow_html=True)
        st.markdown(
            f"""
            <div class="side-card">
              <div class="side-kicker">Fluxo da demo</div>
              <ol>
                <li>Escolher caso narrativo</li>
                <li>Comparar FIFO vs Pe-Q.I</li>
                <li>Conferir regra aplicada</li>
                <li>Operador aprova, bloqueia ou sobrescreve</li>
              </ol>
            </div>
            <div class="side-card compact">
              <div class="side-kicker">Leitura do documento</div>
              <p>{escape(_runtime_label())}</p>
              <p>Sem fallback operacional. Se faltar verdade material, o fluxo fecha em BLOCKED ou REVIEW_REQUIRED.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    _render_intro()
    _render_benchmark_strip()
    judge_submitted, scenario_id = _render_judge_mode(case_by_id)
    variant = "full"
    case = case_by_id[scenario_id]
    defaults = load_case_defaults(case)

    inputs = _render_technical_mode(defaults, case_by_id, scenario_id, variant)
    if inputs["scenario_id"] != scenario_id or inputs["variant"] != variant:
        scenario_id = inputs["scenario_id"]
        variant = inputs["variant"]
        case = case_by_id[scenario_id]
        defaults = load_case_defaults(case)

    if judge_submitted:
        request = judge_request(case)
        payload, fifo_payload = run_payload_pair(request)
        st.session_state["last_payload"] = payload
        st.session_state["last_request"] = request
        st.session_state["last_fifo_payload"] = fifo_payload
    elif inputs["submitted"]:
        request, error = build_request_from_inputs(inputs, scenario_id, variant)
        if error:
            _render_error(error)
            return
        assert request is not None
        payload, fifo_payload = run_payload_pair(request)
        st.session_state["last_payload"] = payload
        st.session_state["last_request"] = request
        st.session_state["last_fifo_payload"] = fifo_payload

    payload = st.session_state.get("last_payload")
    request = st.session_state.get("last_request")
    fifo_payload = st.session_state.get("last_fifo_payload")
    if payload is None and _ui_autorun_enabled():
        request = judge_request(case)
        payload, fifo_payload = run_payload_pair(request)
        st.session_state["last_payload"] = payload
        st.session_state["last_request"] = request
        st.session_state["last_fifo_payload"] = fifo_payload
    if payload is None or request is None:
        _render_judge_empty_state()
        return

    _render_outputs(payload, request, case, fifo_payload)


def _render_intro() -> None:
    st.markdown(
        """
        <section class="hero">
          <div>
            <span class="eyebrow">PequiFlux Yard Copilot · Hackathon</span>
            <h1>Gemma interpreta. Regras decidem. Operador governa.</h1>
            <p>Copiloto local-first para fila de pátio: documento, contexto operacional, regras de bloqueio e decisão auditável em uma tela.</p>
          </div>
          <div class="hero-proof">
            <div><strong>Documento</strong><span>interpretado</span></div>
            <div><strong>Regras</strong><span>conferidas</span></div>
            <div><strong>Operador</strong><span>aprova ou bloqueia</span></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_benchmark_strip() -> None:
    summary = load_benchmark_summary(BENCHMARK_REPORTS_DIR)
    st.markdown(
        f"""
        <section class="benchmark-strip">
          <div>
            <span>Full</span>
            <strong>{escape(summary["full"])}</strong>
          </div>
          <div>
            <span>FIFO</span>
            <strong>{escape(summary["fifo"])}</strong>
          </div>
          <div>
            <span>Heuristico</span>
            <strong>{escape(summary["heuristic"])}</strong>
          </div>
          <small>{escape(summary["source"])}</small>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_judge_mode(case_by_id: dict[str, dict[str, Any]]) -> tuple[bool, str]:
    selected = st.session_state.get("judge_scenario_id", JUDGE_SCENARIOS[0]["scenario_id"])
    st.markdown(
        """
        <div class="section-title judge-title">
          <div><h2>Judge Mode</h2><p>Tres casos prontos para a banca entender em 20 segundos onde FIFO falha e onde o operador continua no controle.</p></div>
          <span class="chip success">modo avaliador</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
    submitted = False
    for column, scenario in zip(st.columns(3, gap="large"), JUDGE_SCENARIOS):
        scenario_id = scenario["scenario_id"]
        with column:
            st.markdown(_judge_case_card(scenario, selected == scenario_id), unsafe_allow_html=True)
            if st.button(
                "Executar caso",
                key=f"judge-run-{scenario_id}",
                type="primary" if selected == scenario_id else "secondary",
                width="stretch",
            ):
                st.session_state["judge_scenario_id"] = scenario_id
                selected = scenario_id
                submitted = True
    if selected not in case_by_id:
        selected = JUDGE_SCENARIOS[0]["scenario_id"]
        st.session_state["judge_scenario_id"] = selected
    return submitted, selected


def _judge_case_card(scenario: dict[str, str], selected: bool) -> str:
    state = " selected" if selected else ""
    return f"""
    <article class="judge-card{state}">
      <span>{escape(scenario["scenario_id"])}</span>
      <h3>{escape(scenario["title"])}</h3>
      <p>{escape(scenario["story"])}</p>
      <div class="judge-facts">
        <div><strong>Documento interpretado</strong><em>{escape(scenario["gemma"])}</em></div>
        <div><strong>Regra em foco</strong><em>{escape(scenario["rule"])}</em></div>
      </div>
    </article>
    """


def _render_judge_empty_state() -> None:
    st.markdown(
        """
        <article class="empty-judge">
          <strong>Escolha um caso e clique em Executar caso.</strong>
          <p>A proxima dobra compara o que o FIFO chamaria com o que o Pe-Q.I recomenda, mostra o documento interpretado, a regra aplicada e a decisao humana disponivel.</p>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _render_technical_mode(
    defaults: dict[str, str],
    case_by_id: dict[str, dict[str, Any]],
    scenario_id: str,
    variant: str,
) -> dict[str, Any]:
    with st.expander("Modo tecnico: escolher variante e editar CSV/JSON", expanded=False):
        selected = st.selectbox(
            "Cenario base", list(case_by_id), index=list(case_by_id).index(scenario_id)
        )
        selected_variant = st.radio(
            "Variante",
            ["full", "heuristic", "fifo"],
            index=["full", "heuristic", "fifo"].index(variant),
            horizontal=True,
        )
        selected_defaults = (
            defaults if selected == scenario_id else load_case_defaults(case_by_id[selected])
        )
        inputs = _render_inputs(
            selected_defaults,
            case_by_id[selected],
            selected_variant,
            expanded=True,
            use_expander=False,
        )
    inputs["scenario_id"] = selected
    inputs["variant"] = selected_variant
    return inputs


def _render_inputs(
    defaults: dict[str, str],
    case: dict[str, Any],
    variant: str,
    *,
    expanded: bool,
    use_expander: bool = True,
) -> dict[str, Any]:
    wrapper = (
        st.expander("Editar pacote operacional de entrada", expanded=expanded)
        if use_expander
        else nullcontext()
    )
    with wrapper:
        st.markdown(
            """
            <div class="section-title compact-title">
              <div><h2>Entradas do pátio</h2><p>Fila, ticket, nota, clima e recursos exigidos pelo blueprint.</p></div>
              <span class="chip">editavel</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
        submitted = False
        top_a, top_b = st.columns([1.08, 0.92], gap="large")
        with st.form("yard_inputs", border=False):
            with top_a:
                st.markdown(
                    '<div class="panel-title">1 · Fila de caminhoes</div>', unsafe_allow_html=True
                )
                queue_csv = st.text_area(
                    "queue.csv",
                    value=defaults["queue_csv"],
                    height=180,
                    help="Colunas minimas: truck_id, arrival_ts. Campos opcionais: status, vehicle_type, contract_priority_flag.",
                )
                st.markdown(_queue_preview(queue_csv), unsafe_allow_html=True)

            with top_b:
                st.markdown(
                    '<div class="panel-title">2 · Ticket ou documento</div>', unsafe_allow_html=True
                )
                uploaded_ticket = st.file_uploader(
                    "Ticket PDF, imagem ou TXT",
                    type=["txt", "pdf", "png", "jpg", "jpeg"],
                    help="TXT funciona em modo teste. Com PEQUIFLUX_GEMMA_RUNTIME=ollama, imagens sao enviadas ao leitor local de documento.",
                )
                ticket_text = st.text_area(
                    "Ticket textual para demo local",
                    value=defaults["ticket_text"],
                    height=180,
                )

            mid_a, mid_b, mid_c = st.columns([1, 1, 1], gap="large")
            with mid_a:
                st.markdown(
                    '<div class="panel-title">3 · Nota do operador</div>', unsafe_allow_html=True
                )
                operator_note = st.text_area(
                    "operator_note", value=defaults["operator_note"], height=140
                )
            with mid_b:
                st.markdown('<div class="panel-title">4 · Clima</div>', unsafe_allow_html=True)
                weather_json = st.text_area(
                    "weather_state.json", value=defaults["weather_json"], height=140
                )
            with mid_c:
                st.markdown('<div class="panel-title">5 · Recursos</div>', unsafe_allow_html=True)
                resource_json = st.text_area(
                    "resource_state.json", value=defaults["resource_json"], height=140
                )

            st.markdown(
                f"""
                <div class="run-strip">
                  <div>
                    <strong>Cenario base:</strong> {escape(case["scenario_id"])}
                    <span>Variante: {escape(variant)}</span>
                  </div>
                  <div class="run-note">A execucao grava arquivos temporarios em cache/ui_sessions dentro do container.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            submitted = st.form_submit_button("Executar decisao", type="primary", width="stretch")

    return {
        "submitted": submitted,
        "queue_csv": queue_csv,
        "uploaded_ticket": uploaded_ticket,
        "ticket_text": ticket_text,
        "operator_note": operator_note,
        "weather_json": weather_json,
        "resource_json": resource_json,
    }


def _render_outputs(
    payload: FrontEndPayload,
    request: DecisionRequest,
    case: dict[str, Any],
    fifo_payload: FrontEndPayload | None,
) -> None:
    st.markdown(
        """
        <div class="section-title">
          <div><h2>Decisao recomendada</h2><p>Quebra de FIFO explicada por criterio verificavel, sem parecer favorecimento.</p></div>
          <span class="chip success">pronto para operador</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(judge_comparison_card(payload, request, fifo_payload), unsafe_allow_html=True)
    st.markdown(recommended_decision_card(payload), unsafe_allow_html=True)
    st.markdown(queue_stack_card(payload, request), unsafe_allow_html=True)
    first_left, first_right = st.columns([1, 1], gap="large")
    with first_left:
        st.markdown(why_not_fifo_card(payload), unsafe_allow_html=True)
    with first_right:
        st.markdown(gemma_extraction_card(payload, request), unsafe_allow_html=True)

    second_left, second_right = st.columns([1, 1], gap="large")
    with second_left:
        st.markdown(blocked_constraints_card(payload), unsafe_allow_html=True)
    with second_right:
        render_operator_action(payload)

    with st.expander("Ver evidencias tecnicas e auditoria", expanded=False):
        render_status_bar(payload)
        render_input_evidence(payload, request, case)
        st.markdown(copilot_timeline_card(payload, request), unsafe_allow_html=True)
        render_driver_message(payload)
        left, right = st.columns([1.15, 0.85], gap="large")
        with left:
            render_validation_matrix(payload)
        with right:
            render_gemma_context(payload, request)
            st.markdown(tool_badges_card(payload), unsafe_allow_html=True)
        render_audit(payload)
    with st.expander("Painel avancado: payload JSON completo", expanded=False):
        st.json(payload.model_dump(mode="json"))


def _render_error(error: str) -> None:
    st.markdown(
        f"""
        <article class="error-card">
          <strong>Entrada invalida</strong>
          <p>{escape(error)}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _queue_preview(queue_csv: str) -> str:
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


def _brand_block() -> str:
    return """
    <div class="brand">
      <div class="brand-mark"></div>
      <div>
        <h1>PequiFlux</h1>
        <p>Yard Copilot · I/O Demo</p>
      </div>
    </div>
    """


def _runtime_label() -> str:
    runtime = os.getenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama")
    if runtime == "ollama":
        return f"Ollama · {os.getenv('GEMMA_MODEL', 'gemma4:latest')}"
    return runtime


def _ui_autorun_enabled() -> bool:
    return os.getenv("PEQUIFLUX_UI_AUTORUN", "").strip().lower() in {"1", "true", "yes"}


if __name__ == "__main__":
    main()
