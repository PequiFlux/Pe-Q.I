from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_portuguese_readme_keeps_conservative_claim_frame() -> None:
    body = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "não deve ser apresentado como sistema pronto para produção" in body
    assert "dados e cenários são sintéticos" in body
    assert "não de validação industrial ou prontidão produtiva" in body


def test_english_readme_keeps_conservative_claim_frame() -> None:
    body = (ROOT / "README.en.md").read_text(encoding="utf-8")

    assert "should not be presented as production-ready software" in body
    assert "The data and scenarios are synthetic" in body
    assert "not industrial validation or production readiness" in body


def test_submission_doc_reinforces_non_production_positioning() -> None:
    body = (ROOT / "docs/HACKATHON_SUBMISSION.md").read_text(encoding="utf-8")

    assert "prova de conceito técnica" in body
    assert "não reivindica dados reais de campo" in body
    assert "integração produtiva" in body
    assert "não reivindica" in body
