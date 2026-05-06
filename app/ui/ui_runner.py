from __future__ import annotations

import streamlit as st

from app.domain.models import DecisionRequest, FrontEndPayload
from app.orchestration.factory import build_decision_orchestrator
from app.orchestration.orchestrator import DecisionOrchestrator


@st.cache_resource
def get_orchestrator() -> DecisionOrchestrator:
    return build_decision_orchestrator(enable_storage=True, enable_logging=True)


def run_payload(request: DecisionRequest) -> FrontEndPayload:
    return get_orchestrator().run_decision(request)


def run_payload_pair(request: DecisionRequest) -> tuple[FrontEndPayload, FrontEndPayload]:
    payload = run_payload(request)
    fifo_payload = run_payload(request.model_copy(update={"variant": "fifo"}))
    return payload, fifo_payload
