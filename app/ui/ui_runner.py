from __future__ import annotations

import streamlit as st

from app.domain.models import DecisionRequest, FrontEndPayload
from app.gemma.runtime_factory import build_gemma_adapter
from app.orchestration.orchestrator import DecisionOrchestrator


@st.cache_resource
def get_orchestrator() -> DecisionOrchestrator:
    return DecisionOrchestrator(gemma_adapter=build_gemma_adapter())


def run_payload(request: DecisionRequest) -> FrontEndPayload:
    return get_orchestrator().run_decision(request)


def run_payload_pair(request: DecisionRequest) -> tuple[FrontEndPayload, FrontEndPayload]:
    payload = run_payload(request)
    fifo_payload = run_payload(request.model_copy(update={"variant": "fifo"}))
    return payload, fifo_payload
