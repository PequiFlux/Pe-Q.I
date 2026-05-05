from __future__ import annotations

from app.adapters.csv_adapter import load_queue_rows
from app.domain.errors import PequiFluxError
from app.domain.models import DecisionRequest


def raw_fifo_call(request: DecisionRequest) -> tuple[str | None, str | None]:
    rows = raw_queue_rows(request)
    waiting = [
        row
        for row in rows
        if (row.get("status") or "waiting").lower() == "waiting" and row.get("truck_id")
    ]
    if not waiting:
        return None, None
    first = min(waiting, key=lambda row: row.get("arrival_ts") or "")
    return first["truck_id"], first.get("declared_destination") or None


def raw_queue_rows(request: DecisionRequest) -> list[dict[str, str]]:
    try:
        rows = sorted(load_queue_rows(request.queue_csv_ref), key=lambda row: row.arrival_ts)
    except PequiFluxError:
        return []
    return [
        {
            "truck_id": row.truck_id,
            "arrival_ts": row.arrival_ts.isoformat(),
            "status": row.status,
            "vehicle_type": str(row.vehicle_type),
            "declared_destination": row.declared_destination or "",
            "position": str(position),
        }
        for position, row in enumerate(rows, start=1)
    ]
