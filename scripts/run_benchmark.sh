#!/usr/bin/env bash
set -euo pipefail

MANIFEST_PATH="${1:-scenarios/manifest.json}"

if [[ "${PEQUIFLUX_IN_CONTAINER:-0}" == "1" ]]; then
  python -m app.cli.run_benchmark --manifest "${MANIFEST_PATH}"
  exit 0
fi

mkdir -p bench/reports
docker compose run --rm benchmark ./scripts/run_benchmark.sh "${MANIFEST_PATH}"
