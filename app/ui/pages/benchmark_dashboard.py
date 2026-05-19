from __future__ import annotations

import csv
import json
import os
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
    if "variant_metrics" in metrics_artifact:
        return _sample_dashboard_model(metrics_artifact, summary_rows, artifact_dir)
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
    default_artifact_dir = os.getenv("PEQUIFLUX_BENCHMARK_ARTIFACT_DIR", "bench/reports/sample")
    artifact_dir = Path(
        st.sidebar.text_input(
            copy_text("Artifact directory", "Diretório de artefatos"), default_artifact_dir
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
    if "scope_metrics" in model:
        st.subheader(copy_text("Synthetic benchmark scope", "Escopo do benchmark sintético"))
        columns = st.columns(len(model["scope_metrics"]))
        for column, item in zip(columns, model["scope_metrics"]):
            column.metric(item["metric"], item["value"], help=item.get("help"))

    if "claim_metrics" in model:
        st.subheader(copy_text("Claim check", "Checagem do claim"))
        columns = st.columns(len(model["claim_metrics"]))
        for column, item in zip(columns, model["claim_metrics"]):
            column.metric(item["metric"], item["value"], help=item.get("help"))

    columns = st.columns(len(model["headline_metrics"]))
    for column, item in zip(columns, model["headline_metrics"]):
        column.metric(item["metric"], item["value"])

    st.subheader(copy_text("Variant comparison", "Comparação por variante"))
    st.dataframe(model["baseline_rows"], hide_index=True, width="stretch")

    if "summary_examples" in model:
        st.subheader(
            copy_text("Scenario evidence from summary.csv", "Evidência por cenário do summary.csv")
        )
        st.dataframe(model["summary_examples"], hide_index=True, width="stretch")

    st.subheader(copy_text("Submission gates", "Gates de submissão"))
    if model["failed_gates"]:
        st.dataframe(model["failed_gates"], hide_index=True, width="stretch")
    else:
        st.success(
            copy_text("All submission gates passed.", "Todos os gates de submissão passaram.")
        )

    st.subheader(copy_text("Failure examples", "Exemplos de falha"))
    st.dataframe(model["failure_examples"], hide_index=True, width="stretch")


def _render_language_selector(st: Any) -> None:
    options = ["Português", "English"]
    default_language = os.getenv("PEQUIFLUX_UI_DEFAULT_LANGUAGE", "pt").strip().lower()
    default_label = "English" if default_language in {"en", "english"} else "Português"
    current = st.session_state.get(LANGUAGE_KEY, default_label)
    if current == "pt":
        current = "Português"
    elif current == "en":
        current = "English"
    st.sidebar.radio(
        "Idioma / Language",
        options,
        index=options.index(current),
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


def _sample_dashboard_model(
    metrics_artifact: dict[str, Any],
    summary_rows: list[dict[str, Any]],
    artifact_dir: Path,
) -> dict[str, Any]:
    variant_metrics = metrics_artifact.get("variant_metrics", {})
    variants = list(
        metrics_artifact.get("run_metadata", {}).get("report_variants") or sorted(variant_metrics)
    )
    full = dict(variant_metrics.get("full", {}))
    raw_fifo = dict(variant_metrics.get("raw_fifo", {}))
    runtime = metrics_artifact.get("run_metadata", {}).get("runtime", "unknown")
    return {
        "benchmark_id": artifact_dir.name,
        "runtime": runtime,
        "scenario_count": metrics_artifact.get("scenario_count", 0),
        "scope_metrics": [
            {
                "metric": "scenarios",
                "value": metrics_artifact.get("scenario_count", 0),
                "help": "Frozen public synthetic logistics cases.",
            },
            {"metric": "variants", "value": len(variants), "help": ", ".join(variants)},
            {
                "metric": "comparative rows",
                "value": len(summary_rows),
                "help": "scenario x variant rows from summary.csv",
            },
            {
                "metric": "runtime",
                "value": runtime,
                "help": metrics_artifact.get("run_metadata", {}).get("latency_note", ""),
            },
        ],
        "claim_metrics": [
            {
                "metric": "raw FIFO top-1",
                "value": raw_fifo.get("decision_match_at_1"),
                "help": "Pure FIFO agreement with the expected decision.",
            },
            {
                "metric": "raw FIFO violations",
                "value": raw_fifo.get("constraint_violation_rate"),
                "help": "Hard-constraint violation rate for raw FIFO.",
            },
            {
                "metric": "full top-1",
                "value": full.get("decision_match_at_1"),
                "help": "Full variant agreement with the expected decision.",
            },
            {
                "metric": "full exception F1",
                "value": full.get("exception_f1"),
                "help": "Exception classification macro-F1 for the full variant.",
            },
            {
                "metric": "full ticket accuracy",
                "value": full.get("ticket_field_accuracy"),
                "help": "Ticket field accuracy for the full variant.",
            },
        ],
        "headline_metrics": [
            {"metric": "full audit completeness", "value": full.get("audit_completeness")},
            {"metric": "full violations", "value": full.get("constraint_violation_rate")},
            {"metric": "full tool success", "value": full.get("tool_call_success_rate")},
            {"metric": "full avg tool calls", "value": full.get("avg_tool_call_count")},
        ],
        "baseline_rows": _variant_metrics_rows(variant_metrics, variants),
        "failed_gates": [],
        "failure_examples": [],
        "summary_examples": _summary_examples(summary_rows),
    }


def _variant_metrics_rows(
    variant_metrics: dict[str, dict[str, Any]], variants: list[str]
) -> list[dict[str, Any]]:
    return [
        {
            "variant": variant,
            "decision_match_at_1": _round(_to_float(metrics.get("decision_match_at_1")) or 0.0),
            "constraint_violation_rate": _round(
                _to_float(metrics.get("constraint_violation_rate")) or 0.0
            ),
            "exception_f1": _round(_to_float(metrics.get("exception_f1")) or 0.0),
            "ticket_field_accuracy": _round(_to_float(metrics.get("ticket_field_accuracy")) or 0.0),
            "audit_completeness": _round(_to_float(metrics.get("audit_completeness")) or 0.0),
            "tool_call_success_rate": _round(
                _to_float(metrics.get("tool_call_success_rate")) or 0.0
            ),
        }
        for variant in variants
        if (metrics := variant_metrics.get(variant))
    ]


def _summary_examples(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = {
        ("S02_RAIN_OPEN", "raw_fifo"),
        ("S02_RAIN_OPEN", "full"),
        ("S03_WET_LOAD", "heuristic"),
        ("S03_WET_LOAD", "full"),
        ("S10_FIFO_BREAK_JUSTIFIED", "raw_fifo"),
        ("S10_FIFO_BREAK_JUSTIFIED", "full"),
    }
    columns = [
        "scenario_id",
        "variant",
        "decision_match_at_1",
        "constraint_violation",
        "ticket_field_accuracy",
        "audit_complete",
        "decision_status",
        "recommended_truck",
        "recommended_destination",
        "tool_path",
    ]
    return [
        {column: row.get(column, "") for column in columns}
        for row in rows
        if (row.get("scenario_id"), row.get("variant")) in selected
    ]


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
