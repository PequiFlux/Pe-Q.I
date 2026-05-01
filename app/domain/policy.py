from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import PolicyProfile

DEFAULT_POLICY = PolicyProfile(
    version="v1-demo",
    min_operational_capacity_pct=20,
    comfort_capacity_pct=50,
    weights={
        "fifo_position": 40,
        "contract_priority": 30,
        "resource_fit": 15,
        "capacity_headroom": 10,
        "wait_sla_pressure": 5,
    },
    tie_breakers=[
        "higher_score",
        "lower_queue_position",
        "earlier_arrival_ts",
        "lexicographic_truck_id",
        "lexicographic_destination_id",
    ],
)


def load_policy_profile(path: str | Path) -> PolicyProfile:
    with Path(path).open("r", encoding="utf-8") as handle:
        return PolicyProfile.model_validate(json.load(handle))


def load_policy_profiles(paths: list[str | Path]) -> dict[str, PolicyProfile]:
    profiles: dict[str, PolicyProfile] = {}
    for path in paths:
        profile = load_policy_profile(path)
        profiles[profile.version] = profile
    return profiles
