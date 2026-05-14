from __future__ import annotations

import json
from pathlib import Path

from app.domain.models import DecisionRequest
from bench.clean_eval import expected_ticket_leakage_violations


SPLIT_MINIMUMS = {
    "public_train": 180,
    "public_dev": 60,
    "public_test_frozen": 60,
    "private_holdout": 60,
}
REQUIRED_METADATA_FIELDS = {
    "scenario_id",
    "scenario_family",
    "document_template_id",
    "modality",
    "perturbation_recipe",
    "created_by",
    "label_quality",
    "sha256",
}


def test_extended_b1_pack_has_emergency_splits_and_metadata() -> None:
    root = Path("scenarios/extended")
    for split, minimum in SPLIT_MINIMUMS.items():
        split_dir = root / split
        manifest_path = split_dir / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        cases = manifest["cases"]
        assert manifest["split"] == split
        assert manifest["scenario_count"] == len(cases)
        assert len(cases) >= minimum
        modalities = set()
        families = set()
        expected_review_count = 0
        for case in cases:
            files = case["files"]
            for logical_name in (
                "ticket",
                "queue",
                "operator_note",
                "weather_state",
                "resource_state",
                "expected_decision",
                "metadata",
            ):
                assert Path(files[logical_name]).exists(), files[logical_name]
            ticket_path = Path(files["ticket"])
            request = DecisionRequest.model_validate(case["request"])
            assert request.scenario_id == case["scenario_id"]
            assert request.ticket_ref == files["ticket"]
            metadata = json.loads(Path(files["metadata"]).read_text(encoding="utf-8"))
            assert REQUIRED_METADATA_FIELDS <= set(metadata)
            assert metadata["scenario_id"] == case["scenario_id"]
            assert metadata["split"] == split
            assert metadata["created_by"] == "generator"
            assert metadata["label_quality"] in {"auto", "reviewed"}
            assert metadata["perturbation_recipe"]
            assert len(metadata["sha256"]) == 64
            assert case["metadata"] == metadata
            if metadata["modality"] == "png":
                assert ticket_path.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), files["ticket"]
            if metadata["modality"] == "pdf_scanned":
                assert ticket_path.read_bytes().startswith(b"%PDF"), files["ticket"]
            if (
                split in {"public_dev", "public_test_frozen", "private_holdout"}
                and metadata["scenario_family"] == "S12_PDF_SCANNED_DOCUMENT_BLOCK"
            ):
                expected = json.loads(Path(files["expected_decision"]).read_text(encoding="utf-8"))
                assert expected["expected_status"] == "REVIEW_REQUIRED"
                assert expected["acceptable_trucks"] == [None]
                assert expected["acceptable_destinations"] == [None]
            else:
                expected = json.loads(Path(files["expected_decision"]).read_text(encoding="utf-8"))
            if expected["expected_status"] == "REVIEW_REQUIRED":
                expected_review_count += 1
            modalities.add(metadata["modality"])
            families.add(metadata["scenario_family"])
        assert {"txt", "png", "pdf_scanned"} <= modalities
        assert len(families) >= 20
        if split in {"public_dev", "public_test_frozen", "private_holdout"}:
            assert expected_review_count / len(cases) <= 0.15


def test_extended_eval_splits_do_not_leak_expected_ticket_sidecars() -> None:
    root = Path("scenarios/extended")
    for split in ("public_dev", "public_test_frozen", "private_holdout"):
        split_dir = root / split
        assert (
            expected_ticket_leakage_violations(
                manifest_path=split_dir / "manifest.json",
                scenario_dir=split_dir,
                variant="full",
            )
            == []
        )
