from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path

from app.domain.errors import PequiFluxError
from app.domain.models import QueueRow, QueueSnapshot, RawQueueRow


def load_queue_rows(path: str) -> list[RawQueueRow]:
    file_path = Path(path)
    if not file_path.exists():
        raise PequiFluxError("QUEUE_NOT_FOUND", f"Queue CSV not found: {path}")

    with file_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {"truck_id", "arrival_ts"}
        if not required.issubset(reader.fieldnames or set()):
            missing = sorted(required.difference(reader.fieldnames or set()))
            raise PequiFluxError(
                "MISSING_REQUIRED_COLUMN",
                f"Queue CSV is missing required columns: {', '.join(missing)}",
            )

        rows: list[RawQueueRow] = []
        for raw in reader:
            if not raw.get("truck_id"):
                raise PequiFluxError("EMPTY_TRUCK_ID", "Queue row has an empty truck_id.")
            rows.append(
                RawQueueRow(
                    truck_id=raw["truck_id"].strip(),
                    arrival_ts=datetime.fromisoformat(raw["arrival_ts"]),
                    status=(raw.get("status") or "waiting").strip(),
                    vehicle_type=(raw.get("vehicle_type") or "unknown").strip(),
                    contract_priority_flag=str(raw.get("contract_priority_flag", "false")).lower()
                    == "true",
                )
            )
    return rows


def normalize_queue_snapshot(
    *,
    request_id: str,
    rows: list[RawQueueRow],
    reference_time: datetime | None = None,
) -> QueueSnapshot:
    if not rows:
        raise PequiFluxError("EMPTY_QUEUE", "Queue snapshot cannot be empty.")

    seen: set[str] = set()
    normalized: list[QueueRow] = []
    reference = reference_time or datetime.now(timezone.utc)

    for raw in sorted(rows, key=lambda row: (row.arrival_ts, row.truck_id)):
        if raw.truck_id in seen:
            raise PequiFluxError("DUPLICATE_TRUCK_ID", f"Duplicated truck_id: {raw.truck_id}")
        seen.add(raw.truck_id)
        wait_minutes = max(int((reference - raw.arrival_ts).total_seconds() // 60), 0)
        normalized.append(
            QueueRow(
                **raw.model_dump(),
                queue_position=len(normalized) + 1,
                wait_minutes=wait_minutes,
            )
        )

    return QueueSnapshot(request_id=request_id, rows=normalized, snapshot_at=reference)

