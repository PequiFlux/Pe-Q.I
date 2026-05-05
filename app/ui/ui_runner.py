from __future__ import annotations

from app.domain.models import DecisionRequest, FrontEndPayload
from app.gemma.runtime_factory import build_gemma_adapter
from app.orchestration.orchestrator import DecisionOrchestrator


def run_payload(request: DecisionRequest) -> FrontEndPayload:
    orchestrator = DecisionOrchestrator(gemma_adapter=build_gemma_adapter())
    return orchestrator.run_decision(request)


def run_payload_pair(request: DecisionRequest) -> tuple[FrontEndPayload, FrontEndPayload]:
    payload = run_payload(request)
    fifo_payload = run_payload(request.model_copy(update={"variant": "fifo"}))
    return payload, fifo_payload
