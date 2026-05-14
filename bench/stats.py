from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path
from typing import Any


def compare_benchmark_metrics(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    bootstrap_samples: int = 10000,
    random_seed: int = 42,
) -> dict[str, Any]:
    baseline_rows, candidate_rows = _paired_rows(baseline, candidate)
    return {
        "scenario_count": len(candidate_rows),
        "bootstrap_samples": bootstrap_samples,
        "confidence_interval": 0.95,
        "random_seed": random_seed,
        "mcnemar": _mcnemar_exact(baseline_rows, candidate_rows),
        "bootstrap": {
            "ticket_field_accuracy": _bootstrap_delta(
                baseline_rows,
                candidate_rows,
                "ticket_field_accuracy",
                bootstrap_samples,
                random_seed,
            ),
            "exception_macro_f1": _bootstrap_delta(
                baseline_rows,
                candidate_rows,
                "exception_match",
                bootstrap_samples,
                random_seed + 1,
            ),
            "fifo_break_justified_precision": _bootstrap_delta(
                baseline_rows,
                candidate_rows,
                "fifo_break_justified",
                bootstrap_samples,
                random_seed + 2,
            ),
            "latency_ms_total": _bootstrap_delta(
                baseline_rows,
                candidate_rows,
                "latency_ms_total",
                bootstrap_samples,
                random_seed + 3,
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare paired benchmark artifacts.")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--baseline-variant", default="full")
    parser.add_argument("--candidate-variant", default="full")
    parser.add_argument("--bootstrap-samples", type=int, default=10000)
    args = parser.parse_args()

    baseline = load_benchmark_artifact(Path(args.baseline), variant=args.baseline_variant)
    candidate = load_benchmark_artifact(Path(args.candidate), variant=args.candidate_variant)
    report = compare_benchmark_metrics(
        baseline,
        candidate,
        bootstrap_samples=args.bootstrap_samples,
        random_seed=42,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


def load_benchmark_artifact(path: Path, *, variant: str = "full") -> dict[str, Any]:
    artifact = json.loads(path.read_text(encoding="utf-8"))
    if "per_scenario" in artifact or "rows" in artifact:
        return artifact

    sibling_rows = path.parent / "per_scenario.json"
    if sibling_rows.exists():
        rows = json.loads(sibling_rows.read_text(encoding="utf-8"))
        artifact["per_scenario"] = [row for row in rows if row.get("variant") in {variant, None}]
    return artifact


def _paired_rows(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    baseline_rows = _extract_rows(baseline)
    candidate_rows = _extract_rows(candidate)
    baseline_by_id = {str(row["scenario_id"]): row for row in baseline_rows}
    candidate_by_id = {str(row["scenario_id"]): row for row in candidate_rows}
    shared_ids = sorted(baseline_by_id.keys() & candidate_by_id.keys())
    return (
        [baseline_by_id[scenario_id] for scenario_id in shared_ids],
        [candidate_by_id[scenario_id] for scenario_id in shared_ids],
    )


def _extract_rows(artifact: dict[str, Any]) -> list[dict[str, Any]]:
    if "per_scenario" in artifact:
        return list(artifact["per_scenario"])
    if "rows" in artifact:
        return list(artifact["rows"])
    raise ValueError("Benchmark artifact must include per_scenario or rows.")


def _mcnemar_exact(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_only = 0
    baseline_only = 0
    for baseline, candidate in zip(baseline_rows, candidate_rows):
        baseline_correct = bool(baseline.get("decision_match_at_1"))
        candidate_correct = bool(candidate.get("decision_match_at_1"))
        candidate_only += int(candidate_correct and not baseline_correct)
        baseline_only += int(baseline_correct and not candidate_correct)

    discordant = candidate_only + baseline_only
    if discordant == 0:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant, index) * (0.5**discordant)
            for index in range(0, min(candidate_only, baseline_only) + 1)
        )
        p_value = min(1.0, 2 * tail)
    return {
        "candidate_only_correct": candidate_only,
        "baseline_only_correct": baseline_only,
        "discordant_pairs": discordant,
        "p_value": round(p_value, 6),
        "promote": p_value < 0.05,
    }


def _bootstrap_delta(
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    field: str,
    bootstrap_samples: int,
    random_seed: int,
) -> dict[str, Any]:
    pairs = [
        (_numeric(baseline.get(field)), _numeric(candidate.get(field)))
        for baseline, candidate in zip(baseline_rows, candidate_rows)
        if baseline.get(field) is not None and candidate.get(field) is not None
    ]
    if not pairs:
        return {"delta": None, "ci95": [None, None], "promote": False}

    delta = _mean([candidate - baseline for baseline, candidate in pairs])
    rng = random.Random(random_seed)
    sampled_deltas = []
    for _ in range(bootstrap_samples):
        sample = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        sampled_deltas.append(_mean([candidate - baseline for baseline, candidate in sample]))
    sampled_deltas.sort()
    lower = sampled_deltas[int((len(sampled_deltas) - 1) * 0.025)]
    upper = sampled_deltas[int((len(sampled_deltas) - 1) * 0.975)]
    return {
        "delta": round(delta, 6),
        "ci95": [round(lower, 6), round(upper, 6)],
        "promote": lower > 0,
    }


def _numeric(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return float(value)


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


if __name__ == "__main__":
    main()
