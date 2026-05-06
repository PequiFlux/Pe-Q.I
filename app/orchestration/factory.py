from __future__ import annotations

import os

from app.gemma.runtime_factory import build_gemma_adapter
from app.orchestration.orchestrator import DecisionOrchestrator
from app.storage.jsonl_logger import JsonlLogger
from app.storage.sqlite_store import SQLiteStore


def build_decision_orchestrator(
    *,
    enable_storage: bool = False,
    enable_logging: bool = False,
) -> DecisionOrchestrator:
    sqlite_store = (
        SQLiteStore(path=os.getenv("PEQUIFLUX_SQLITE_PATH", "var/db/pequiflux.db"))
        if enable_storage
        else None
    )
    jsonl_logger = (
        JsonlLogger(path=os.getenv("PEQUIFLUX_JSONL_LOG_PATH", "logs/events.jsonl"))
        if enable_logging
        else None
    )
    return DecisionOrchestrator(
        gemma_adapter=build_gemma_adapter(),
        sqlite_store=sqlite_store,
        jsonl_logger=jsonl_logger,
    )
