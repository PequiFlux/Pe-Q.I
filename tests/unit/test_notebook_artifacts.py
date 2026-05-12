from __future__ import annotations

import json
from pathlib import Path


NOTEBOOKS = [
    Path("notebooks/01_baselines.ipynb"),
    Path("notebooks/02_multimodal_parsing_eval.ipynb"),
    Path("notebooks/03_robustness.ipynb"),
]


def test_required_notebooks_exist_and_reference_canonical_benchmark_modules() -> None:
    for path in NOTEBOOKS:
        notebook = json.loads(path.read_text(encoding="utf-8"))
        source = "\n".join("".join(cell.get("source", [])) for cell in notebook.get("cells", []))

        assert notebook["nbformat"] == 4
        assert notebook["cells"]
        assert "bench.reporting" in source or "bench.stats" in source
        assert "artifacts/latest" in source
