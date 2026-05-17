from __future__ import annotations

import hashlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
README_FILES = (ROOT / "README.md", ROOT / "README.en.md")
STALE_SCREENSHOTS = {
    "assets/screenshots/pequiflux-ui-02-example-loaded.png",
    "assets/screenshots/pequiflux-ui-03-result.png",
    "assets/screenshots/pequiflux-ui-04-audit-expanded.png",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_readme_screenshot_references_exist_and_are_current() -> None:
    for readme in README_FILES:
        body = readme.read_text(encoding="utf-8")
        refs = sorted(set(re.findall(r"assets/screenshots/[^)`\]\"' >]+\.png", body)))

        assert "assets/screenshots/pequiflux-ui.png" in refs
        assert not (STALE_SCREENSHOTS & set(refs))
        assert refs, f"{readme.name} should keep the UI screenshot gallery."

        for ref in refs:
            assert (ROOT / ref).is_file(), f"{readme.name} references missing asset {ref}"


def test_writeup_screenshot_matches_canonical_readme_asset() -> None:
    canonical = ROOT / "assets/screenshots/pequiflux-ui.png"
    writeup = ROOT / "docs/writeup_assets/pequiflux-ui.png"

    assert _sha256(canonical) == _sha256(writeup)


def test_judge_demo_video_capture_path_is_documented() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    demo_script = (ROOT / "docs/DEMO_SCRIPT.md").read_text(encoding="utf-8")
    submission = (ROOT / "docs/HACKATHON_SUBMISSION.md").read_text(encoding="utf-8")
    capture_script = (ROOT / "scripts/capture_judge_demo_video.mjs").read_text(
        encoding="utf-8"
    )

    assert "judge-demo-video" in makefile
    assert "PEQUIFLUX_JUDGE_VIDEO_PATH" in makefile
    assert "host.docker.internal:8501" in makefile
    assert "make judge-demo-video" in demo_script
    assert "artifacts/judge-demo/pequiflux-gemma-proof.webm" in demo_script
    assert "make judge-demo-video" in submission
    assert "Judge proof" in capture_script
    assert "Test mode is active" in capture_script
