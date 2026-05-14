from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

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
        "fixture_ticket_path": str(ticket_path),
        "fixture_ticket_content_type": _content_type_for_suffix(ticket_path.suffix.lower()) or "",
    }


def build_request_from_inputs(
    inputs: dict[str, Any],
    scenario_id: str,
    variant: str,
) -> tuple[DecisionRequest | None, str | None]:
    request_id = f"REQ-UI-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S%f')}-{uuid4().hex[:8]}"
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
            content_type = _content_type_for_suffix(suffix)
            if content_type is None:
                return None, f"Tipo de ticket não suportado: {suffix}"
            ticket_path = run_dir / f"ticket{suffix}"
            ticket_path.write_bytes(uploaded.getvalue())
        elif str(inputs.get("ticket_text") or "").strip():
            content_type = "text/plain"
            ticket_path = run_dir / "ticket.txt"
            ticket_path.write_text(inputs["ticket_text"], encoding="utf-8")
        else:
            fixture_ticket_path = Path(str(inputs.get("fixture_ticket_path") or "")).expanduser()
            suffix = fixture_ticket_path.suffix.lower()
            content_type = _content_type_for_suffix(suffix)
            if content_type is None:
                return None, f"Tipo de ticket não suportado: {suffix or '(sem extensão)'}"
            if not fixture_ticket_path.exists():
                return None, f"Fixture do ticket não encontrado: {fixture_ticket_path}"
            ticket_path = run_dir / f"ticket{suffix}"
            shutil.copyfile(fixture_ticket_path, ticket_path)
            expected_ticket_path = fixture_ticket_path.with_name("expected_ticket.json")
            if expected_ticket_path.exists():
                shutil.copyfile(expected_ticket_path, run_dir / "expected_ticket.json")

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
    fixture_ticket_path = str(inputs.get("fixture_ticket_path") or "").strip()
    uploaded = inputs.get("uploaded_ticket")

    if not queue_csv:
        return "Fila CSV obrigatória."
    if uploaded is None and not ticket_text and not fixture_ticket_path:
        return "Ticket/documento obrigatório."
    if not weather_json:
        return "Clima obrigatório."
    if not resource_json:
        return "Recursos obrigatórios."
    if uploaded is None:
        if ticket_text or not fixture_ticket_path:
            return None
        fixture_ticket = Path(fixture_ticket_path).expanduser()
        suffix = fixture_ticket.suffix.lower()
        content_type = _content_type_for_suffix(suffix)
        if content_type is None:
            return f"Tipo de ticket não suportado: {suffix or '(sem extensão)'}"
        if not fixture_ticket.exists():
            return f"Fixture do ticket não encontrado: {fixture_ticket}"
        if runtime_mode() == "text" and content_type != "text/plain":
            expected_ticket = fixture_ticket.with_name("expected_ticket.json")
            if not expected_ticket.exists():
                return (
                    "Fixture multimodal em modo teste exige expected_ticket.json ao lado do "
                    "arquivo do ticket."
                )
        return None

    suffix = Path(str(uploaded.name)).suffix.lower()
    content_type = _content_type_for_suffix(suffix)
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


def _content_type_for_suffix(suffix: str) -> str | None:
    return CONTENT_TYPES.get(suffix)
