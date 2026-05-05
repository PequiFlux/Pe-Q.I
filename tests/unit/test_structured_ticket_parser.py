from __future__ import annotations

import pytest

from app.domain.errors import PequiFluxError
from app.services.structured_ticket_parser import parse_structured_ticket_text


def test_structured_ticket_parser_rejects_invalid_float_field_formally() -> None:
    text = "\n".join(
        [
            "ticket_id: TCK-001",
            "truck_id: TRK-001",
            "vehicle_type: truck",
            "document_status: clear",
            "load_condition: dry",
            "parse_confidence: high",
        ]
    )

    with pytest.raises(PequiFluxError) as exc_info:
        parse_structured_ticket_text(text)

    assert exc_info.value.code == "INVALID_STRUCTURED_TICKET_FIELD"
    assert "parse_confidence" in exc_info.value.message
