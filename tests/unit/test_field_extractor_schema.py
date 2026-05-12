from __future__ import annotations

from app.domain.models import ParsedTicket
from app.gemma.field_extractor import field_extraction_from_parsed_ticket


def test_field_extractor_emits_evidence_per_parsed_ticket_field() -> None:
    result = field_extraction_from_parsed_ticket(
        ParsedTicket(
            ticket_id="TCK-001",
            truck_id="TRK-001",
            vehicle_type="truck",
            document_status="clear",
            load_condition="dry",
            parse_confidence=0.94,
            evidence_refs=["line: truck_id TRK-001"],
        ),
        source="gemma4:e4b",
    )

    assert result.needs_review is False
    assert result.fields["truck_id"].value == "TRK-001"
    assert result.fields["truck_id"].confidence == 0.94
    assert result.fields["truck_id"].evidence == ["line: truck_id TRK-001"]
    assert result.fields["truck_id"].source == "gemma4:e4b"


def test_field_extractor_routes_low_confidence_critical_fields_to_review() -> None:
    result = field_extraction_from_parsed_ticket(
        ParsedTicket(
            truck_id=None,
            document_status="unknown",
            load_condition="unknown",
            parse_confidence=0.42,
        ),
        source="gemma4:e4b",
    )

    assert result.needs_review is True
    assert "Critical fields" in result.reason
