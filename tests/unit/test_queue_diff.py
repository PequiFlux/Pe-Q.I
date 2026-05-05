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


def test_selected_truck_moves_to_position_1():
    rows = [
        _queue_row("TRK-001", 1),
        _queue_row("TRK-002", 2),
        _queue_row("TRK-003", 3),
    ]
    diff = _build_queue_diff(_snapshot(rows), "TRK-001", "first_eligible")
    selected = [e for e in diff if e.decision == "recommended"]
    assert len(selected) == 1
    assert selected[0].truck_id == "TRK-001"
    assert selected[0].position_before == 1
    assert selected[0].position_after == 1


def test_fifo_break_skips_above_no_trucks_below():
    rows = [
        _queue_row("TRK-001", 1),
        _queue_row("TRK-002", 2),
        _queue_row("TRK-003", 3),
        _queue_row("TRK-004", 4),
        _queue_row("TRK-005", 5),
    ]
    diff = _build_queue_diff(_snapshot(rows), "TRK-005", "first_eligible_pair")
    by_truck = {e.truck_id: e for e in diff}
    assert by_truck["TRK-005"].decision == "recommended"
    assert by_truck["TRK-005"].position_after == 1
    for tid in ("TRK-001", "TRK-002", "TRK-003", "TRK-004"):
        assert by_truck[tid].decision == "skipped"
        assert by_truck[tid].position_after is None


def test_no_candidate_leaves_all_unchanged():
    rows = [
        _queue_row("TRK-001", 1),
        _queue_row("TRK-002", 2),
    ]
    diff = _build_queue_diff(_snapshot(rows), None, "review required")
    for entry in diff:
        assert entry.position_after == entry.position_before
        assert entry.decision == "shifted"
        assert entry.reason == "displaced_by_recommended_selection"


def test_selected_at_position_2_skips_position_1_shifts_below():
    rows = [
        _queue_row("TRK-001", 1),
        _queue_row("TRK-002", 2),
        _queue_row("TRK-003", 3),
        _queue_row("TRK-004", 4),
    ]
    diff = _build_queue_diff(_snapshot(rows), "TRK-002", "constraint_bypass")
    by_truck = {e.truck_id: e for e in diff}
    assert by_truck["TRK-002"].decision == "recommended"
    assert by_truck["TRK-002"].position_after == 1
    assert by_truck["TRK-001"].decision == "skipped"
    assert by_truck["TRK-001"].position_after is None
    assert by_truck["TRK-003"].decision == "shifted"
    assert by_truck["TRK-003"].position_before == 3
    assert by_truck["TRK-003"].position_after == 2
    assert by_truck["TRK-004"].decision == "shifted"
    assert by_truck["TRK-004"].position_before == 4
    assert by_truck["TRK-004"].position_after == 3


def test_all_positions_are_consistent():
    rows = [
        _queue_row("TRK-001", 1),
        _queue_row("TRK-002", 2),
        _queue_row("TRK-003", 3),
        _queue_row("TRK-004", 4),
        _queue_row("TRK-005", 5),
    ]
    diff = _build_queue_diff(_snapshot(rows), "TRK-003", "justified")
    skipped = [e for e in diff if e.decision == "skipped"]
    shifted = [e for e in diff if e.decision == "shifted"]
    recommended = [e for e in diff if e.decision == "recommended"]
    assert len(skipped) == 2
    assert len(recommended) == 1
    assert len(shifted) == 2
    for s in skipped:
        assert s.position_after is None
    for s in shifted:
        assert s.position_after == s.position_before - 1
    assert recommended[0].position_after == 1


def test_single_truck_queue_selected():
    rows = [_queue_row("TRK-001", 1)]
    diff = _build_queue_diff(_snapshot(rows), "TRK-001", "only_truck")
    assert len(diff) == 1
    assert diff[0].decision == "recommended"
    assert diff[0].position_before == 1
    assert diff[0].position_after == 1
