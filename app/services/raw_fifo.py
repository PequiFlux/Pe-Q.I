from __future__ import annotations

import csv
from pathlib import Path

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
        rows = list(
            csv.DictReader(Path(request.queue_csv_ref).read_text(encoding="utf-8").splitlines())
        )
    except (OSError, csv.Error):
        return []
    rows = sorted(rows, key=lambda row: row.get("arrival_ts") or "")
    for position, row in enumerate(rows, start=1):
        row["position"] = str(position)
    return rows
