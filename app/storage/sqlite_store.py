from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from app.domain.models import AuditRecord, DecisionFinalized, DecisionPreview, OperatorDecision


class SQLiteStore:
    def __init__(self, path: str = "pequiflux.db", migrations_path: str | None = None) -> None:
        self.path = Path(path)
        self.migrations_path = migrations_path or str(Path(__file__).with_name("migrations.sql"))

    def initialize(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.executescript(Path(self.migrations_path).read_text(encoding="utf-8"))

    def save_decision(self, preview: DecisionPreview) -> None:
        with sqlite3.connect(self.path) as connection:
            self._insert_decision_record(connection, preview)
            connection.commit()

    def save_audit_record(self, audit: AuditRecord) -> None:
        with sqlite3.connect(self.path) as connection:
            self._insert_audit_record(connection, audit)
            connection.commit()

    def save_decision_bundle(self, preview: DecisionPreview, audit: AuditRecord) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute("BEGIN")
            try:
                self._insert_decision_record(connection, preview)
                self._insert_audit_record(connection, audit)
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()

    def save_operator_action(self, decision_id: str, action: OperatorDecision) -> None:
        with sqlite3.connect(self.path) as connection:
            self._insert_operator_action(connection, decision_id, action)
            connection.commit()

    def save_decision_finalized(self, finalized: DecisionFinalized) -> None:
        with sqlite3.connect(self.path) as connection:
            self._insert_decision_finalized(connection, finalized)
            connection.commit()

    def save_operator_finalization(
        self,
        *,
        finalized: DecisionFinalized,
        audit: AuditRecord,
    ) -> None:
        with sqlite3.connect(self.path) as connection:
            connection.execute("BEGIN")
            try:
                self._insert_operator_action(
                    connection,
                    finalized.decision_id,
                    finalized.operator_action,
                )
                self._insert_decision_finalized(connection, finalized)
                self._insert_audit_record(connection, audit)
            except Exception:
                connection.rollback()
                raise
            else:
                connection.commit()

    def _insert_decision_record(
        self,
        connection: sqlite3.Connection,
        preview: DecisionPreview,
    ) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO decision_records (
                decision_id, request_id, scenario_id, variant, decision_status,
                recommended_truck_id, recommended_destination_id, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                preview.decision_id,
                preview.request_id,
                preview.scenario_id,
                preview.variant,
                preview.decision_status,
                preview.recommended_truck.truck_id if preview.recommended_truck else None,
                (
                    preview.recommended_destination.destination_id
                    if preview.recommended_destination
                    else None
                ),
                preview.created_at.isoformat(),
            ),
        )

    def _insert_audit_record(self, connection: sqlite3.Connection, audit: AuditRecord) -> None:
        payload = audit.model_dump_json(indent=None)
        connection.execute(
            """
            INSERT OR REPLACE INTO audit_records (
                decision_id, audit_json, created_at
            ) VALUES (?, ?, ?)
            """,
            (audit.decision_id, payload, audit.created_at.isoformat()),
        )

    def _insert_operator_action(
        self,
        connection: sqlite3.Connection,
        decision_id: str,
        action: OperatorDecision,
    ) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO operator_actions (
                action_id, decision_id, action_type, reason, actor_id, created_at, before_json, after_json
            ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?, ?)
            """,
            (
                f"{decision_id}:{action.action_type}",
                decision_id,
                action.action_type,
                action.reason,
                action.actor_id,
                json.dumps({}, separators=(",", ":")),
                json.dumps(action.model_dump(mode="json"), separators=(",", ":")),
            ),
        )

    def _insert_decision_finalized(
        self,
        connection: sqlite3.Connection,
        finalized: DecisionFinalized,
    ) -> None:
        connection.execute(
            """
            INSERT OR REPLACE INTO decision_finalizations (
                decision_id, final_status, operator_action_json, finalized_at
            ) VALUES (?, ?, ?, ?)
            """,
            (
                finalized.decision_id,
                finalized.final_status,
                finalized.operator_action.model_dump_json(),
                finalized.finalized_at.isoformat(),
            ),
        )
        connection.execute(
            """
            UPDATE decision_records
            SET decision_status = ?
            WHERE decision_id = ?
            """,
            (finalized.final_status, finalized.decision_id),
        )
