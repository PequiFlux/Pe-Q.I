from __future__ import annotations

import csv
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from app.ui.components.common import LANGUAGE_KEY, copy_text


HEADLINE_METRICS = (
    "constraint_violation_rate",
    "audit_completeness",
    "decision_match_at_1",
    "ticket_field_accuracy",
    "exception_macro_f1",
    "latency_p95_ms",
)


def dashboard_model_from_artifacts(artifact_dir: Path) -> dict[str, Any]:
    metrics_artifact = json.loads((artifact_dir / "metrics.json").read_text(encoding="utf-8"))
    summary_rows = _read_csv_rows(artifact_dir / "summary.csv")
    error_rows = _read_csv_rows(artifact_dir / "error_analysis.csv")
    metrics = metrics_artifact.get("metrics", {})
    gates = metrics_artifact.get("gates", {})
    return {
        "benchmark_id": metrics_artifact.get("benchmark_id", artifact_dir.name),
        "runtime": metrics_artifact.get("runtime", "unknown"),
        "scenario_count": metrics_artifact.get("scenario_count", 0),
        "submission_ready": bool(gates.get("submission_ready", False)),
        "headline_metrics": [
            {"metric": metric, "value": metrics.get(metric)} for metric in HEADLINE_METRICS
        ],
        "baseline_rows": _variant_summary(summary_rows),
        "failed_gates": list(gates.get("failed_gates", [])),
        "failure_examples": [
            row for row in error_rows if str(row.get("decision_correct", "")).lower() == "false"
        ][:6],
    }


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Pe-Q.I Benchmark", layout="wide")
    _render_language_selector(st)
    st.title(copy_text("Benchmark dashboard", "Dashboard de benchmark"))
    artifact_dir = Path(
        st.sidebar.text_input(
            copy_text("Artifact directory", "Diretório de artefatos"), "artifacts/latest"
        )
    )
    if not (artifact_dir / "metrics.json").exists():
        st.warning(
            copy_text("Benchmark artifacts not found.", "Artefatos de benchmark não encontrados.")
        )
        return

    model = dashboard_model_from_artifacts(artifact_dir)
    st.caption(
        f"{model['benchmark_id']} | runtime={model['runtime']} | "
        f"scenarios={model['scenario_count']}"
    )
    columns = st.columns(len(model["headline_metrics"]))
    for column, item in zip(columns, model["headline_metrics"]):
        column.metric(item["metric"], item["value"])

    st.subheader(copy_text("Baseline vs full", "Baseline vs full"))
    st.dataframe(model["baseline_rows"], hide_index=True, use_container_width=True)

    st.subheader(copy_text("Submission gates", "Gates de submissão"))
    if model["failed_gates"]:
        st.dataframe(model["failed_gates"], hide_index=True, use_container_width=True)
    else:
        st.success(
            copy_text("All submission gates passed.", "Todos os gates de submissão passaram.")
        )

    st.subheader(copy_text("Failure examples", "Exemplos de falha"))
    st.dataframe(model["failure_examples"], hide_index=True, use_container_width=True)


def _render_language_selector(st: Any) -> None:
    options = ["Português", "English"]
    st.sidebar.radio(
        "Idioma / Language",
        options,
        index=options.index(st.session_state.get(LANGUAGE_KEY, "Português")),
        key=LANGUAGE_KEY,
        horizontal=True,
    )
    st.sidebar.caption(
        copy_text(
            "English UI copy is enabled. Metrics, scenario IDs, and CSV fields remain canonical.",
            "Interface em português ativada. Métricas, IDs de cenário e campos CSV permanecem canônicos.",
        )
    )


def _read_csv_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _variant_summary(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        variant = str(row.get("variant", ""))
        if variant:
            buckets[variant].append(row)
    return [
        {
            "variant": variant,
            "decision_match_at_1": _mean_bool(items, "decision_match_at_1"),
            "ticket_field_accuracy": _mean_float(items, "ticket_field_accuracy"),
            "exception_match": _mean_bool(items, "exception_match"),
            "latency_ms_total": _mean_float(items, "latency_ms_total"),
        }
        for variant, items in sorted(buckets.items())
    ]


def _mean_bool(rows: list[dict[str, Any]], key: str) -> float:
    return _round(sum(1.0 for row in rows if _truthy(row.get(key))) / len(rows)) if rows else 0.0


def _mean_float(rows: list[dict[str, Any]], key: str) -> float:
    values = [_to_float(row.get(key)) for row in rows]
    values = [value for value in values if value is not None]
    return _round(sum(values) / len(values)) if values else 0.0


def _truthy(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def _to_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)


def _round(value: float) -> float:
    return round(value, 3)


if __name__ == "__main__":
    main()
