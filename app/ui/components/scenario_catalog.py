from __future__ import annotations

from typing import Any

from app.ui.components.common import escape


def scenario_label(case: dict[str, Any]) -> str:
    description = str(case.get("description") or "").strip()
    if not description:
        return str(case["scenario_id"])
    return f"{case['scenario_id']} · {description}"


def scenario_note(case: dict[str, Any]) -> str:
    ticket_path = str(case.get("files", {}).get("ticket", ""))
    ticket_kind = ticket_path.rsplit(".", 1)[-1].upper() if "." in ticket_path else "N/A"
    return f"""
    <div class="scenario-note">
      <strong>{escape(case["scenario_id"])}</strong>
      <span>{escape(str(case.get("description") or "Sem descrição."))}</span>
      <em>Fixture: {escape(ticket_kind)}</em>
    </div>
    """
