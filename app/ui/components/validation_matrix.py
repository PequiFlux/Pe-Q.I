from __future__ import annotations

from typing import Any

import streamlit as st

from app.domain.models import FrontEndPayload
from app.ui.components.common import chip, copy_text, escape


def render_validation_matrix(payload: FrontEndPayload) -> None:
    heatmap = _validation_heatmap(payload)
    st.markdown(
        f"""
        <article class="card">
          <div class="card-head">
            <div><h3>{escape(copy_text("Validation heatmap", "Heatmap de validação"))}</h3><p>{escape(copy_text("Trucks in rows, destinations in columns: green eligible, red blocked.", "Caminhões nas linhas, destinos nas colunas: verde elegível, vermelho bloqueado."))}</p></div>
            {chip("HC-01..HC-07", "green")}
          </div>
          {heatmap}
        </article>
        """,
        unsafe_allow_html=True,
    )


def _validation_heatmap(payload: FrontEndPayload) -> str:
    if payload.audit_record is None or not payload.audit_record.hard_constraints_checked:
        return f'<div class="heatmap-empty">{escape(copy_text("Validation unavailable for this state.", "Validação indisponível para este estado."))}</div>'
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
    header = "".join(
        f'<div class="heatmap-head">{escape(destination)}</div>' for destination in destinations
    )
    rows = "".join(_heatmap_row(truck, destinations, by_pair, selected_pair) for truck in trucks)
    return f"""
    <div class="heatmap-wrap">
      <div class="heatmap-grid" style="grid-template-columns: 112px repeat({len(destinations)}, minmax(118px, 1fr));">
        <div class="heatmap-corner">{escape(copy_text("Queue", "Fila"))}</div>
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
            failure.get("constraint_id", "HC") for failure in entry.get("failed_constraints", [])
        ]
        is_selected = selected_pair == (truck, destination)
        if is_selected:
            state = "selected"
            label = copy_text("selected", "selecionado")
        elif entry.get("eligible"):
            state = "eligible"
            label = copy_text("eligible", "elegível")
        else:
            state = "blocked"
            label = ", ".join(failures) or copy_text("blocked", "bloqueado")
        cells.append(f'<div class="heat-cell {state}">{escape(label)}</div>')
    return f"""
    <div class="heatmap-truck">{escape(truck)}</div>
    {''.join(cells)}
    """
