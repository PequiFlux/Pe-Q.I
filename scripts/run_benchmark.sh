#!/usr/bin/env bash
set -euo pipefail

MANIFEST_PATH="${1:-scenarios/manifest.json}"
python -c "from pathlib import Path; print(Path('${MANIFEST_PATH}').resolve())"

