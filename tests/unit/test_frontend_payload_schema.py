from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import FrontEndPayload


def test_frontend_payload_schema_matches_pydantic_model():
    expected = FrontEndPayload.model_json_schema()
    expected = {"$id": "schemas/FrontEndPayload.schema.json", **expected}

    schema = json.loads(
        Path("scenarios/schemas/FrontEndPayload.schema.json").read_text(encoding="utf-8")
    )

    assert schema == expected
