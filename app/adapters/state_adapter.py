from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import ResourceState, WeatherState


def load_weather_state(path: str) -> WeatherState:
    with Path(path).open("r", encoding="utf-8") as handle:
        return WeatherState.model_validate(json.load(handle))


def load_resource_state(path: str) -> list[ResourceState]:
    with Path(path).open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return [ResourceState.model_validate(item) for item in payload]

