from __future__ import annotations

import csv
import html
import json
import os
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
CONTENT_TYPES = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def main() -> None:
    st.set_page_config(page_title="PequiFlux Yard Copilot", layout="wide")
    _inject_styles()

    manifest = _load_manifest()
    case_by_id = {case["scenario_id"]: case for case in manifest["cases"]}

    with st.sidebar:
        st.markdown(_brand_block(), unsafe_allow_html=True)
        scenario_id = st.selectbox("Cenario base", list(case_by_id), index=9)
        variant = st.radio("Variante", ["full", "heuristic", "fifo"], horizontal=True)
        st.markdown(
            f"""
            <div class="side-card">
              <div class="side-kicker">Fluxo da demo</div>
              <ol>
                <li>Preencher entradas</li>
                <li>Executar interpretacao</li>
                <li>Validar hard constraints</li>
                <li>Operador decide</li>
              </ol>
            </div>
            <div class="side-card compact">
              <div class="side-kicker">Runtime Gemma</div>
              <p>{_escape(_runtime_label())}</p>
              <p>Sem fallback operacional. Se faltar verdade material, o fluxo fecha em BLOCKED ou REVIEW_REQUIRED.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    case = case_by_id[scenario_id]
    defaults = _load_case_defaults(case)

    _render_intro()
    inputs = _render_inputs(defaults, case, variant, expanded=False)

    if inputs["submitted"]:
        payload, request, error = _execute_from_inputs(inputs, scenario_id, variant)
        if error:
            _render_error(error)
            return
        assert payload is not None and request is not None
        st.session_state["last_payload"] = payload
        st.session_state["last_request"] = request

    payload = st.session_state.get("last_payload")
    request = st.session_state.get("last_request")
    if payload is None or request is None:
        request = DecisionRequest.model_validate(case["request"]).model_copy(update={"variant": variant})
        payload = _run_payload(request)

    _render_outputs(payload, request, case)


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


def _render_intro() -> None:
    st.markdown(
        """
        <section class="hero">
          <div>
            <span class="eyebrow">PequiFlux Yard Copilot · Hackathon</span>
            <h1>Gemma interpreta. Regras decidem. Operador governa.</h1>
            <p>Copiloto local-first para fila de pátio: ticket multimodal, contexto operacional, hard constraints e decisão auditável em uma tela.</p>
          </div>
          <div class="hero-proof">
            <div><strong>Gemma</strong><span>interpreta ticket</span></div>
            <div><strong>HC-01..07</strong><span>bloqueio fechado</span></div>
            <div><strong>Human gate</strong><span>approve/block/override</span></div>
          </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


def _render_inputs(
    defaults: dict[str, str],
    case: dict[str, Any],
    variant: str,
    *,
    expanded: bool,
) -> dict[str, Any]:
    with st.expander("Editar pacote operacional de entrada", expanded=expanded):
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
                    help="TXT funciona em modo teste. Com PEQUIFLUX_GEMMA_RUNTIME=ollama, imagens sao enviadas ao runtime Gemma local.",
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


def _render_outputs(payload: FrontEndPayload, request: DecisionRequest, case: dict[str, Any]) -> None:
    st.markdown(
        """
        <div class="section-title">
          <div><h2>Saida do Copilot</h2><p>Resposta formal: recomendacao, restricoes, mensagem e trilha de auditoria.</p></div>
          <span class="chip success">FrontEndPayload</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_status_bar(payload)
    top_left, top_right = st.columns([1.05, 0.95], gap="large")
    with top_left:
        _render_recommendation(payload)
        _render_operator_action(payload)
    with top_right:
        st.markdown(_copilot_timeline_card(payload, request), unsafe_allow_html=True)
        st.markdown(_tool_badges_card(payload), unsafe_allow_html=True)

    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        _render_validation_matrix(payload)
    with right:
        _render_gemma_context(payload, request)
    with st.expander("Entradas usadas nesta decisão", expanded=False):
        _render_input_evidence(payload, request, case)
    audit_col, message_col = st.columns([1, 1], gap="large")
    with audit_col:
        _render_audit(payload)
    with message_col:
        _render_driver_message(payload)
    with st.expander("Payload JSON completo", expanded=False):
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
    truck = payload.recommended_truck.truck_id if payload.recommended_truck else "SEM CHAMADA"
    destination = (
        payload.recommended_destination.destination_id
        if payload.recommended_destination
        else "REVIEW_REQUIRED"
    )
    details = "".join(f"<li>{_escape(item)}</li>" for item in payload.reason_details[:5])
    st.markdown(
        f"""
        <article class="card primary-output">
          <div class="card-head">
            <div><h3>Recomendacao operacional</h3><p>O operador ve o par recomendado e a razao rastreavel.</p></div>
            {_chip(str(payload.decision_status), "blue")}
          </div>
          <div class="decision-pair">
            <div>
              <span>Caminhao</span>
              <strong>{_escape(truck)}</strong>
            </div>
            <div>
              <span>Destino</span>
              <strong>{_escape(destination)}</strong>
            </div>
          </div>
          <div class="reason-box">
            <h4>Por que agora?</h4>
            <p>{_escape(payload.reason_summary)}</p>
            <ul>{details}</ul>
          </div>
        </article>
        """,
        unsafe_allow_html=True,
    )


def _render_validation_matrix(payload: FrontEndPayload) -> None:
    rows = []
    if payload.audit_record:
        selected_pair = None
        if payload.recommended_truck and payload.recommended_destination:
            selected_pair = (
                payload.recommended_truck.truck_id,
                payload.recommended_destination.destination_id,
            )
        for entry in payload.audit_record.hard_constraints_checked:
            failures = ", ".join(
                failure["constraint_id"] for failure in entry.get("failed_constraints", [])
            )
            is_selected = selected_pair == (entry["truck_id"], entry["destination_id"])
            rows.append(
                {
                    "truck": entry["truck_id"],
                    "destination": entry["destination_id"],
                    "status": "selecionado" if is_selected else ("elegivel" if entry["eligible"] else "bloqueado"),
                    "constraints": failures or "nenhuma",
                }
            )
    table = "".join(_matrix_row(row) for row in rows)
    st.markdown(
        f"""
        <article class="card">
          <div class="card-head">
            <div><h3>Matriz de validacao</h3><p>Nenhum par e recomendado antes das hard constraints.</p></div>
            {_chip("HC-01..HC-07", "green")}
          </div>
          <div class="table-wrap">
            <table>
              <thead><tr><th>Truck</th><th>Destino</th><th>Status</th><th>Restricoes</th></tr></thead>
              <tbody>{table}</tbody>
            </table>
          </div>
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
            <div><h3>Contexto interpretado</h3><p>Resultado visivel do Gemma adapter, sem chat nem chain-of-thought.</p></div>
            {_chip("Gemma", "purple")}
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
    st.markdown('<article class="card streamlit-card"><div class="card-head"><div><h3>Acao humana</h3><p>Approve, block ou override sem bypass de hard constraints.</p></div></div>', unsafe_allow_html=True)
    action = st.radio("Acao", options=[str(item) for item in payload.operator_actions], horizontal=True)
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
        return "PDF encaminhado ao adaptador Gemma local; a UI nao mostra prompt nem OCR bruto."
    return "Imagem encaminhada ao adaptador Gemma local; parsing multimodal ocorre no container."


def _document_icon(content_type: str) -> str:
    if content_type == "application/pdf":
        return "PDF"
    if content_type.startswith("image/"):
        return "IMG"
    return "TXT"


def _copilot_timeline_card(payload: FrontEndPayload, request: DecisionRequest) -> str:
    steps = [
        (
            "1. Intake",
            "ok",
            f"{Path(request.queue_csv_ref).name}, {Path(request.ticket_ref).name}, clima e recursos normalizados.",
        ),
        (
            "2. Gemma interpreted",
            _step_status(payload, "parse_ticket_document"),
            f"Campos: {', '.join(payload.gemma_visible_summary.parsed_fields[:5])}.",
        ),
        (
            "3. Truth resolved",
            _step_status(payload, "resolve_truth"),
            "Conflitos materiais e necessidade de revisao foram avaliados.",
        ),
        (
            "4. Hard constraints",
            "ok" if payload.audit_record and payload.audit_record.hard_constraints_checked else "review",
            _constraints_summary(payload),
        ),
        (
            "5. Ranking",
            _step_status(payload, "rank_candidates"),
            _ranking_summary(payload),
        ),
        (
            "6. Human gate",
            "ready" if payload.operator_actions else "review",
            f"Acoes disponiveis: {', '.join(str(action) for action in payload.operator_actions)}.",
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
        ("parse_ticket_document", _tool_status(payload, "parse_ticket_document")),
        ("resolve_truth", _tool_status(payload, "resolve_truth")),
        ("validate_hard_constraints", _tool_status(payload, "validate_hard_constraints")),
        ("rank_candidates", _tool_status(payload, "rank_candidates")),
        ("generate_audit_payload", "ok" if payload.audit_record else "blocked"),
    ]
    items = "".join(
        f"<div class=\"tool-badge {status}\"><strong>{_escape(name)}</strong><span>{_escape(status)}</span></div>"
        for name, status in badges
    )
    return f"""
    <article class="card tools-card">
      <div class="card-head">
        <div><h3>Tools e contratos</h3><p>Status das etapas permitidas pelo blueprint.</p></div>
        {_chip("schema-bound", "green")}
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


def _ranking_summary(payload: FrontEndPayload) -> str:
    if payload.recommended_truck and payload.recommended_destination:
        return (
            f"{payload.recommended_truck.truck_id} -> "
            f"{payload.recommended_destination.destination_id}; "
            f"{len(payload.queue_diff)} itens no diff da fila."
        )
    return "Sem par recomendado; decisao exige bloqueio ou revisao."


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


def _matrix_row(row: dict[str, str]) -> str:
    row_class = "selected" if row["status"] == "selecionado" else ""
    color = "green" if row["status"] in {"selecionado", "elegivel"} else "red"
    return f"""
    <tr class="{row_class}">
      <td>{_escape(row["truck"])}</td>
      <td>{_escape(row["destination"])}</td>
      <td>{_chip(row["status"], color)}</td>
      <td>{_escape(row["constraints"])}</td>
    </tr>
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
            padding: 16px 18px;
            margin-bottom: 12px;
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
            min-height: 70px;
            padding: 11px;
            border-radius: 12px;
            background: rgba(255,255,255,0.08);
            border: 1px solid rgba(255,255,255,0.12);
          }
          .hero-proof strong {
            display: block;
            color: #fff;
            font-size: 18px;
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
            margin: 14px 0 12px;
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
            margin-bottom: 12px;
            padding: 14px;
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
            .tool-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
          }
          @media (max-width: 860px) {
            .status-grid,
            .hero-proof,
            .decision-pair,
            .input-summary,
            .package-grid,
            .tool-grid,
            .mini-metrics {
              grid-template-columns: 1fr;
            }
            .run-strip,
            .section-title,
            .card-head {
              flex-direction: column;
            }
            .timeline-item {
              grid-template-columns: 18px minmax(0, 1fr);
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
