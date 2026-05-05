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
        for line_number, raw in enumerate(reader, start=2):
            if not raw.get("truck_id"):
                raise PequiFluxError("EMPTY_TRUCK_ID", f"Queue row {line_number} has an empty truck_id.")
            arrival_ts = _parse_arrival_ts(raw.get("arrival_ts"), line_number)
            rows.append(
                RawQueueRow(
                    truck_id=raw["truck_id"].strip(),
                    arrival_ts=arrival_ts,
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
    reference = _ensure_utc(reference_time or datetime.now(timezone.utc), "reference_time")

    for raw in sorted(rows, key=lambda row: (row.arrival_ts, row.truck_id)):
        if raw.truck_id in seen:
            raise PequiFluxError("DUPLICATE_TRUCK_ID", f"Duplicated truck_id: {raw.truck_id}")
        seen.add(raw.truck_id)
        arrival_ts = _ensure_utc(raw.arrival_ts, f"arrival_ts for truck_id={raw.truck_id}")
        wait_minutes = max(int((reference - arrival_ts).total_seconds() // 60), 0)
        row_data = raw.model_dump()
        row_data["arrival_ts"] = arrival_ts
        normalized.append(
            QueueRow(
                **row_data,
                queue_position=len(normalized) + 1,
                wait_minutes=wait_minutes,
            )
        )

    return QueueSnapshot(request_id=request_id, rows=normalized, snapshot_at=reference)


def _parse_arrival_ts(value: str | None, line_number: int) -> datetime:
    if not value or not value.strip():
        raise PequiFluxError("INVALID_ARRIVAL_TS", f"Queue row {line_number} has an empty arrival_ts.")
    raw_value = value.strip()
    try:
        parsed = datetime.fromisoformat(raw_value)
    except ValueError as exc:
        raise PequiFluxError(
            "INVALID_ARRIVAL_TS",
            f"Queue row {line_number} has invalid ISO-8601 arrival_ts: {raw_value}",
        ) from exc
    return _ensure_utc(parsed, f"arrival_ts on queue row {line_number}")


def _ensure_utc(value: datetime, field_name: str) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PequiFluxError(
            "NAIVE_TIMESTAMP",
            f"{field_name} must include timezone information; use an ISO-8601 UTC offset such as +00:00.",
        )
    return value.astimezone(timezone.utc)
