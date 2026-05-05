from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from app.ui.components.common import percent_label
from bench.variants import FIFO_SAFE_VARIANT, OPERATIONAL_FIFO_VARIANT, RAW_FIFO_VARIANT
from bench.variants import report_variant_name

BENCHMARK_STRIP_FALLBACK = {
    "full": "pack versionado | 0% violacoes de regra",
    "fifo": "raw FIFO vs FIFO seguro separados no benchmark",
    "heuristic": "sem leitura Gemma multimodal | 92.5% no parse e falha em S03_WET_LOAD",
    "source": "Scenario pack sintetico · snapshot 20260505T172342Z",
}


def load_benchmark_summary(reports_dir: Path) -> dict[str, str]:
    report_dir = _latest_benchmark_report_dir(reports_dir)
    if report_dir is None:
        return _explicit_fallback("relatorio ausente")
    try:
        metrics = _load_metrics(report_dir / "metrics.json")
        rows = _load_summary_rows(report_dir / "summary.csv")
        return _build_summary(report_dir.name, metrics, rows)
    except (OSError, json.JSONDecodeError, csv.Error, TypeError, ValueError):
        return _explicit_fallback(f"schema invalido em {report_dir.name}")


def _latest_benchmark_report_dir(reports_dir: Path) -> Path | None:
    if not reports_dir.exists():
        return None
    candidates = [
        path
        for path in reports_dir.iterdir()
        if path.is_dir() and (path / "metrics.json").exists() and (path / "summary.csv").exists()
    ]
    return sorted(candidates)[-1] if candidates else None


def _load_metrics(metrics_path: Path) -> dict[str, dict[str, Any]]:
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    if not isinstance(metrics, dict):
        raise TypeError("metrics root must be an object")
    variant_metrics = metrics.get("variant_metrics")
    if not isinstance(variant_metrics, dict):
        raise TypeError("variant_metrics must be an object")

    full = _variant_metric(variant_metrics, "full")
    heuristic = _variant_metric(variant_metrics, "heuristic")
    raw_fifo = _optional_variant_metric(variant_metrics, RAW_FIFO_VARIANT)
    fifo_safe = _optional_variant_metric(
        variant_metrics,
        report_variant_name(OPERATIONAL_FIFO_VARIANT),
    )
    legacy_fifo = _optional_variant_metric(variant_metrics, OPERATIONAL_FIFO_VARIANT)
    for key in ("passed_count", "scenario_count", "constraint_violation_rate"):
        _required_metric_number(full, key)
    _required_metric_number(heuristic, "ticket_field_accuracy")
    _required_metric_number(raw_fifo, "decision_match_at_1", required=False)
    _required_metric_number(fifo_safe, "decision_match_at_1", required=False)
    _required_metric_number(legacy_fifo, "decision_match_at_1", required=False)
    return {
        "full": full,
        "heuristic": heuristic,
        RAW_FIFO_VARIANT: raw_fifo,
        FIFO_SAFE_VARIANT: fifo_safe,
        OPERATIONAL_FIFO_VARIANT: legacy_fifo,
    }


def _load_summary_rows(summary_path: Path) -> list[dict[str, str]]:
    rows = list(csv.DictReader(summary_path.read_text(encoding="utf-8").splitlines()))
    if not rows:
        raise ValueError("summary.csv must have rows")
    required_columns = {"scenario_id", "variant", "decision_match_at_1"}
    if not required_columns.issubset(rows[0].keys()):
        raise ValueError("summary.csv is missing required columns")
    return rows


def _build_summary(
    report_name: str,
    metrics: dict[str, dict[str, Any]],
    rows: list[dict[str, str]],
) -> dict[str, str]:
    full = metrics["full"]
    heuristic = metrics["heuristic"]
    raw_fifo = metrics[RAW_FIFO_VARIANT]
    fifo_safe = metrics[FIFO_SAFE_VARIANT]
    legacy_fifo = metrics[OPERATIONAL_FIFO_VARIANT]
    fifo_variant = RAW_FIFO_VARIANT if raw_fifo or fifo_safe else OPERATIONAL_FIFO_VARIANT
    fifo_misses = [
        row["scenario_id"]
        for row in rows
        if row.get("variant") == fifo_variant and row.get("decision_match_at_1") == "False"
    ]
    first_miss = fifo_misses[0] if fifo_misses else "nenhum"
    fifo_label = _fifo_label(
        miss_count=len(fifo_misses),
        first_miss=first_miss,
        raw_fifo=raw_fifo,
        fifo_safe=fifo_safe,
        legacy_fifo=legacy_fifo,
    )
    return {
        "full": (
            f"{int(full['passed_count'])}/{int(full['scenario_count'])} cenarios | "
            f"{percent_label(full['constraint_violation_rate'])} violacoes de regra"
        ),
        "fifo": f"{fifo_label} | ex.: {first_miss}",
        "heuristic": (
            "sem leitura Gemma multimodal"
            f" | {percent_label(heuristic['ticket_field_accuracy'])} no texto estruturado"
        ),
        "source": f"Scenario pack sintetico · {report_name}",
    }


def _fifo_label(
    *,
    miss_count: int,
    first_miss: str,
    raw_fifo: dict[str, Any] | None,
    fifo_safe: dict[str, Any] | None,
    legacy_fifo: dict[str, Any] | None,
) -> str:
    if raw_fifo or fifo_safe:
        safe_accuracy = _metric_number(fifo_safe, "decision_match_at_1", default=None)
        return (
            f"raw {miss_count} fora do alvo | seguro "
            f"{percent_label(safe_accuracy) if safe_accuracy is not None else 'n/a'}"
        )
    if legacy_fifo is not None:
        return f"{miss_count} cenarios fora do alvo | ex.: {first_miss}"
    return "schema sem linha FIFO reconhecida"


def _variant_metric(variant_metrics: dict[str, Any], variant: str) -> dict[str, Any]:
    metric = _optional_variant_metric(variant_metrics, variant)
    if metric is None:
        raise TypeError(f"variant_metrics.{variant} must be an object")
    return metric


def _optional_variant_metric(
    variant_metrics: dict[str, Any], variant: str
) -> dict[str, Any] | None:
    metric = variant_metrics.get(variant)
    if metric is None:
        return None
    if not isinstance(metric, dict):
        raise TypeError(f"variant_metrics.{variant} must be an object")
    return metric


def _metric_number(
    metric: dict[str, Any] | None,
    key: str,
    *,
    default: float | None,
) -> float | None:
    if metric is None:
        return default
    value = metric.get(key, default)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"metric {key} must be numeric") from exc


def _required_metric_number(
    metric: dict[str, Any] | None,
    key: str,
    *,
    required: bool = True,
) -> None:
    if metric is None:
        return
    value = _metric_number(metric, key, default=None)
    if value is None and required:
        raise TypeError(f"metric {key} is required")


def _explicit_fallback(reason: str) -> dict[str, str]:
    summary = dict(BENCHMARK_STRIP_FALLBACK)
    summary["source"] = f"{summary['source']} · fallback explicito: {reason}"
    return summary
