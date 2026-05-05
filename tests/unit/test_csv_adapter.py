from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.adapters.csv_adapter import load_queue_rows, normalize_queue_snapshot
from app.domain.errors import PequiFluxError


def test_load_queue_rows_rejects_invalid_arrival_ts(tmp_path) -> None:
    queue_path = tmp_path / "queue.csv"
    queue_path.write_text(
        "truck_id,arrival_ts,status\nTRK-001,not-a-date,waiting\n",
        encoding="utf-8",
    )

    with pytest.raises(PequiFluxError, match="INVALID_ARRIVAL_TS"):
        load_queue_rows(str(queue_path))


def test_load_queue_rows_rejects_naive_arrival_ts(tmp_path) -> None:
    queue_path = tmp_path / "queue.csv"
    queue_path.write_text(
        "truck_id,arrival_ts,status\nTRK-001,2026-04-04T08:00:00,waiting\n",
        encoding="utf-8",
    )

    with pytest.raises(PequiFluxError, match="NAIVE_TIMESTAMP"):
        load_queue_rows(str(queue_path))


def test_normalize_queue_snapshot_converts_arrival_ts_to_utc(tmp_path) -> None:
    queue_path = tmp_path / "queue.csv"
    queue_path.write_text(
        "truck_id,arrival_ts,status\nTRK-001,2026-04-04T08:00:00-03:00,waiting\n",
        encoding="utf-8",
    )
    rows = load_queue_rows(str(queue_path))

    snapshot = normalize_queue_snapshot(
        request_id="REQ-001",
        rows=rows,
        reference_time=datetime(2026, 4, 4, 12, 0, tzinfo=timezone.utc),
    )

    assert snapshot.rows[0].arrival_ts == datetime(2026, 4, 4, 11, 0, tzinfo=timezone.utc)
    assert snapshot.rows[0].wait_minutes == 60


def test_load_queue_rows_preserves_declared_destination_when_present(tmp_path) -> None:
    queue_path = tmp_path / "queue.csv"
    queue_path.write_text(
        "truck_id,arrival_ts,status,declared_destination\n"
        "TRK-001,2026-04-04T08:00:00+00:00,waiting,DST-COV-01\n",
        encoding="utf-8",
    )

    rows = load_queue_rows(str(queue_path))

    assert rows[0].declared_destination == "DST-COV-01"


def test_normalize_queue_snapshot_rejects_naive_reference_time(tmp_path) -> None:
    queue_path = tmp_path / "queue.csv"
    queue_path.write_text(
        "truck_id,arrival_ts,status\nTRK-001,2026-04-04T08:00:00+00:00,waiting\n",
        encoding="utf-8",
    )
    rows = load_queue_rows(str(queue_path))

    with pytest.raises(PequiFluxError, match="reference_time must include timezone"):
        normalize_queue_snapshot(
            request_id="REQ-001",
            rows=rows,
            reference_time=datetime(2026, 4, 4, 12, 0),
        )
