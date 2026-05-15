from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any


SPLIT_SIZES = {
    "public_train": 180,
    "public_dev": 60,
    "public_test_frozen": 100,
    "private_holdout": 60,
}
EVALUATION_SPLITS = {"public_dev", "public_test_frozen", "private_holdout"}
EVALUATION_REVIEW_FAMILIES = {
    "S03_WET_LOAD",
    "S06_DOCUMENT_BLOCK",
    "S11_IMAGE_ROTATED_WET_LOAD",
    "S12_PDF_SCANNED_DOCUMENT_BLOCK",
    "S13_TRUCK_ID_NOT_IN_QUEUE",
    "S14_NOTE_RAIN_WEATHER_NONE_CONFLICT",
    "S15_UNKNOWN_DESTINATION_IN_TICKET",
}
MULTIMODAL_SUFFIXES = {".pdf", ".png", ".jpg", ".jpeg"}
PERTURBATIONS = [
    "rotation_90",
    "rotation_minus_90",
    "light_skew",
    "blur",
    "jpeg_compression",
    "low_resolution",
    "ocr_noise",
    "pt_br_abbreviation",
    "missing_field",
    "ticket_note_conflict",
    "unknown_destination",
    "blocked_resource",
    "weather_load_conflict",
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the deterministic B1 extended pack.")
    parser.add_argument("--source-manifest", default="scenarios/manifest.json")
    parser.add_argument("--output-root", default="scenarios/extended")
    args = parser.parse_args()

    build_extended_pack(Path(args.source_manifest), Path(args.output_root))


def build_extended_pack(source_manifest: Path, output_root: Path) -> None:
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    base_cases = manifest["cases"]
    for split, size in SPLIT_SIZES.items():
        split_dir = output_root / split
        split_dir.mkdir(parents=True, exist_ok=True)
        cases = []
        selected_cases = _cases_for_split(base_cases=base_cases, split=split, size=size)
        for index, base_case in enumerate(selected_cases):
            cycle = index // len(base_cases) + 1
            scenario_id = f"B1_{split.upper()}_{index + 1:03d}_{base_case['scenario_id']}"
            case_dir = split_dir / scenario_id
            if case_dir.exists():
                shutil.rmtree(case_dir)
            case_dir.mkdir(parents=True)
            case = _copy_case(
                base_case=base_case,
                case_dir=case_dir,
                scenario_id=scenario_id,
                split=split,
                cycle=cycle,
                index=index,
            )
            cases.append(case)
        _write_manifest(
            split_dir=split_dir,
            split=split,
            source_manifest=source_manifest,
            common_manifest=manifest,
            cases=cases,
        )


def _cases_for_split(
    *,
    base_cases: list[dict[str, Any]],
    split: str,
    size: int,
) -> list[dict[str, Any]]:
    if split not in EVALUATION_SPLITS:
        return [base_cases[index % len(base_cases)] for index in range(size)]

    dispatchable_cases = [
        case for case in base_cases if case["scenario_id"] not in EVALUATION_REVIEW_FAMILIES
    ]
    selected = list(base_cases)
    fill_index = 0
    while len(selected) < size:
        selected.append(dispatchable_cases[fill_index % len(dispatchable_cases)])
        fill_index += 1
    return selected[:size]


def _copy_case(
    *,
    base_case: dict[str, Any],
    case_dir: Path,
    scenario_id: str,
    split: str,
    cycle: int,
    index: int,
) -> dict[str, Any]:
    base_files = {name: Path(path) for name, path in base_case["files"].items()}
    files: dict[str, str] = {}
    for logical_name, source_path in base_files.items():
        target_name = source_path.name
        target_path = case_dir / target_name
        shutil.copy2(source_path, target_path)
        if logical_name == "expected_decision":
            _adjust_expected_decision_for_clean_eval(
                target_path=target_path,
                split=split,
                base_case=base_case,
            )
        if logical_name == "ticket":
            _materialize_ticket_document_if_needed(
                target_path=target_path,
                source_ticket_path=source_path,
                scenario_id=scenario_id,
                perturbations=_perturbations_for(_modality(target_path), index),
            )
        files[logical_name] = str(target_path)

    ticket_path = Path(files["ticket"])
    sidecar_source = base_files["ticket"].with_name("expected_ticket.json")
    if sidecar_source.exists() and _should_copy_expected_ticket(split, ticket_path):
        target_sidecar = case_dir / "expected_ticket.json"
        shutil.copy2(sidecar_source, target_sidecar)

    metadata_path = case_dir / "metadata.json"
    metadata = _metadata(
        scenario_id=scenario_id,
        split=split,
        base_case=base_case,
        case_dir=case_dir,
        ticket_path=ticket_path,
        cycle=cycle,
        index=index,
    )
    metadata_path.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    files["metadata"] = str(metadata_path)

    request = dict(base_case["request"])
    request.update(
        {
            "request_id": f"REQ-{scenario_id}",
            "scenario_id": scenario_id,
            "queue_csv_ref": files["queue"],
            "ticket_ref": files["ticket"],
        }
    )
    return {
        "scenario_id": scenario_id,
        "description": f"B1 {split} case derived from {base_case['scenario_id']}: {base_case['description']}",
        "files": files,
        "request": request,
        "metadata": metadata,
    }


def _metadata(
    *,
    scenario_id: str,
    split: str,
    base_case: dict[str, Any],
    case_dir: Path,
    ticket_path: Path,
    cycle: int,
    index: int,
) -> dict[str, Any]:
    modality = _modality(ticket_path)
    return {
        "scenario_id": scenario_id,
        "scenario_family": base_case["scenario_id"],
        "document_template_id": f"{base_case['scenario_id']}-template",
        "modality": modality,
        "perturbation_recipe": _perturbations_for(modality, index),
        "created_by": "generator",
        "label_quality": "reviewed" if split in EVALUATION_SPLITS else "auto",
        "source_case_id": base_case["scenario_id"],
        "split": split,
        "cycle": cycle,
        "sha256": _case_sha256(case_dir),
    }


def _write_manifest(
    *,
    split_dir: Path,
    split: str,
    source_manifest: Path,
    common_manifest: dict[str, Any],
    cases: list[dict[str, Any]],
) -> None:
    manifest = {
        "version": "B1-emergency-0.1",
        "split": split,
        "scenario_count": len(cases),
        "source_manifest": str(source_manifest),
        "policy_profile_ref": common_manifest["policy_profile_ref"],
        "destinations_ref": common_manifest["destinations_ref"],
        "leakage_policy": (
            "expected_ticket.json allowed only in public_train; forbidden for multimodal "
            "public_dev, public_test_frozen and private_holdout evaluation cases"
        ),
        "cases": cases,
    }
    (split_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _should_copy_expected_ticket(split: str, ticket_path: Path) -> bool:
    return split not in EVALUATION_SPLITS or ticket_path.suffix.lower() not in MULTIMODAL_SUFFIXES


def _materialize_ticket_document_if_needed(
    *,
    target_path: Path,
    source_ticket_path: Path,
    scenario_id: str,
    perturbations: list[str],
) -> None:
    if target_path.suffix.lower() != ".png" or target_path.read_bytes().startswith(
        b"\x89PNG\r\n\x1a\n"
    ):
        return
    source_sidecar = source_ticket_path.with_name("expected_ticket.json")
    if not source_sidecar.exists():
        return
    ticket = json.loads(source_sidecar.read_text(encoding="utf-8"))
    _render_ticket_png(
        target_path=target_path,
        scenario_id=scenario_id,
        ticket=ticket,
        rotate=any(item.startswith("rotation") for item in perturbations),
    )


def _adjust_expected_decision_for_clean_eval(
    *,
    target_path: Path,
    split: str,
    base_case: dict[str, Any],
) -> None:
    if split not in EVALUATION_SPLITS:
        return
    if base_case["scenario_id"] != "S12_PDF_SCANNED_DOCUMENT_BLOCK":
        return
    expected = json.loads(target_path.read_text(encoding="utf-8"))
    expected.update(
        {
            "expected_status": "REVIEW_REQUIRED",
            "acceptable_trucks": [None],
            "acceptable_destinations": [None],
            "required_constraints": [],
            "fifo_break_expected": False,
            "expected_primary_exception": "DOCUMENT_BLOCK",
        }
    )
    target_path.write_text(json.dumps(expected, indent=2, sort_keys=True), encoding="utf-8")


def _render_ticket_png(
    *,
    target_path: Path,
    scenario_id: str,
    ticket: dict[str, Any],
    rotate: bool,
) -> None:
    fitz = _load_pymupdf()
    doc = fitz.open()
    page = doc.new_page(width=900, height=600)
    fields = [
        ("PequiFlux synthetic ticket", scenario_id),
        ("ticket_id", ticket.get("ticket_id")),
        ("truck_id", ticket.get("truck_id")),
        ("vehicle_type", ticket.get("vehicle_type")),
        ("document_status", ticket.get("document_status")),
        ("load_condition", ticket.get("load_condition")),
        ("destination_constraints", ", ".join(ticket.get("destination_constraints") or [])),
        ("contract_priority_flag", ticket.get("contract_priority_flag")),
        ("parse_confidence", ticket.get("parse_confidence")),
    ]
    lines = [f"{label}: {value}" for label, value in fields if value not in (None, "")]
    if rotate:
        page.insert_textbox(
            fitz.Rect(36, 36, 560, 840),
            "\n".join(lines),
            fontsize=22,
            fontname="helv",
            rotate=90,
        )
    else:
        page.insert_textbox(
            fitz.Rect(48, 48, 840, 552),
            "\n".join(lines),
            fontsize=22,
            fontname="helv",
        )
    pixmap = page.get_pixmap(matrix=fitz.Matrix(1.6, 1.6), alpha=False)
    pixmap.save(target_path)
    doc.close()


def _load_pymupdf() -> Any:
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover - dependency is part of requirements
        raise RuntimeError("PyMuPDF is required to render synthetic image tickets") from exc
    return fitz


def _modality(ticket_path: Path) -> str:
    suffix = ticket_path.suffix.lower()
    if suffix == ".txt":
        return "txt"
    if suffix == ".pdf":
        return "pdf_scanned"
    if suffix == ".png":
        return "png"
    if suffix in {".jpg", ".jpeg"}:
        return "jpg"
    return suffix.removeprefix(".") or "unknown"


def _perturbations_for(modality: str, index: int) -> list[str]:
    if modality == "txt":
        return [PERTURBATIONS[(index + 7) % len(PERTURBATIONS)]]
    first = PERTURBATIONS[index % len(PERTURBATIONS)]
    second = PERTURBATIONS[(index + 3) % len(PERTURBATIONS)]
    return list(dict.fromkeys([first, second]))


def _case_sha256(case_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(case_dir.iterdir()):
        if path.name == "metadata.json" or not path.is_file():
            continue
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


if __name__ == "__main__":
    main()
