from __future__ import annotations

import json
from pathlib import Path

from app.ui.benchmark_summary import load_benchmark_summary


def test_load_benchmark_summary_reads_current_schema(tmp_path: Path) -> None:
    report_dir = tmp_path / "20260505T000000Z"
    report_dir.mkdir()
    (report_dir / "metrics.json").write_text(
        json.dumps(
            {
                "variant_metrics": {
                    "raw_fifo": {"decision_match_at_1": 0.3},
                    "fifo_safe": {"decision_match_at_1": 0.8},
                    "heuristic": {"ticket_field_accuracy": 0.925},
                    "full": {
                        "passed_count": 20,
                        "scenario_count": 20,
                        "constraint_violation_rate": 0.0,
                    },
                }
            }
        ),
        encoding="utf-8",
    )
    (report_dir / "summary.csv").write_text(
        "\n".join(
            [
                "scenario_id,variant,decision_match_at_1",
                "S01,raw_fifo,True",
                "S02,raw_fifo,False",
            ]
        ),
        encoding="utf-8",
    )

    summary = load_benchmark_summary(tmp_path)

    assert summary["full"] == "20/20 cenarios | 0% violacoes de regra"
    assert summary["fifo"] == "raw 1 fora do alvo | seguro 80% | ex.: S02"
    assert summary["heuristic"] == "sem leitura Gemma multimodal | 92% no texto estruturado"
    assert summary["source"] == "Scenario pack sintetico · 20260505T000000Z"


def test_load_benchmark_summary_returns_unavailable_summary_for_invalid_schema(
    tmp_path: Path,
) -> None:
    report_dir = tmp_path / "20260505T000000Z"
    report_dir.mkdir()
    (report_dir / "metrics.json").write_text(
        json.dumps({"variant_metrics": {"full": {"passed_count": 10}}}),
        encoding="utf-8",
    )
    (report_dir / "summary.csv").write_text(
        "scenario_id,variant,decision_match_at_1\nS01,full,True\n",
        encoding="utf-8",
    )

    summary = load_benchmark_summary(tmp_path)

    assert summary["full"] == "pack versionado | 0% violacoes de regra"
    assert "resumo indisponivel: schema invalido em 20260505T000000Z" in summary["source"]
