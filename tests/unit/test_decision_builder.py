from __future__ import annotations

from datetime import datetime, timezone

from app.domain.enums import LoadCondition, Severity, VehicleType
from app.domain.models import (
    ConstraintFailure,
    ExceptionAssessment,
    InterpretedContext,
    ParsedTicket,
    ProvenanceRecord,
    QueueRow,
    QueueSnapshot,
    RankedCandidate,
    RankedCandidates,
    TruthResolution,
    ValidationEntry,
    ValidationResult,
)
from app.services.decision_builder import build_decision_preview


def _queue_row(truck_id: str, position: int) -> QueueRow:
    return QueueRow(
        truck_id=truck_id,
        arrival_ts=datetime(2026, 5, 5, 8, 0, tzinfo=timezone.utc),
        status="waiting",
        vehicle_type=VehicleType.TRUCK,
        queue_position=position,
        wait_minutes=position * 10,
    )


def _context() -> InterpretedContext:
    return InterpretedContext(
        parsed_ticket=ParsedTicket(load_condition=LoadCondition.DRY, parse_confidence=0.95),
        exception_assessment=ExceptionAssessment(
            primary_exception="RAIN_ON_OPEN_DESTINATION",
            severity=Severity.MEDIUM,
        ),
        truth_resolution=TruthResolution(authoritative_sources=["ticket"]),
        provenance=[
            ProvenanceRecord(
                field="load_condition",
                source="ticket_document",
                confidence=0.95,
            )
        ],
    )


def test_decision_preview_queue_diff_marks_called_blocked_unchanged_and_shifted() -> None:
    queue_snapshot = QueueSnapshot(
        request_id="REQ-QUEUE",
        rows=[
            _queue_row("TRK-001", 1),
            _queue_row("TRK-002", 2),
            _queue_row("TRK-003", 3),
            _queue_row("TRK-004", 4),
        ],
    )
    validation = ValidationResult(
        validation_matrix=[
            ValidationEntry(
                truck_id="TRK-001",
                destination_id="DST-OPEN-01",
                eligible=False,
                failed_constraints=[
                    ConstraintFailure(
                        constraint_id="HC-01",
                        severity="hard",
                        source="weather",
                        detail="Rain blocked open destination.",
                    )
                ],
            ),
            ValidationEntry(truck_id="TRK-002", destination_id="DST-COV-01", eligible=True),
            ValidationEntry(truck_id="TRK-003", destination_id="DST-COV-01", eligible=True),
            ValidationEntry(truck_id="TRK-004", destination_id="DST-COV-01", eligible=True),
        ],
        policy_profile_version="v1-demo",
    )
    ranking = RankedCandidates(
        candidates=[
            RankedCandidate(
                truck_id="TRK-003",
                destination_id="DST-COV-01",
                score=100,
                queue_position=3,
                arrival_ts=datetime(2026, 5, 5, 8, 0, tzinfo=timezone.utc),
                fifo_break=True,
                reason_details=[
                    "FIFO ordering preserved when possible.",
                    "Long wait time increased ranking priority.",
                ],
            )
        ]
    )

    preview = build_decision_preview(
        interpreted_context=_context(),
        validation=validation,
        ranking=ranking,
        queue_snapshot=queue_snapshot,
        request_id="REQ-QUEUE",
        scenario_id="S-QUEUE",
        variant="full",
    )
    by_truck = {entry.truck_id: entry for entry in preview.queue_diff}

    assert by_truck["TRK-003"].decision == "called"
    assert by_truck["TRK-003"].position_after is None
    assert by_truck["TRK-001"].decision == "blocked"
    assert by_truck["TRK-001"].position_after == 1
    assert by_truck["TRK-002"].decision == "unchanged"
    assert by_truck["TRK-002"].position_after == 2
    assert by_truck["TRK-004"].decision == "shifted"
    assert by_truck["TRK-004"].position_after == 3
