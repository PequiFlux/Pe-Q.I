from __future__ import annotations

from app.domain.enums import DecisionStatus
from app.domain.errors import PequiFluxError
from app.domain.models import DriverMessage


def compose_driver_message(
    *,
    request_id: str,
    decision_status: DecisionStatus,
    recommended_truck: str | None,
    recommended_destination: str | None,
    reason_summary: str,
    max_chars: int = 220,
    locale: str = "pt-BR",
) -> DriverMessage:
    if locale != "pt-BR":
        raise PequiFluxError("UNSUPPORTED_LOCALE", f"Unsupported locale: {locale}")

    if (
        decision_status == DecisionStatus.PREVIEW_READY
        and recommended_truck
        and recommended_destination
    ):
        message = f"Chamar {recommended_truck} para {recommended_destination}. {reason_summary}"
        template_id = "dispatch_ptbr_v1"
    elif decision_status == DecisionStatus.BLOCKED:
        message = "Aguardar. Sem rota valida no momento. Procurar operador."
        template_id = "blocked_ptbr_v1"
    else:
        message = "Aguardar conferencia operacional. Caso em revisao."
        template_id = "review_ptbr_v1"

    if len(message) > max_chars:
        raise PequiFluxError("MESSAGE_TOO_LONG", "Driver message exceeds the configured limit.")
    return DriverMessage(message=message, template_id=template_id)
