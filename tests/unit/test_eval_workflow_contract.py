from pathlib import Path


def test_eval_workflow_contract() -> None:
    workflow = Path(".github/workflows/eval.yml").read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert "pull_request:" in workflow
    assert "python -m bench.clean_eval" in workflow
    assert 'default: "gemma4:e4b"' in workflow
    assert '--runtime "$RUNTIME"' in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "submission_ready" in workflow
