from __future__ import annotations

import csv
import html
import json
import os
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import streamlit as st
from pydantic import ValidationError

from app.domain.errors import PequiFluxError
from app.domain.models import DecisionRequest, FrontEndPayload
from app.gemma.runtime_factory import build_gemma_adapter
from app.orchestration.orchestrator import DecisionOrchestrator
from app.services.operator_governance import finalize_operator_decision
from app.storage.sqlite_store import SQLiteStore


MANIFEST_PATH = Path("scenarios/manifest.json")
UI_WORK_DIR = Path("cache/ui_sessions")
BENCHMARK_REPORTS_DIR = Path("bench/reports")
BENCHMARK_STRIP_FALLBACK = {
    "full": "10/10 cenarios | 0% violacoes de regra",
    "fifo": "3 cenarios fora do alvo | ex.: S03_WET_LOAD",
    "heuristic": "sem leitura Gemma multimodal | 100% no texto estruturado",
    "source": "Scenario pack sintetico · snapshot 20260503T143757Z",
}
CONTENT_TYPES = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
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
        "story": "A fila favorece um destino seco, mas o ticket e a nota indicam carga umida.",
        "gemma": "Leitura extrai carga umida, placa e necessidade de conferencia.",
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
    _inject_styles()

    manifest = _load_manifest()
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
              <p>{_escape(_runtime_label())}</p>
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
    defaults = _load_case_defaults(case)

    inputs = _render_technical_mode(defaults, case_by_id, scenario_id, variant)
    if inputs["scenario_id"] != scenario_id or inputs["variant"] != variant:
        scenario_id = inputs["scenario_id"]
        variant = inputs["variant"]
        case = case_by_id[scenario_id]
        defaults = _load_case_defaults(case)

    if judge_submitted:
        request = _judge_request(case)
        payload = _run_payload(request)
        fifo_request = request.model_copy(update={"variant": "fifo"})
        fifo_payload = _run_payload(fifo_request)
        st.session_state["last_payload"] = payload
        st.session_state["last_request"] = request
        st.session_state["last_fifo_payload"] = fifo_payload
    elif inputs["submitted"]:
        payload, request, error = _execute_from_inputs(inputs, scenario_id, variant)
        if error:
            _render_error(error)
            return
        assert payload is not None and request is not None
        fifo_request = request.model_copy(update={"variant": "fifo"})
        fifo_payload = _run_payload(fifo_request)
        st.session_state["last_payload"] = payload
        st.session_state["last_request"] = request
        st.session_state["last_fifo_payload"] = fifo_payload

    payload = st.session_state.get("last_payload")
    request = st.session_state.get("last_request")
    fifo_payload = st.session_state.get("last_fifo_payload")
    if payload is None or request is None:
        _render_judge_empty_state()
        return

    _render_outputs(payload, request, case, fifo_payload)


def _load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def _load_case_defaults(case: dict[str, Any]) -> dict[str, str]:
    files = case["files"]
    return {
        "queue_csv": Path(files["queue"]).read_text(encoding="utf-8"),
        "ticket_text": Path(files["ticket"]).read_text(encoding="utf-8"),
        "operator_note": Path(files["operator_note"]).read_text(encoding="utf-8").strip(),
        "weather_json": Path(files["weather_state"]).read_text(encoding="utf-8"),
        "resource_json": Path(files["resource_state"]).read_text(encoding="utf-8"),
    }


def _judge_request(case: dict[str, Any]) -> DecisionRequest:
    request = DecisionRequest.model_validate(case["request"]).model_copy(update={"variant": "full"})
    if request.scenario_id == "S03_WET_LOAD":
        return request.model_copy(
            update={"operator_note": "Carga umida confirmada; usar moega compativel."}
        )
    return request


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
    summary = _benchmark_summary()
    st.markdown(
        f"""
        <section class="benchmark-strip">
          <div>
            <span>Full</span>
            <strong>{_escape(summary["full"])}</strong>
          </div>
          <div>
            <span>FIFO</span>
            <strong>{_escape(summary["fifo"])}</strong>
          </div>
          <div>
            <span>Heuristico</span>
            <strong>{_escape(summary["heuristic"])}</strong>
          </div>
          <small>{_escape(summary["source"])}</small>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _benchmark_summary() -> dict[str, str]:
    report_dir = _latest_benchmark_report_dir()
    if report_dir is None:
        return BENCHMARK_STRIP_FALLBACK
    try:
        metrics = json.loads((report_dir / "metrics.json").read_text(encoding="utf-8"))
        rows = list(csv.DictReader((report_dir / "summary.csv").read_text(encoding="utf-8").splitlines()))
    except (OSError, json.JSONDecodeError, csv.Error):
        return BENCHMARK_STRIP_FALLBACK
    full = metrics["variant_metrics"]["full"]
    fifo = metrics["variant_metrics"]["fifo"]
    heuristic = metrics["variant_metrics"]["heuristic"]
    fifo_misses = [
        row["scenario_id"]
        for row in rows
        if row.get("variant") == "fifo" and row.get("decision_match_at_1") == "False"
    ]
    first_miss = fifo_misses[0] if fifo_misses else "nenhum"
    return {
        "full": (
            f"{int(full['passed_count'])}/{int(full['scenario_count'])} cenarios | "
            f"{_percent_label(full['constraint_violation_rate'])} violacoes de regra"
        ),
        "fifo": (
            f"{len(fifo_misses)} cenarios fora do alvo"
            f" | ex.: {first_miss}"
        ),
        "heuristic": (
            "sem leitura Gemma multimodal"
            f" | {_percent_label(heuristic['ticket_field_accuracy'])} no texto estruturado"
        ),
        "source": f"Scenario pack sintetico · {report_dir.name}",
    }


def _latest_benchmark_report_dir() -> Path | None:
    if not BENCHMARK_REPORTS_DIR.exists():
        return None
    candidates = [
        path
        for path in BENCHMARK_REPORTS_DIR.iterdir()
        if path.is_dir() and (path / "metrics.json").exists() and (path / "summary.csv").exists()
    ]
    return sorted(candidates)[-1] if candidates else None


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
      <span>{_escape(scenario["scenario_id"])}</span>
      <h3>{_escape(scenario["title"])}</h3>
      <p>{_escape(scenario["story"])}</p>
      <div class="judge-facts">
        <div><strong>Documento interpretado</strong><em>{_escape(scenario["gemma"])}</em></div>
        <div><strong>Regra em foco</strong><em>{_escape(scenario["rule"])}</em></div>
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
        selected = st.selectbox("Cenario base", list(case_by_id), index=list(case_by_id).index(scenario_id))
        selected_variant = st.radio("Variante", ["full", "heuristic", "fifo"], index=["full", "heuristic", "fifo"].index(variant), horizontal=True)
        selected_defaults = defaults if selected == scenario_id else _load_case_defaults(case_by_id[selected])
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
                st.markdown('<div class="panel-title">1 · Fila de caminhoes</div>', unsafe_allow_html=True)
                queue_csv = st.text_area(
                    "queue.csv",
                    value=defaults["queue_csv"],
                    height=180,
                    help="Colunas minimas: truck_id, arrival_ts. Campos opcionais: status, vehicle_type, contract_priority_flag.",
                )
                st.markdown(_queue_preview(queue_csv), unsafe_allow_html=True)

            with top_b:
                st.markdown('<div class="panel-title">2 · Ticket ou documento</div>', unsafe_allow_html=True)
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
                st.markdown('<div class="panel-title">3 · Nota do operador</div>', unsafe_allow_html=True)
                operator_note = st.text_area("operator_note", value=defaults["operator_note"], height=140)
            with mid_b:
                st.markdown('<div class="panel-title">4 · Clima</div>', unsafe_allow_html=True)
                weather_json = st.text_area("weather_state.json", value=defaults["weather_json"], height=140)
            with mid_c:
                st.markdown('<div class="panel-title">5 · Recursos</div>', unsafe_allow_html=True)
                resource_json = st.text_area("resource_state.json", value=defaults["resource_json"], height=140)

            st.markdown(
                f"""
                <div class="run-strip">
                  <div>
                    <strong>Cenario base:</strong> {_escape(case["scenario_id"])}
                    <span>Variante: {_escape(variant)}</span>
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


def _execute_from_inputs(
    inputs: dict[str, Any],
    scenario_id: str,
    variant: str,
) -> tuple[FrontEndPayload | None, DecisionRequest | None, str | None]:
    request_id = f"REQ-UI-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    run_dir = UI_WORK_DIR / request_id
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        queue_path = run_dir / "queue.csv"
        weather_path = run_dir / "weather_state.json"
        resource_path = run_dir / "resource_state.json"

        queue_path.write_text(inputs["queue_csv"], encoding="utf-8")
        weather_payload = json.loads(inputs["weather_json"])
        resource_payload = json.loads(inputs["resource_json"])
        weather_path.write_text(json.dumps(weather_payload, indent=2), encoding="utf-8")
        resource_path.write_text(json.dumps(resource_payload, indent=2), encoding="utf-8")

        uploaded = inputs["uploaded_ticket"]
        if uploaded is not None:
            suffix = Path(uploaded.name).suffix.lower()
            content_type = CONTENT_TYPES.get(suffix)
            if content_type is None:
                return None, None, f"Tipo de ticket nao suportado: {suffix}"
            ticket_path = run_dir / f"ticket{suffix}"
            ticket_path.write_bytes(uploaded.getvalue())
        else:
            content_type = "text/plain"
            ticket_path = run_dir / "ticket.txt"
            ticket_path.write_text(inputs["ticket_text"], encoding="utf-8")

        request = DecisionRequest.model_validate(
            {
                "request_id": request_id,
                "scenario_id": scenario_id,
                "variant": variant,
                "queue_csv_ref": str(queue_path),
                "ticket_ref": str(ticket_path),
                "ticket_content_type": content_type,
                "operator_note": inputs["operator_note"],
                "weather_state": weather_payload,
                "resource_state": resource_payload,
                "policy_profile_version": "v1-demo",
                "run_mode": "interactive",
                "received_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return _run_payload(request), request, None
    except json.JSONDecodeError as exc:
        return None, None, f"JSON invalido: {exc}"
    except ValidationError as exc:
        return None, None, f"Entrada fora do contrato Pydantic: {exc}"
    except OSError as exc:
        return None, None, f"Falha ao preparar arquivos da execucao: {exc}"


def _run_payload(request: DecisionRequest) -> FrontEndPayload:
    orchestrator = DecisionOrchestrator(gemma_adapter=build_gemma_adapter())
    return orchestrator.run_decision(request)


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

    st.markdown(_queue_stack_card(payload, request), unsafe_allow_html=True)
    st.markdown(_judge_comparison_card(payload, request, fifo_payload), unsafe_allow_html=True)
    st.markdown(_recommended_decision_card(payload), unsafe_allow_html=True)
    first_left, first_right = st.columns([1, 1], gap="large")
    with first_left:
        st.markdown(_why_not_fifo_card(payload), unsafe_allow_html=True)
    with first_right:
        st.markdown(_gemma_extraction_card(payload, request), unsafe_allow_html=True)

    second_left, second_right = st.columns([1, 1], gap="large")
    with second_left:
        st.markdown(_blocked_constraints_card(payload), unsafe_allow_html=True)
    with second_right:
        _render_operator_action(payload)

    with st.expander("Ver evidencias tecnicas e auditoria", expanded=False):
        _render_status_bar(payload)
        _render_input_evidence(payload, request, case)
        st.markdown(_copilot_timeline_card(payload, request), unsafe_allow_html=True)
        _render_driver_message(payload)
        left, right = st.columns([1.15, 0.85], gap="large")
        with left:
            _render_validation_matrix(payload)
        with right:
            _render_gemma_context(payload, request)
            st.markdown(_tool_badges_card(payload), unsafe_allow_html=True)
        _render_audit(payload)
    with st.expander("Painel avancado: payload JSON completo", expanded=False):
        st.json(payload.model_dump(mode="json"))


def _render_operational_overview(
    payload: FrontEndPayload,
    request: DecisionRequest,
    case: dict[str, Any],
) -> None:
    left, right = st.columns([0.92, 1.08], gap="large")
    with left:
        st.markdown(_input_package_card(request, case), unsafe_allow_html=True)
        st.markdown(_ticket_preview_card(request), unsafe_allow_html=True)
    with right:
        st.markdown(_copilot_timeline_card(payload, request), unsafe_allow_html=True)
        st.markdown(_tool_badges_card(payload), unsafe_allow_html=True)


def _render_input_evidence(
    payload: FrontEndPayload,
    request: DecisionRequest,
    case: dict[str, Any],
) -> None:
    left, right = st.columns([0.92, 1.08], gap="large")
    with left:
        st.markdown(_input_package_card(request, case), unsafe_allow_html=True)
    with right:
        st.markdown(_ticket_preview_card(request), unsafe_allow_html=True)


def _render_status_bar(payload: FrontEndPayload) -> None:
    truck = payload.recommended_truck.truck_id if payload.recommended_truck else "-"
    destination = (
        payload.recommended_destination.destination_id if payload.recommended_destination else "-"
    )
    rejected = len(payload.audit_record.rejected_candidates) if payload.audit_record else 0
    latency = sum(payload.latency_ms.values())
    fifo_break = bool(
        payload.recommended_truck and payload.recommended_truck.queue_position_before != 1
    )
    cards = [
        ("Status", _display_status(str(payload.decision_status)), "estado final da previa"),
        ("Caminhao", truck, "proxima chamada"),
        ("Destino", destination, "recurso recomendado"),
        ("FIFO", "quebrado" if fifo_break else "preservado", "justificavel e auditado"),
        ("Rejeicoes", str(rejected), "pares inelegiveis"),
        ("Latencia", f"{latency} ms", "pipeline local"),
    ]
    for column, (label, value, note) in zip(st.columns(6), cards):
        with column:
            st.markdown(_status_card(label, value, note), unsafe_allow_html=True)


def _render_recommendation(payload: FrontEndPayload) -> None:
    st.markdown(_recommended_decision_card(payload), unsafe_allow_html=True)


def _judge_comparison_card(
    payload: FrontEndPayload,
    request: DecisionRequest,
    fifo_payload: FrontEndPayload | None,
) -> str:
    fifo_truck, fifo_destination = _raw_fifo_call(request)
    if fifo_truck == "sem chamada" and fifo_payload and fifo_payload.recommended_truck:
        fifo_truck = fifo_payload.recommended_truck.truck_id
    if fifo_destination == "sem destino" and fifo_payload and fifo_payload.recommended_destination:
        fifo_destination = fifo_payload.recommended_destination.destination_id
    recommended_truck = payload.recommended_truck.truck_id if payload.recommended_truck else "revisao humana"
    recommended_destination = (
        payload.recommended_destination.destination_id
        if payload.recommended_destination
        else "aguardar decisao humana"
    )
    applied_rule = _primary_rule(payload)
    gemma_fields = _gemma_short_summary(payload)
    return f"""
    <section class="judge-comparison">
      <div class="comparison-tile fifo">
        <span>FIFO chamaria</span>
        <strong>{_escape(fifo_truck)}</strong>
        <p>Destino provavel: {_escape(fifo_destination)}</p>
      </div>
      <div class="comparison-arrow">vs</div>
      <div class="comparison-tile peqi">
        <span>Pe-Q.I recomenda</span>
        <strong>{_escape(recommended_truck)}</strong>
        <p>Destino: {_escape(recommended_destination)}</p>
      </div>
      <div class="comparison-proof">
        <div><span>Documento interpretado</span><strong>{_escape(gemma_fields)}</strong></div>
        <div><span>Regra aplicada</span><strong>{_escape(applied_rule)}</strong></div>
        <div><span>Decisao humana</span><strong>{_escape(_operator_actions_label(payload.operator_actions))}</strong></div>
      </div>
    </section>
    """


def _recommended_decision_card(payload: FrontEndPayload) -> str:
    skipped_truck = _first_skipped_truck(payload)
    recommended_truck = payload.recommended_truck.truck_id if payload.recommended_truck else "sem chamada"
    destination = (
        payload.recommended_destination.destination_id
        if payload.recommended_destination
        else "revisao humana"
    )
    reason_items = "".join(
        f"<li>{_escape(_reason_detail_label(item))}</li>" for item in payload.reason_details[:3]
    )
    return f"""
    <section class="decision-story single">
      <div class="story-main">
        <span class="eyebrow dark">1. Decisao recomendada</span>
        <h2>{_escape(recommended_truck)} deve ir para { _escape(destination) }</h2>
        <p>O primeiro da fila nao e chamado automaticamente. A recomendacao preserva legitimidade porque mostra o criterio que sustenta a quebra.</p>
        <ul>{reason_items}</ul>
      </div>
      <div class="story-grid compact">
        {_story_tile("Nao chamar agora", skipped_truck or "nenhum", "Nao e fura-fila: ha evidencia operacional para nao chamar o primeiro.")}
        {_story_tile("Chamar agora", recommended_truck, f"Destino: {destination}", "action")}
        {_story_tile("Critério sustentado", "verificavel", _reason_detail_label(payload.reason_summary), "proof")}
      </div>
    </section>
    """


def _queue_stack_card(payload: FrontEndPayload, request: DecisionRequest) -> str:
    queue_rows = _raw_queue_rows(request)[:5]
    diff_by_truck = {entry.truck_id: entry for entry in payload.queue_diff}
    recommended_id = payload.recommended_truck.truck_id if payload.recommended_truck else None
    first_id = queue_rows[0]["truck_id"] if queue_rows else None
    cards = "".join(
        _queue_stack_item(row, diff_by_truck.get(row["truck_id"]), payload, first_id, recommended_id)
        for row in queue_rows
    )
    return f"""
    <section class="queue-focus">
      <div class="card-head">
        <div><h3>Fila em decisao</h3><p>Os 5 primeiros caminhoes como o operador ve: quem subiu, quem ficou aguardando e por qual restricao.</p></div>
        {_chip("FIFO visivel", "green")}
      </div>
      <div class="queue-stack">{cards}</div>
    </section>
    """


def _queue_stack_item(
    row: dict[str, str],
    diff_entry: Any,
    payload: FrontEndPayload,
    first_id: str | None,
    recommended_id: str | None,
) -> str:
    truck_id = row["truck_id"]
    card_class, label, detail = _queue_stack_state(
        truck_id,
        diff_entry,
        payload,
        first_id,
        recommended_id,
    )
    after = "-" if diff_entry is None or diff_entry.position_after is None else str(diff_entry.position_after)
    destination = row.get("declared_destination") or "sem destino"
    return f"""
    <article class="queue-card {card_class}">
      <div class="queue-rank">#{_escape(row["position"])}</div>
      <div>
        <strong>{_escape(truck_id)}</strong>
        <span>{_escape(row.get("vehicle_type") or "veiculo")} · destino {_escape(destination)}</span>
      </div>
      <div class="queue-state">
        <em>{_escape(label)}</em>
        <small>{_escape(detail)}</small>
      </div>
      <div class="queue-after">pos. {_escape(after)}</div>
    </article>
    """


def _queue_stack_state(
    truck_id: str,
    diff_entry: Any,
    payload: FrontEndPayload,
    first_id: str | None,
    recommended_id: str | None,
) -> tuple[str, str, str]:
    if truck_id == recommended_id:
        before = diff_entry.position_before if diff_entry else "-"
        after = diff_entry.position_after if diff_entry else "chamada"
        return "promoted", "subiu para chamada", f"antes #{before}; agora #{after}"
    if truck_id == first_id and truck_id != recommended_id:
        rules = _truck_failure_rules(payload, truck_id)
        if rules:
            return "blocked", "bloqueado por restricao", ", ".join(rules[:3])
        return "waiting", "mantido aguardando", "sem criterio suficiente para chamada automatica"
    if diff_entry and diff_entry.decision == "skipped":
        rules = _truck_failure_rules(payload, truck_id)
        detail = ", ".join(rules[:3]) if rules else diff_entry.reason
        return "waiting", "mantido aguardando", detail
    return "neutral", "sem mudanca", "ordem preservada ate nova avaliacao"


def _why_not_fifo_card(payload: FrontEndPayload) -> str:
    skipped_truck = _first_skipped_truck(payload)
    if skipped_truck:
        title = f"Por que {skipped_truck} nao foi chamado?"
        body = "Porque a fila pura perdeu legitimidade neste contexto: a decisao precisa respeitar restricoes, risco operacional e criterio publicado."
    else:
        title = "FIFO preservado"
        body = "O primeiro da fila continua compativel com as restricoes avaliadas."
    details = "".join(
        f"<li>{_escape(_reason_detail_label(item))}</li>" for item in payload.reason_details[:3]
    )
    return f"""
    <article class="card narrative-card">
      <div class="card-head">
        <div><h3>2. Por que nao FIFO?</h3><p>{_escape(title)}</p></div>
        {_chip("anti-arbitragem", "green")}
      </div>
      <p>{_escape(body)}</p>
      <ul class="note-list">{details}</ul>
    </article>
    """


def _gemma_extraction_card(payload: FrontEndPayload, request: DecisionRequest) -> str:
    parsed = payload.benchmark_observed.get("parsed_ticket", {})
    fields = [
        ("ticket", parsed.get("ticket_id") or Path(request.ticket_ref).name),
        ("caminhao lido", parsed.get("truck_id") or "nao informado"),
        ("carga", parsed.get("load_condition") or "unknown"),
        ("destino no ticket", ", ".join(parsed.get("destination_constraints") or []) or "nao informado"),
        ("confianca", _confidence_value(payload)),
    ]
    items = "".join(
        f"<div><span>{_escape(label)}</span><strong>{_escape(value)}</strong></div>"
        for label, value in fields
    )
    return f"""
    <article class="card narrative-card">
      <div class="card-head">
        <div><h3>3. Documento interpretado</h3><p>Campos do ticket que entram na decisao, sem expor prompt ou JSON.</p></div>
        {_chip("leitura", "purple")}
      </div>
      <div class="package-grid">{items}</div>
    </article>
    """


def _blocked_constraints_card(payload: FrontEndPayload) -> str:
    failures = _constraint_failure_summary(payload)
    items = "".join(
        f"<li><strong>{_escape(constraint)}</strong><span>{_escape(detail)}</span></li>"
        for constraint, detail in failures[:4]
    )
    rejected = len(payload.audit_record.rejected_candidates) if payload.audit_record else 0
    return f"""
    <article class="card narrative-card">
      <div class="card-head">
        <div><h3>4. Quais restricoes bloquearam alternativas</h3><p>{rejected} pares foram rejeitados antes de qualquer recomendacao.</p></div>
        {_chip("regras duras", "green")}
      </div>
      <ul class="constraint-list">{items}</ul>
    </article>
    """


def _render_validation_matrix(payload: FrontEndPayload) -> None:
    heatmap = _validation_heatmap(payload)
    st.markdown(
        f"""
        <article class="card">
          <div class="card-head">
            <div><h3>Heatmap de validacao</h3><p>Caminhoes nas linhas, destinos nas colunas: verde elegivel, vermelho bloqueado.</p></div>
            {_chip("HC-01..HC-07", "green")}
          </div>
          {heatmap}
        </article>
        """,
        unsafe_allow_html=True,
    )


def _render_gemma_context(payload: FrontEndPayload, request: DecisionRequest) -> None:
    fields = "".join(
        f"<span>{_escape(field)}</span>"
        for field in payload.gemma_visible_summary.parsed_fields
    )
    notes = "".join(f"<li>{_escape(note)}</li>" for note in payload.confidence_notes)
    preview = json.dumps(
        {
            "exception": payload.gemma_visible_summary.exception_label,
            "ticket_content_type": request.ticket_content_type,
            "fields": payload.gemma_visible_summary.parsed_fields,
            "review_notes": payload.gemma_visible_summary.notes,
        },
        indent=2,
        sort_keys=True,
    )
    st.markdown(
        f"""
        <article class="card">
          <div class="card-head">
            <div><h3>Documento interpretado</h3><p>Resultado avancado da leitura estruturada, sem chat nem chain-of-thought.</p></div>
            {_chip("avancado", "purple")}
          </div>
          <div class="field-cloud">{fields}</div>
          <div class="mini-metrics">
            {_mini_metric("Excecao", payload.gemma_visible_summary.exception_label)}
            {_mini_metric("Documento", request.ticket_content_type)}
            {_mini_metric("Confianca", _confidence_value(payload))}
          </div>
          <pre class="json-preview">{_escape(preview)}</pre>
          <ul class="note-list">{notes}</ul>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _render_operator_action(payload: FrontEndPayload) -> None:
    st.markdown('<article class="card streamlit-card narrative-card"><div class="card-head"><div><h3>5. Acao do operador</h3><p>O sistema recomenda; o operador aprova, bloqueia ou justifica override sem burlar restricao dura.</p></div></div>', unsafe_allow_html=True)
    action = st.radio(
        "Acao",
        options=[str(item) for item in payload.operator_actions],
        format_func=_operator_action_label,
        horizontal=True,
    )
    reason = st.text_input("Motivo", value="OP-DEMO-01 revisou a decisao.")
    requested_truck = None
    requested_destination = None
    if action.endswith("override"):
        requested_truck = st.selectbox("Caminhao solicitado", [item.truck_id for item in payload.queue_diff])
        destination_options = sorted(
            {
                entry["destination_id"]
                for entry in (
                    payload.audit_record.hard_constraints_checked if payload.audit_record else []
                )
            }
        )
        requested_destination = st.selectbox("Destino solicitado", destination_options)
    if st.button("Registrar acao", type="primary"):
        try:
            finalized, updated_audit = finalize_operator_decision(
                payload=payload,
                action_type=action,
                reason=reason,
                actor_id="OP-DEMO-01",
                requested_truck_id=requested_truck,
                requested_destination_id=requested_destination,
                sqlite_store=_ui_sqlite_store(),
            )
        except PequiFluxError as exc:
            st.error(exc.message)
        else:
            st.success("Acao humana finalizada e persistida.")
            st.session_state["operator_finalization"] = finalized.model_dump(mode="json")
            st.session_state["operator_audit_update"] = updated_audit.operator_action
    if "operator_finalization" in st.session_state:
        st.json(st.session_state["operator_finalization"])
    st.markdown("</article>", unsafe_allow_html=True)


def _render_audit(payload: FrontEndPayload) -> None:
    steps = [
        ("request", payload.request_id),
        ("scenario", payload.scenario_id),
        ("variant", payload.variant),
        ("rules", ", ".join(payload.audit_record.fired_rules if payload.audit_record else [])),
        ("tags", ", ".join(payload.benchmark_tags)),
    ]
    items = "".join(
        f"<div class=\"audit-step\"><strong>{_escape(label)}</strong><span>{_escape(value)}</span></div>"
        for label, value in steps
    )
    st.markdown(
        f"""
        <article class="card">
          <div class="card-head">
            <div><h3>Trilha auditavel</h3><p>Campos minimos para reconstruir a decisao.</p></div>
            {_chip("XAI", "green")}
          </div>
          <div class="audit-list">{items}</div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _render_driver_message(payload: FrontEndPayload) -> None:
    st.markdown(
        f"""
        <article class="card phone-card">
          <div class="phone">
            <div class="phone-head"><strong>PequiFlux</strong><span>Mensagem ao motorista</span></div>
            <div class="bubble">Seu check-in foi processado.</div>
            <div class="bubble me">{_escape(payload.driver_message.message)}</div>
            <div class="phone-input">Mensagem</div>
          </div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _render_error(error: str) -> None:
    st.markdown(
        f"""
        <article class="error-card">
          <strong>Entrada invalida</strong>
          <p>{_escape(error)}</p>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _ui_sqlite_store() -> SQLiteStore:
    return SQLiteStore(path=os.getenv("PEQUIFLUX_SQLITE_PATH", "var/db/pequiflux_ui.db"))


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


def _input_package_card(request: DecisionRequest, case: dict[str, Any]) -> str:
    resources = request.resource_state
    blocked = sum(1 for resource in resources if resource.status.lower() == "blocked")
    available = sum(1 for resource in resources if resource.status.lower() == "available")
    scenario_title = case.get("title") or request.scenario_id
    package_items = [
        ("cenario", scenario_title),
        ("variante", request.variant),
        ("clima", f"{request.weather_state.precipitation}/{request.weather_state.severity}"),
        ("recursos", f"{len(resources)} totais · {available} livres · {blocked} bloqueados"),
        ("fila", Path(request.queue_csv_ref).name),
        ("ticket", Path(request.ticket_ref).name),
    ]
    items = "".join(
        f"<div><span>{_escape(label)}</span><strong>{_escape(value)}</strong></div>"
        for label, value in package_items
    )
    return f"""
    <article class="card input-package">
      <div class="card-head">
        <div><h3>Pacote operacional</h3><p>Entradas que alimentam Gemma, regras e auditoria.</p></div>
        {_chip("I/O", "green")}
      </div>
      <div class="package-grid">{items}</div>
    </article>
    """


def _ticket_preview_card(request: DecisionRequest) -> str:
    ticket_path = Path(request.ticket_ref)
    preview = _ticket_preview_text(ticket_path, request.ticket_content_type)
    return f"""
    <article class="card ticket-preview">
      <div class="card-head">
        <div><h3>Ticket recebido</h3><p>Documento bruto ao lado do resumo estruturado do Gemma.</p></div>
        {_chip(request.ticket_content_type, "purple")}
      </div>
      <div class="document-tile">
        <div class="document-icon">{_document_icon(request.ticket_content_type)}</div>
        <div>
          <strong>{_escape(ticket_path.name)}</strong>
          <span>{_escape(preview)}</span>
        </div>
      </div>
    </article>
    """


def _ticket_preview_text(ticket_path: Path, content_type: str) -> str:
    if content_type == "text/plain":
        try:
            text = ticket_path.read_text(encoding="utf-8").strip()
        except OSError:
            return "Texto indisponivel no cache da execucao."
        return " ".join(text.split())[:360] or "Ticket textual vazio."
    if content_type == "application/pdf":
        return "PDF encaminhado ao leitor local; a UI nao mostra prompt nem OCR bruto."
    return "Imagem encaminhada ao leitor local; interpretacao multimodal ocorre no container."


def _document_icon(content_type: str) -> str:
    if content_type == "application/pdf":
        return "PDF"
    if content_type.startswith("image/"):
        return "IMG"
    return "TXT"


def _copilot_timeline_card(payload: FrontEndPayload, request: DecisionRequest) -> str:
    steps = [
        (
            "1. Documento interpretado",
            _step_status(payload, "parse_ticket_document"),
            f"Campos: {', '.join(payload.gemma_visible_summary.parsed_fields[:5])}.",
        ),
        (
            "2. Regras conferidas",
            _step_status(payload, "resolve_truth"),
            "Conflitos materiais e necessidade de revisao foram avaliados.",
        ),
        (
            "3. Alternativas bloqueadas",
            "ok" if payload.audit_record and payload.audit_record.hard_constraints_checked else "review",
            _constraints_summary(payload),
        ),
        (
            "4. Fila recalculada",
            _step_status(payload, "rank_candidates"),
            _ranking_summary(payload),
        ),
        (
            "5. Operador decide",
            "ready" if payload.operator_actions else "review",
            f"Acoes disponiveis: {_operator_actions_label(payload.operator_actions)}.",
        ),
    ]
    items = "".join(_timeline_item(*step) for step in steps)
    return f"""
    <article class="card copilot-timeline">
      <div class="card-head">
        <div><h3>Linha do Copilot</h3><p>Leitura guiada do raciocinio operacional, sem chat livre.</p></div>
        {_chip(str(payload.decision_status), "blue")}
      </div>
      <div class="timeline">{items}</div>
    </article>
    """


def _tool_badges_card(payload: FrontEndPayload) -> str:
    badges = [
        ("Documento interpretado", "parse_ticket_document", _tool_status(payload, "parse_ticket_document")),
        ("Regras conferidas", "resolve_truth", _tool_status(payload, "resolve_truth")),
        (
            "Alternativas bloqueadas",
            "validate_hard_constraints",
            _tool_status(payload, "validate_hard_constraints"),
        ),
        ("Fila recalculada", "rank_candidates", _tool_status(payload, "rank_candidates")),
        ("Auditoria gerada", "generate_audit_payload", "ok" if payload.audit_record else "blocked"),
    ]
    items = "".join(
        f"<div class=\"tool-badge {status}\" title=\"{_escape(technical)}\"><strong>{_escape(name)}</strong><span>{_escape(status)}</span></div>"
        for name, technical, status in badges
    )
    return f"""
    <article class="card tools-card">
      <div class="card-head">
        <div><h3>Painel avancado</h3><p>Status das etapas internas permitidas pelo blueprint.</p></div>
        {_chip("auditoria", "green")}
      </div>
      <div class="tool-grid">{items}</div>
    </article>
    """


def _step_status(payload: FrontEndPayload, latency_key: str) -> str:
    if latency_key in payload.latency_ms:
        return "ok"
    if payload.decision_status.endswith("BLOCKED") or str(payload.decision_status).endswith("REVIEW_REQUIRED"):
        return "review"
    return "pending"


def _tool_status(payload: FrontEndPayload, latency_key: str) -> str:
    if latency_key in payload.latency_ms:
        return "ok"
    if payload.audit_record is None:
        return "blocked"
    return "skipped"


def _constraints_summary(payload: FrontEndPayload) -> str:
    if payload.audit_record is None:
        return "Auditoria indisponivel porque o fluxo fechou antes da validacao."
    checked = len(payload.audit_record.hard_constraints_checked)
    rejected = len(payload.audit_record.rejected_candidates)
    return f"{checked} pares avaliados; {rejected} rejeitados por restricao dura."


def _constraint_failure_summary(payload: FrontEndPayload) -> list[tuple[str, str]]:
    if payload.audit_record is None:
        return [("auditoria", "Fluxo fechou antes da matriz de restricoes.")]
    failures: dict[str, str] = {}
    for rejected in payload.audit_record.rejected_candidates:
        for failure in rejected.get("failed_constraints", []):
            failures.setdefault(
                failure.get("constraint_id", "restricao"),
                failure.get("detail", "Par bloqueado por regra operacional."),
            )
    if not failures:
        return [("nenhuma", "Nenhuma alternativa foi bloqueada por restricao dura.")]
    return list(failures.items())


def _raw_fifo_call(request: DecisionRequest) -> tuple[str, str]:
    rows = _raw_queue_rows(request)
    waiting = [
        row
        for row in rows
        if (row.get("status") or "waiting").lower() == "waiting" and row.get("truck_id")
    ]
    if not waiting:
        return "sem chamada", "sem destino"
    first = min(waiting, key=lambda row: row.get("arrival_ts") or "")
    return first["truck_id"], first.get("declared_destination") or "sem destino"


def _raw_queue_rows(request: DecisionRequest) -> list[dict[str, str]]:
    try:
        rows = list(csv.DictReader(Path(request.queue_csv_ref).read_text(encoding="utf-8").splitlines()))
    except (OSError, csv.Error):
        return []
    rows = sorted(rows, key=lambda row: row.get("arrival_ts") or "")
    for position, row in enumerate(rows, start=1):
        row["position"] = str(position)
    return rows


def _truck_failure_rules(payload: FrontEndPayload, truck_id: str) -> list[str]:
    if payload.audit_record is None:
        return []
    rules: list[str] = []
    for rejected in payload.audit_record.rejected_candidates:
        if rejected.get("truck_id") != truck_id:
            continue
        for failure in rejected.get("failed_constraints", []):
            constraint_id = failure.get("constraint_id")
            if constraint_id and constraint_id not in rules:
                rules.append(constraint_id)
    return rules


def _validation_heatmap(payload: FrontEndPayload) -> str:
    if payload.audit_record is None or not payload.audit_record.hard_constraints_checked:
        return '<div class="heatmap-empty">Validacao indisponivel para este estado.</div>'
    checks = payload.audit_record.hard_constraints_checked
    selected_pair = None
    if payload.recommended_truck and payload.recommended_destination:
        selected_pair = (
            payload.recommended_truck.truck_id,
            payload.recommended_destination.destination_id,
        )
    truck_order = {entry.truck_id: entry.position_before for entry in payload.queue_diff}
    trucks = sorted(
        {entry["truck_id"] for entry in checks},
        key=lambda truck: (truck_order.get(truck, 999), truck),
    )
    destinations = sorted({entry["destination_id"] for entry in checks})
    by_pair = {(entry["truck_id"], entry["destination_id"]): entry for entry in checks}
    header = "".join(f"<div class=\"heatmap-head\">{_escape(destination)}</div>" for destination in destinations)
    rows = "".join(
        _heatmap_row(truck, destinations, by_pair, selected_pair)
        for truck in trucks
    )
    return f"""
    <div class="heatmap-wrap">
      <div class="heatmap-grid" style="grid-template-columns: 112px repeat({len(destinations)}, minmax(118px, 1fr));">
        <div class="heatmap-corner">Fila</div>
        {header}
        {rows}
      </div>
    </div>
    """


def _heatmap_row(
    truck: str,
    destinations: list[str],
    by_pair: dict[tuple[str, str], dict[str, Any]],
    selected_pair: tuple[str, str] | None,
) -> str:
    cells = []
    for destination in destinations:
        entry = by_pair.get((truck, destination))
        if entry is None:
            cells.append('<div class="heat-cell empty">-</div>')
            continue
        failures = [
            failure.get("constraint_id", "HC")
            for failure in entry.get("failed_constraints", [])
        ]
        is_selected = selected_pair == (truck, destination)
        if is_selected:
            state = "selected"
            label = "selecionado"
        elif entry.get("eligible"):
            state = "eligible"
            label = "elegivel"
        else:
            state = "blocked"
            label = ", ".join(failures) or "bloqueado"
        cells.append(f'<div class="heat-cell {state}">{_escape(label)}</div>')
    return f"""
    <div class="heatmap-truck">{_escape(truck)}</div>
    {''.join(cells)}
    """


def _primary_rule(payload: FrontEndPayload) -> str:
    failures = _constraint_failure_summary(payload)
    if failures and failures[0][0] != "nenhuma":
        return failures[0][0]
    if payload.audit_record and payload.audit_record.fired_rules:
        return payload.audit_record.fired_rules[0]
    return str(payload.decision_status)


def _gemma_short_summary(payload: FrontEndPayload) -> str:
    parsed = payload.benchmark_observed.get("parsed_ticket", {})
    parts = [
        parsed.get("load_condition"),
        parsed.get("truck_id"),
        _exception_label_short(payload.gemma_visible_summary.exception_label),
    ]
    visible = [str(part) for part in parts if part]
    if visible:
        return ", ".join(visible[:3])
    return ", ".join(payload.gemma_visible_summary.parsed_fields[:3]) or "campos indisponiveis"


def _exception_label_short(label: str) -> str:
    labels = {
        "RAIN_ON_OPEN_DESTINATION": "chuva em moega aberta",
        "WET_LOAD": "carga umida",
        "DOCUMENT_BLOCK": "documento bloqueado",
        "MANUAL_REVIEW_HINT": "revisao humana",
        "NO_EXCEPTION": "sem excecao",
    }
    return labels.get(label, label.lower().replace("_", " "))


def _ranking_summary(payload: FrontEndPayload) -> str:
    if payload.recommended_truck and payload.recommended_destination:
        return (
            f"{payload.recommended_truck.truck_id} -> "
            f"{payload.recommended_destination.destination_id}; "
            f"{len(payload.queue_diff)} itens no diff da fila."
        )
    return "Sem par recomendado; decisao exige bloqueio ou revisao."


def _operator_actions_label(actions: list[Any]) -> str:
    return ", ".join(_operator_action_label(str(action)) for action in actions)


def _operator_action_label(action: str) -> str:
    labels = {
        "approve": "aprovar",
        "block": "bloquear",
        "override": "sobrescrever",
    }
    return labels.get(action, action)


def _reason_detail_label(text: str) -> str:
    translations = {
        "FIFO ordering preserved when possible.": "Ordem de chegada preservada quando possivel.",
        "Long wait time increased ranking priority.": "Tempo de espera elevou a prioridade na fila.",
        "FIFO break justified by Long wait time increased ranking priority.": (
            "Quebra de FIFO justificada por tempo de espera e criterio verificavel."
        ),
    }
    if text in translations:
        return translations[text]
    return text


def _first_skipped_truck(payload: FrontEndPayload) -> str | None:
    skipped = [entry for entry in payload.queue_diff if entry.decision == "skipped"]
    if not skipped:
        return None
    return min(skipped, key=lambda entry: entry.position_before).truck_id


def _story_tile(label: str, value: str, detail: str, kind: str = "muted") -> str:
    return f"""
    <div class="story-tile {kind}">
      <span>{_escape(label)}</span>
      <strong>{_escape(value)}</strong>
      <p>{_escape(detail)}</p>
    </div>
    """


def _timeline_item(label: str, status: str, detail: str) -> str:
    return f"""
    <div class="timeline-item {status}">
      <div class="timeline-dot"></div>
      <div>
        <strong>{_escape(label)}</strong>
        <p>{_escape(detail)}</p>
      </div>
      {_chip(status, _status_color(status))}
    </div>
    """


def _mini_metric(label: str, value: str) -> str:
    return f"<div><span>{_escape(label)}</span><strong>{_escape(value)}</strong></div>"


def _confidence_value(payload: FrontEndPayload) -> str:
    for note in payload.confidence_notes:
        if note.startswith("parse_confidence="):
            return note.split("=", 1)[1]
    return "n/a"


def _percent_label(value: float | int) -> str:
    return f"{round(float(value) * 100):.0f}%"


def _status_color(status: str) -> str:
    if status in {"ok", "ready"}:
        return "green"
    if status in {"blocked", "review"}:
        return "red"
    return "blue"


def _display_status(status: str) -> str:
    return status.replace("_", " ")


def _status_card(label: str, value: str, note: str) -> str:
    return f"""
    <div class="status-card">
      <span>{_escape(label)}</span>
      <strong>{_escape(value)}</strong>
      <p>{_escape(note)}</p>
    </div>
    """


def _chip(text: str, color: str = "") -> str:
    suffix = f" {color}" if color else ""
    return f'<span class="chip{suffix}">{_escape(text)}</span>'


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


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
          :root {
            --green-50: #ecfdf5;
            --green-100: #d8f9e9;
            --green-400: #34d399;
            --green-500: #22c98b;
            --green-700: #087d55;
            --green-800: #075f45;
            --green-900: #063d31;
            --pequi-50: #fff9e6;
            --pequi-400: #f5c542;
            --pequi-700: #8a5a00;
            --red-50: #fff1f2;
            --red-600: #dc2626;
            --blue-50: #eff6ff;
            --blue-700: #1d4ed8;
            --purple-50: #f5f3ff;
            --purple-700: #6d28d9;
            --slate-50: #f8fafc;
            --slate-100: #f1f5f9;
            --slate-200: #e2e8f0;
            --slate-500: #64748b;
            --slate-700: #334155;
            --slate-900: #0f172a;
            --ink: #10231d;
            --muted: #66746f;
            --line: rgba(16, 35, 29, 0.10);
            --shadow: 0 18px 42px rgba(15, 23, 42, 0.10);
          }
          .stApp {
            color: var(--ink);
            background:
              linear-gradient(135deg, #f7fbf5 0%, #f3f8ef 46%, #f8fafc 100%);
          }
          header[data-testid="stHeader"],
          div[data-testid="stToolbar"],
          div[data-testid="stDecoration"] {
            display: none;
          }
          .block-container {
            max-width: 1500px;
            padding-top: 8px;
            padding-bottom: 40px;
          }
          section[data-testid="stSidebar"] {
            background:
              linear-gradient(180deg, rgba(52, 211, 153, 0.13), rgba(4, 120, 87, 0.02)),
              linear-gradient(180deg, var(--green-900), #041f19);
          }
          section[data-testid="stSidebar"] label,
          section[data-testid="stSidebar"] p,
          section[data-testid="stSidebar"] span,
          section[data-testid="stSidebar"] li {
            color: rgba(236, 255, 248, 0.82);
          }
          .brand {
            display: grid;
            grid-template-columns: 48px 1fr;
            gap: 12px;
            align-items: center;
            padding: 8px 2px 18px;
            margin-bottom: 18px;
            border-bottom: 1px solid rgba(255,255,255,0.10);
          }
          .brand-mark {
            width: 48px;
            height: 48px;
            border-radius: 15px;
            background:
              radial-gradient(circle at 70% 25%, var(--pequi-400) 0 16%, transparent 17%),
              linear-gradient(145deg, var(--green-400), var(--green-700));
            box-shadow: 0 18px 36px rgba(52, 211, 153, 0.28);
          }
          .brand h1 {
            margin: 0;
            color: #fff;
            font-size: 20px;
            line-height: 1.05;
          }
          .brand p {
            margin: 4px 0 0;
            color: rgba(236,255,248,0.64);
            font-size: 12px;
          }
          .side-card {
            margin-top: 14px;
            padding: 15px;
            border-radius: 16px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.10);
          }
          .side-card.compact p,
          .side-card li {
            font-size: 12px;
            line-height: 1.45;
          }
          .side-kicker {
            color: rgba(236,255,248,0.56);
            font-size: 11px;
            font-weight: 900;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .hero {
            display: grid;
            grid-template-columns: minmax(0, 1fr) minmax(340px, 0.45fr);
            gap: 14px;
            align-items: center;
            padding: 14px 18px;
            margin-bottom: 10px;
            border-radius: 18px;
            color: #fff;
            background:
              linear-gradient(135deg, #063d31, #0f172a);
            box-shadow: 0 12px 26px rgba(15, 23, 42, 0.10);
          }
          .eyebrow {
            color: rgba(255,255,255,0.66);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.08em;
            text-transform: uppercase;
          }
          .hero h1 {
            margin: 6px 0 0;
            max-width: 760px;
            font-size: 28px;
            line-height: 1.06;
            letter-spacing: 0;
          }
          .hero p {
            margin: 8px 0 0;
            max-width: 860px;
            color: rgba(255,255,255,0.72);
            font-size: 13px;
            line-height: 1.38;
          }
          .hero-proof {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
          }
          .hero-proof div {
            min-height: 62px;
            padding: 10px;
            border-radius: 12px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
          }
          .hero-proof strong {
            display: block;
            color: #fff;
            font-size: 17px;
            line-height: 1.05;
          }
          .hero-proof span {
            display: block;
            margin-top: 6px;
            color: rgba(255,255,255,0.62);
            font-size: 11px;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }
          .section-title,
          .card-head {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 12px;
            margin: 10px 0 10px;
          }
          .benchmark-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr)) auto;
            gap: 10px;
            align-items: stretch;
            margin: 0 0 10px;
            padding: 10px;
            border-radius: 18px;
            background: rgba(255,255,255,0.88);
            border: 1px solid var(--line);
            box-shadow: 0 8px 22px rgba(15,23,42,0.05);
          }
          .benchmark-strip div {
            min-width: 0;
            padding: 11px 12px;
            border-radius: 14px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .benchmark-strip span {
            display: block;
            color: var(--green-800);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .benchmark-strip strong {
            display: block;
            margin-top: 5px;
            color: var(--ink);
            font-size: 14px;
            line-height: 1.3;
            overflow-wrap: anywhere;
          }
          .benchmark-strip small {
            display: grid;
            align-items: center;
            max-width: 170px;
            color: var(--muted);
            font-size: 11px;
            line-height: 1.35;
          }
          .compact-title {
            margin-top: 0;
          }
          div[data-testid="stExpander"] {
            border: 1px solid var(--line);
            border-radius: 16px;
            background: rgba(255,255,255,0.80);
            box-shadow: 0 8px 20px rgba(15,23,42,0.05);
          }
          div[data-testid="stExpander"] summary {
            color: var(--green-800);
            font-weight: 900;
          }
          .section-title h2,
          .card-head h3 {
            margin: 0;
            letter-spacing: 0;
          }
          .section-title h2 {
            font-size: 22px;
          }
          .judge-title {
            margin-top: 4px;
          }
          .judge-card {
            min-height: 276px;
            margin-bottom: 10px;
            padding: 17px;
            border-radius: 18px;
            background: rgba(255,255,255,0.90);
            border: 1px solid var(--line);
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
          }
          .judge-card.selected {
            border-color: rgba(34,201,139,0.42);
            background: linear-gradient(145deg, var(--green-50), #fff);
            box-shadow: 0 14px 30px rgba(7,95,69,0.13);
          }
          .judge-card > span,
          .judge-facts strong,
          .comparison-tile span,
          .comparison-proof span {
            display: block;
            color: var(--muted);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .judge-card h3 {
            margin: 10px 0 8px;
            color: var(--ink);
            font-size: 21px;
            line-height: 1.12;
            letter-spacing: 0;
          }
          .judge-card p {
            margin: 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
          }
          .judge-facts {
            display: grid;
            gap: 8px;
            margin-top: 14px;
          }
          .judge-facts div {
            padding: 10px;
            border-radius: 14px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .judge-facts em {
            display: block;
            margin-top: 5px;
            color: var(--ink);
            font-size: 12px;
            line-height: 1.35;
            font-style: normal;
          }
          .empty-judge {
            margin-top: 10px;
            padding: 18px;
            border-radius: 18px;
            background: linear-gradient(145deg, #fff, var(--pequi-50));
            border: 1px solid rgba(245,197,66,0.38);
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
          }
          .empty-judge strong {
            display: block;
            color: var(--ink);
            font-size: 18px;
          }
          .empty-judge p {
            margin: 6px 0 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
          }
          .card-head h3 {
            font-size: 18px;
          }
          .section-title p,
          .card-head p {
            margin: 5px 0 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.4;
          }
          .panel-title {
            margin: 0 0 8px;
            font-size: 13px;
            color: var(--green-800);
            font-weight: 950;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }
          .input-summary {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 8px;
            margin: -4px 0 12px;
          }
          .input-summary div,
          .status-card,
          .audit-step {
            border-radius: 14px;
            padding: 11px;
            background: rgba(255,255,255,0.76);
            border: 1px solid var(--line);
          }
          .input-summary strong,
          .status-card strong {
            display: block;
            font-size: 22px;
            line-height: 1;
          }
          .input-summary span,
          .status-card span {
            display: block;
            margin-top: 6px;
            color: var(--muted);
            font-size: 11px;
            font-weight: 850;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }
          .run-strip {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            align-items: center;
            margin: 14px 0 10px;
            padding: 12px 14px;
            border-radius: 16px;
            background: rgba(255,255,255,0.76);
            border: 1px solid var(--line);
          }
          .run-strip strong,
          .run-strip span {
            margin-right: 10px;
            font-size: 13px;
          }
          .run-note {
            color: var(--muted);
            font-size: 12px;
          }
          div[data-testid="stButton"] button {
            border-radius: 10px;
            border: 1px solid rgba(34,201,139,0.30);
            background: #fff;
            color: var(--green-800);
            font-weight: 900;
          }
          div[data-testid="stButton"] button[kind="primary"] {
            background: linear-gradient(145deg, var(--green-700), var(--green-900));
            border-color: rgba(34,201,139,0.44);
            color: #fff;
          }
          div[data-testid="stButton"] button:hover {
            border-color: var(--green-700);
            color: var(--green-800);
          }
          div[data-testid="stButton"] button[kind="primary"]:hover {
            color: #fff;
          }
          .status-grid {
            display: grid;
            grid-template-columns: repeat(6, minmax(0, 1fr));
            gap: 10px;
            margin: 10px 0 12px;
          }
          .status-card p {
            margin: 8px 0 0;
            color: var(--muted);
            font-size: 12px;
            line-height: 1.35;
          }
          .decision-story {
            display: grid;
            grid-template-columns: minmax(360px, 0.92fr) minmax(0, 1.08fr);
            gap: 14px;
            align-items: stretch;
            margin: 2px 0 10px;
          }
          .queue-focus {
            margin: 2px 0 10px;
            padding: 14px;
            border-radius: 18px;
            background: rgba(255,255,255,0.88);
            border: 1px solid var(--line);
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
          }
          .queue-stack {
            display: grid;
            gap: 7px;
          }
          .queue-card {
            display: grid;
            grid-template-columns: 58px minmax(0, 1fr) minmax(220px, 0.62fr) 74px;
            gap: 12px;
            align-items: center;
            min-height: 62px;
            padding: 11px 13px;
            border-radius: 16px;
            background: #fff;
            border: 1px solid var(--line);
            box-shadow: 0 8px 18px rgba(15,23,42,0.04);
          }
          .queue-card.promoted {
            border-color: rgba(34,201,139,0.42);
            background: linear-gradient(90deg, var(--green-50), #fff);
            transform: translateX(10px);
          }
          .queue-card.blocked {
            border-color: rgba(220,38,38,0.28);
            background: linear-gradient(90deg, var(--red-50), #fff);
          }
          .queue-card.waiting {
            background: linear-gradient(90deg, var(--slate-50), #fff);
          }
          .queue-rank {
            display: grid;
            place-items: center;
            width: 44px;
            height: 44px;
            border-radius: 14px;
            color: var(--green-800);
            background: var(--green-50);
            border: 1px solid rgba(34,201,139,0.22);
            font-size: 14px;
            font-weight: 950;
          }
          .queue-card.blocked .queue-rank {
            color: var(--red-600);
            background: var(--red-50);
            border-color: rgba(220,38,38,0.20);
          }
          .queue-card strong {
            display: block;
            color: var(--ink);
            font-size: 20px;
            line-height: 1.05;
          }
          .queue-card span,
          .queue-state small,
          .queue-after {
            color: var(--muted);
            font-size: 12px;
            line-height: 1.35;
          }
          .queue-state em {
            display: block;
            color: var(--ink);
            font-size: 12px;
            font-style: normal;
            font-weight: 950;
            letter-spacing: 0.05em;
            text-transform: uppercase;
          }
          .queue-state small {
            display: block;
            margin-top: 4px;
          }
          .queue-after {
            justify-self: end;
            border-radius: 999px;
            padding: 7px 9px;
            background: var(--slate-50);
            border: 1px solid var(--line);
            font-weight: 900;
          }
          .judge-comparison {
            display: grid;
            grid-template-columns: minmax(0, 0.92fr) 54px minmax(0, 0.92fr) minmax(300px, 1fr);
            gap: 10px;
            align-items: stretch;
            margin: 2px 0 10px;
          }
          .comparison-tile,
          .comparison-proof {
            min-width: 0;
            padding: 15px;
            border-radius: 18px;
            border: 1px solid var(--line);
            background: rgba(255,255,255,0.90);
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
          }
          .comparison-tile.fifo {
            background: linear-gradient(145deg, var(--red-50), #fff);
          }
          .comparison-tile.peqi {
            background: linear-gradient(145deg, var(--green-50), #fff);
            border-color: rgba(34,201,139,0.30);
          }
          .comparison-tile strong {
            display: block;
            margin-top: 8px;
            overflow-wrap: anywhere;
            color: var(--ink);
            font-size: 26px;
            line-height: 1.05;
          }
          .comparison-tile p {
            margin: 8px 0 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.35;
          }
          .comparison-arrow {
            display: grid;
            place-items: center;
            border-radius: 18px;
            color: var(--green-800);
            background: #fff;
            border: 1px solid var(--line);
            font-size: 14px;
            font-weight: 950;
            text-transform: uppercase;
          }
          .comparison-proof {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
          }
          .comparison-proof div {
            min-width: 0;
            padding: 10px;
            border-radius: 14px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .comparison-proof strong {
            display: block;
            margin-top: 6px;
            overflow-wrap: anywhere;
            color: var(--ink);
            font-size: 13px;
            line-height: 1.3;
          }
          .decision-story.single {
            grid-template-columns: minmax(0, 0.9fr) minmax(0, 1.1fr);
          }
          .story-main {
            padding: 18px;
            border-radius: 18px;
            color: #fff;
            background: linear-gradient(135deg, #063d31, #0f172a);
            box-shadow: 0 18px 38px rgba(15,23,42,0.16);
          }
          .eyebrow.dark {
            color: rgba(255,255,255,0.68);
          }
          .story-main h2 {
            margin: 10px 0 10px;
            font-size: 30px;
            line-height: 1.04;
            letter-spacing: 0;
          }
          .story-main p,
          .story-main li {
            color: rgba(255,255,255,0.76);
            font-size: 13px;
            line-height: 1.42;
          }
          .story-main ul {
            margin: 10px 0 0;
            padding-left: 18px;
          }
          .story-grid {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
          }
          .story-grid.compact {
            height: 100%;
          }
          .story-tile {
            min-width: 0;
            min-height: 154px;
            padding: 14px;
            border-radius: 18px;
            border: 1px solid var(--line);
            background: rgba(255,255,255,0.90);
            box-shadow: 0 10px 24px rgba(15,23,42,0.06);
          }
          .story-tile.action {
            background: linear-gradient(145deg, var(--green-50), #fff);
            border-color: rgba(34,201,139,0.26);
          }
          .story-tile.proof {
            background: linear-gradient(145deg, var(--pequi-50), #fff);
            border-color: rgba(245,197,66,0.34);
          }
          .story-tile span {
            display: block;
            color: var(--muted);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .story-tile strong {
            display: block;
            margin-top: 12px;
            overflow-wrap: anywhere;
            color: var(--ink);
            font-size: 25px;
            line-height: 1.05;
          }
          .story-tile p {
            margin: 10px 0 0;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
          }
          .narrative-card {
            min-height: 0;
          }
          .constraint-list {
            display: grid;
            gap: 10px;
            margin: 0;
            padding: 0;
            list-style: none;
          }
          .constraint-list li {
            padding: 12px;
            border-radius: 14px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .constraint-list strong,
          .constraint-list span {
            display: block;
          }
          .constraint-list strong {
            color: var(--green-800);
            font-size: 12px;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .constraint-list span {
            margin-top: 5px;
            color: var(--muted);
            font-size: 13px;
            line-height: 1.4;
          }
          .input-package,
          .ticket-preview,
          .copilot-timeline,
          .tools-card {
            min-height: 0;
          }
          .package-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
          }
          .package-grid div,
          .mini-metrics div,
          .tool-badge {
            min-width: 0;
            border-radius: 14px;
            padding: 11px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .package-grid span,
          .mini-metrics span,
          .tool-badge span {
            display: block;
            margin-bottom: 6px;
            color: var(--muted);
            font-size: 10px;
            font-weight: 950;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .package-grid strong,
          .mini-metrics strong,
          .tool-badge strong {
            display: block;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            color: var(--ink);
            font-size: 13px;
          }
          .document-tile {
            display: grid;
            grid-template-columns: 74px minmax(0, 1fr);
            gap: 12px;
            align-items: center;
            padding: 12px;
            border-radius: 18px;
            background:
              linear-gradient(135deg, rgba(236,253,245,0.88), rgba(255,255,255,0.95));
            border: 1px solid var(--line);
          }
          .document-icon {
            display: grid;
            place-items: center;
            width: 74px;
            height: 88px;
            border-radius: 12px;
            color: #fff;
            background: linear-gradient(145deg, var(--green-800), var(--slate-900));
            font-weight: 950;
            letter-spacing: 0.08em;
            box-shadow: 0 16px 32px rgba(15, 23, 42, 0.16);
          }
          .document-tile strong,
          .document-tile span {
            display: block;
            overflow-wrap: anywhere;
          }
          .document-tile span {
            margin-top: 7px;
            color: var(--muted);
            font-size: 12px;
            line-height: 1.45;
          }
          .timeline {
            position: relative;
            display: grid;
            gap: 8px;
          }
          .timeline-item {
            display: grid;
            grid-template-columns: 18px minmax(0, 1fr) auto;
            gap: 10px;
            align-items: center;
            padding: 11px;
            border-radius: 16px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .timeline-item.ok,
          .timeline-item.ready {
            border-color: rgba(34,201,139,0.28);
            background: linear-gradient(90deg, rgba(236,253,245,0.92), #fff);
          }
          .timeline-item.review,
          .timeline-item.blocked {
            border-color: rgba(239,68,68,0.24);
            background: linear-gradient(90deg, rgba(255,241,242,0.92), #fff);
          }
          .timeline-dot {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            background: var(--green-500);
            box-shadow: 0 0 0 4px rgba(34,201,139,0.12);
          }
          .timeline-item.review .timeline-dot,
          .timeline-item.blocked .timeline-dot {
            background: var(--red-600);
            box-shadow: 0 0 0 4px rgba(220,38,38,0.11);
          }
          .timeline-item.pending .timeline-dot {
            background: var(--blue-700);
            box-shadow: 0 0 0 4px rgba(29,78,216,0.10);
          }
          .timeline-item strong {
            display: block;
            color: var(--ink);
            font-size: 13px;
          }
          .timeline-item p {
            margin: 4px 0 0;
            color: var(--muted);
            font-size: 12px;
            line-height: 1.35;
          }
          .tool-grid,
          .mini-metrics {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 8px;
            margin: 10px 0 12px;
          }
          .tool-grid {
            grid-template-columns: repeat(5, minmax(0, 1fr));
          }
          .tool-badge {
            position: relative;
            padding-top: 13px;
            border-top: 4px solid var(--slate-200);
          }
          .tool-badge.ok {
            border-top-color: var(--green-500);
            background: var(--green-50);
          }
          .tool-badge.blocked {
            border-top-color: var(--red-600);
            background: var(--red-50);
          }
          .tool-badge.skipped {
            border-top-color: var(--slate-500);
            background: var(--slate-50);
          }
          .card {
            margin-bottom: 10px;
            padding: 13px;
            border-radius: 16px;
            background: rgba(255,255,255,0.88);
            border: 1px solid var(--line);
            box-shadow: 0 8px 22px rgba(15,23,42,0.06);
          }
          .primary-output {
            background:
              linear-gradient(135deg, rgba(236,253,245,0.90), rgba(255,255,255,0.96));
          }
          .decision-pair {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin: 10px 0;
          }
          .decision-pair div {
            border-radius: 14px;
            padding: 13px;
            background: linear-gradient(145deg, #063d31, #0f172a);
            color: #fff;
          }
          .decision-pair span {
            display: block;
            color: rgba(255,255,255,0.62);
            font-size: 11px;
            text-transform: uppercase;
            font-weight: 900;
            letter-spacing: 0.07em;
          }
          .decision-pair strong {
            display: block;
            margin-top: 7px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 24px;
          }
          .reason-box {
            border-radius: 14px;
            padding: 12px;
            background: #fff;
            border: 1px solid var(--line);
          }
          .reason-box h4 {
            margin: 0 0 8px;
          }
          .reason-box p,
          .reason-box li,
          .note-list li {
            color: var(--muted);
            font-size: 13px;
            line-height: 1.45;
          }
          .chip {
            display: inline-flex;
            align-items: center;
            max-width: 100%;
            border-radius: 999px;
            padding: 6px 10px;
            background: var(--green-50);
            border: 1px solid rgba(34,201,139,0.22);
            color: var(--green-800);
            font-size: 12px;
            font-weight: 850;
            white-space: nowrap;
          }
          .chip.blue { color: var(--blue-700); background: var(--blue-50); border-color: rgba(59,130,246,0.22); }
          .chip.purple { color: var(--purple-700); background: var(--purple-50); border-color: rgba(139,92,246,0.22); }
          .chip.red { color: var(--red-600); background: var(--red-50); border-color: rgba(239,68,68,0.22); }
          .chip.success,
          .chip.green { color: var(--green-800); background: var(--green-50); }
          .table-wrap {
            overflow-x: auto;
            border-radius: 16px;
            border: 1px solid var(--line);
            background: #fff;
          }
          .heatmap-wrap {
            overflow-x: auto;
            border-radius: 16px;
            border: 1px solid var(--line);
            background: #fff;
          }
          .heatmap-grid {
            display: grid;
            min-width: 760px;
          }
          .heatmap-corner,
          .heatmap-head,
          .heatmap-truck,
          .heat-cell {
            min-height: 54px;
            padding: 10px;
            border-right: 1px solid rgba(16,35,29,0.07);
            border-bottom: 1px solid rgba(16,35,29,0.07);
          }
          .heatmap-corner,
          .heatmap-head {
            display: grid;
            align-items: center;
            background: var(--slate-50);
            color: var(--muted);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.06em;
            text-transform: uppercase;
          }
          .heatmap-truck {
            display: grid;
            align-items: center;
            color: var(--ink);
            background: #fff;
            font-size: 13px;
            font-weight: 950;
          }
          .heat-cell {
            display: grid;
            place-items: center;
            text-align: center;
            font-size: 12px;
            font-weight: 950;
            line-height: 1.25;
            overflow-wrap: anywhere;
          }
          .heat-cell.eligible {
            color: var(--green-800);
            background: var(--green-50);
          }
          .heat-cell.blocked {
            color: var(--red-600);
            background: var(--red-50);
          }
          .heat-cell.selected {
            color: var(--green-900);
            background: linear-gradient(145deg, var(--green-100), var(--pequi-50));
            box-shadow: inset 0 0 0 2px rgba(34,201,139,0.35);
          }
          .heat-cell.empty {
            color: var(--slate-500);
            background: var(--slate-50);
          }
          .heatmap-empty {
            padding: 14px;
            border-radius: 16px;
            color: var(--muted);
            background: var(--slate-50);
            border: 1px solid var(--line);
            font-size: 13px;
          }
          table {
            width: 100%;
            min-width: 720px;
            border-collapse: collapse;
            font-size: 13px;
          }
          th {
            text-align: left;
            padding: 12px;
            color: var(--muted);
            font-size: 11px;
            font-weight: 950;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            border-bottom: 1px solid var(--line);
            background: var(--slate-50);
          }
          td {
            padding: 12px;
            border-bottom: 1px solid rgba(16,35,29,0.07);
            vertical-align: middle;
          }
          tr:last-child td {
            border-bottom: 0;
          }
          tr.selected {
            background: linear-gradient(90deg, rgba(34,201,139,0.12), rgba(245,197,66,0.06));
          }
          .field-cloud {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            margin: 8px 0 12px;
          }
          .field-cloud span {
            border-radius: 999px;
            padding: 6px 9px;
            background: var(--green-50);
            color: var(--green-800);
            font-size: 11px;
            font-weight: 850;
          }
          .json-preview {
            border-radius: 16px;
            padding: 14px;
            background: #09231c;
            color: #c8ffe9;
            font-size: 12px;
            line-height: 1.55;
            overflow: auto;
            white-space: pre-wrap;
          }
          .streamlit-card {
            padding-bottom: 4px;
          }
          .audit-list {
            display: grid;
            gap: 10px;
          }
          .audit-step {
            display: grid;
            grid-template-columns: 120px minmax(0, 1fr);
            gap: 10px;
            align-items: start;
          }
          .audit-step strong {
            color: var(--green-800);
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.06em;
          }
          .audit-step span {
            color: var(--muted);
            font-size: 12px;
            line-height: 1.4;
            overflow-wrap: anywhere;
          }
          .phone-card {
            display: grid;
            place-items: center;
          }
          .phone {
            width: min(320px, 100%);
            border-radius: 30px;
            padding: 12px;
            background: #111827;
            box-shadow: 0 30px 60px rgba(15,23,42,0.24);
          }
          .phone-head {
            padding: 15px;
            border-radius: 22px 22px 8px 8px;
            color: #fff;
            background: linear-gradient(145deg, var(--green-500), var(--green-800));
          }
          .phone-head strong,
          .phone-head span {
            display: block;
          }
          .phone-head span {
            margin-top: 3px;
            color: rgba(255,255,255,0.70);
            font-size: 12px;
          }
          .bubble {
            margin-top: 10px;
            border-radius: 16px;
            padding: 11px 12px;
            background: #fff;
            font-size: 12px;
            line-height: 1.45;
          }
          .bubble.me {
            background: #d9fdd3;
          }
          .phone-input {
            margin-top: 10px;
            border-radius: 999px;
            padding: 10px 13px;
            background: rgba(255,255,255,0.86);
            color: #8a8a8a;
            font-size: 12px;
          }
          .error-card {
            padding: 16px;
            border-radius: 18px;
            background: var(--red-50);
            color: var(--red-600);
            border: 1px solid rgba(239,68,68,0.22);
          }
          @media (max-width: 1280px) {
            .status-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
            .hero { grid-template-columns: 1fr; }
            .decision-story { grid-template-columns: 1fr; }
            .judge-comparison { grid-template-columns: 1fr; }
            .comparison-arrow { min-height: 42px; }
            .tool-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
          }
          @media (max-width: 860px) {
            .status-grid,
            .hero-proof,
            .story-grid,
            .comparison-proof,
            .decision-pair,
            .input-summary,
            .package-grid,
            .tool-grid,
            .mini-metrics {
              grid-template-columns: 1fr;
            }
            .run-strip,
            .benchmark-strip,
            .section-title,
            .card-head {
              flex-direction: column;
            }
            .benchmark-strip {
              grid-template-columns: 1fr;
            }
            .benchmark-strip small {
              max-width: none;
            }
            .timeline-item {
              grid-template-columns: 18px minmax(0, 1fr);
            }
            .queue-card {
              grid-template-columns: 48px minmax(0, 1fr);
            }
            .queue-state,
            .queue-after {
              grid-column: 2;
              justify-self: start;
            }
            .timeline-item .chip {
              grid-column: 2;
              width: fit-content;
            }
            .hero h1 {
              font-size: 28px;
            }
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
