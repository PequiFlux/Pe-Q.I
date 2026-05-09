from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.domain.models import DecisionRequest

MANIFEST_PATH = Path("scenarios/manifest.json")
UI_WORK_DIR = Path("cache/ui_sessions")
CONTENT_TYPES = {
    ".txt": "text/plain",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def load_case_defaults(case: dict[str, Any]) -> dict[str, str]:
    files = case["files"]
    ticket_path = Path(files["ticket"])
    return {
        "queue_csv": Path(files["queue"]).read_text(encoding="utf-8"),
        "ticket_text": (
            ticket_path.read_text(encoding="utf-8") if ticket_path.suffix.lower() == ".txt" else ""
        ),
        "operator_note": Path(files["operator_note"]).read_text(encoding="utf-8").strip(),
        "weather_json": Path(files["weather_state"]).read_text(encoding="utf-8"),
        "resource_json": Path(files["resource_state"]).read_text(encoding="utf-8"),
    }


def build_request_from_inputs(
    inputs: dict[str, Any],
    scenario_id: str,
    variant: str,
) -> tuple[DecisionRequest | None, str | None]:
    request_id = f"REQ-UI-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    run_dir = UI_WORK_DIR / request_id
    try:
        validation_error = validate_ui_inputs(inputs)
        if validation_error:
            return None, validation_error
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
                return None, f"Tipo de ticket não suportado: {suffix}"
            ticket_path = run_dir / f"ticket{suffix}"
            ticket_path.write_bytes(uploaded.getvalue())
        else:
            content_type = "text/plain"
            ticket_path = run_dir / "ticket.txt"
            ticket_path.write_text(inputs["ticket_text"], encoding="utf-8")

        return (
            DecisionRequest.model_validate(
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
            ),
            None,
        )
    except json.JSONDecodeError as exc:
        return None, f"JSON invalido: {exc}"
    except ValidationError as exc:
        return None, f"Entrada fora do contrato Pydantic: {exc}"
    except OSError as exc:
        return None, f"Falha ao preparar arquivos da execução: {exc}"


def validate_ui_inputs(inputs: dict[str, Any]) -> str | None:
    queue_csv = str(inputs.get("queue_csv") or "").strip()
    ticket_text = str(inputs.get("ticket_text") or "").strip()
    weather_json = str(inputs.get("weather_json") or "").strip()
    resource_json = str(inputs.get("resource_json") or "").strip()
    uploaded = inputs.get("uploaded_ticket")

    if not queue_csv:
        return "Fila CSV obrigatória."
    if uploaded is None and not ticket_text:
        return "Ticket/documento obrigatório."
    if not weather_json:
        return "Clima obrigatório."
    if not resource_json:
        return "Recursos obrigatórios."
    if uploaded is None:
        return None

    suffix = Path(str(uploaded.name)).suffix.lower()
    content_type = CONTENT_TYPES.get(suffix)
    if content_type is None:
        return f"Tipo de ticket não suportado: {suffix}"
    if runtime_mode() == "text" and content_type != "text/plain":
        return (
            "Modo teste aceita upload apenas TXT. Para PDF/PNG/JPG, use Ollama ou um "
            "cenário versionado com fixture multimodal."
        )
    return None


def runtime_mode() -> str:
    return os.getenv("PEQUIFLUX_GEMMA_RUNTIME", "ollama").strip().lower()
