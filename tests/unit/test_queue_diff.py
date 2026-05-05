from __future__ import annotations

from datetime import datetime, timezone

from app.domain.enums import VehicleType
from app.domain.models import QueueRow, QueueSnapshot
from app.services.decision_builder import _build_queue_diff


def _queue_row(truck_id: str, position: int) -> QueueRow:
    return QueueRow(
        truck_id=truck_id,
        arrival_ts=datetime(2025, 1, 1, 8, 0, tzinfo=timezone.utc),
        status="waiting",
        vehicle_type=VehicleType.UNKNOWN,
        queue_position=position,
        wait_minutes=position * 10,
    )


def _snapshot(rows: list[QueueRow]) -> QueueSnapshot:
    return QueueSnapshot(request_id="REQ-001", rows=rows)


def test_called_truck_leaves_queue_when_fifo_is_preserved() -> None:
    rows = [
        _queue_row("TRK-001", 1),
        _queue_row("TRK-002", 2),
        _queue_row("TRK-003", 3),
    ]
    diff = _build_queue_diff(_snapshot(rows), "TRK-001", "first_eligible")
    by_truck = {entry.truck_id: entry for entry in diff}

    assert by_truck["TRK-001"].decision == "called"
    assert by_truck["TRK-001"].position_before == 1
    assert by_truck["TRK-001"].position_after is None
    assert by_truck["TRK-002"].decision == "shifted"
    assert by_truck["TRK-002"].position_after == 1
    assert by_truck["TRK-003"].decision == "shifted"
    assert by_truck["TRK-003"].position_after == 2


def test_fifo_break_keeps_trucks_ahead_waiting_and_removes_called_truck() -> None:
    rows = [
        _queue_row("TRK-001", 1),
        _queue_row("TRK-002", 2),
        _queue_row("TRK-003", 3),
        _queue_row("TRK-004", 4),
        _queue_row("TRK-005", 5),
    ]
    diff = _build_queue_diff(_snapshot(rows), "TRK-005", "first_eligible_pair")
    by_truck = {entry.truck_id: entry for entry in diff}

    assert by_truck["TRK-005"].decision == "called"
    assert by_truck["TRK-005"].position_after is None
    for truck_id in ("TRK-001", "TRK-002", "TRK-003", "TRK-004"):
        assert by_truck[truck_id].decision == "unchanged"
        assert by_truck[truck_id].position_after == by_truck[truck_id].position_before


def test_blocked_trucks_ahead_are_marked_without_impossible_after_position() -> None:
    rows = [
        _queue_row("TRK-001", 1),
        _queue_row("TRK-002", 2),
        _queue_row("TRK-003", 3),
    ]
    diff = _build_queue_diff(
        _snapshot(rows),
        "TRK-003",
        "constraint_bypass",
        blocked_truck_ids={"TRK-001"},
    )
    by_truck = {entry.truck_id: entry for entry in diff}

    assert by_truck["TRK-001"].decision == "blocked"
    assert by_truck["TRK-001"].position_after == 1
    assert by_truck["TRK-002"].decision == "unchanged"
    assert by_truck["TRK-002"].position_after == 2
    assert by_truck["TRK-003"].decision == "called"
    assert by_truck["TRK-003"].position_after is None


def test_no_candidate_leaves_all_positions_unchanged() -> None:
    rows = [
        _queue_row("TRK-001", 1),
        _queue_row("TRK-002", 2),
    ]
    diff = _build_queue_diff(_snapshot(rows), None, "review required")
    for entry in diff:
        assert entry.position_after == entry.position_before
        assert entry.decision == "unchanged"
        assert entry.reason == "no_dispatch_kept_queue_position"


def test_selected_at_position_2_keeps_first_and_shifts_below() -> None:
    rows = [
        _queue_row("TRK-001", 1),
        _queue_row("TRK-002", 2),
        _queue_row("TRK-003", 3),
        _queue_row("TRK-004", 4),
    ]
    diff = _build_queue_diff(_snapshot(rows), "TRK-002", "constraint_bypass")
    by_truck = {entry.truck_id: entry for entry in diff}

    assert by_truck["TRK-001"].decision == "unchanged"
    assert by_truck["TRK-001"].position_after == 1
    assert by_truck["TRK-002"].decision == "called"
    assert by_truck["TRK-002"].position_after is None
    assert by_truck["TRK-003"].decision == "shifted"
    assert by_truck["TRK-003"].position_after == 2
    assert by_truck["TRK-004"].decision == "shifted"
    assert by_truck["TRK-004"].position_after == 3


def test_single_truck_queue_called() -> None:
    rows = [_queue_row("TRK-001", 1)]
    diff = _build_queue_diff(_snapshot(rows), "TRK-001", "only_truck")
    assert len(diff) == 1
    assert diff[0].decision == "called"
    assert diff[0].position_before == 1
    assert diff[0].position_after is None
