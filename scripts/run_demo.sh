#!/usr/bin/env bash
set -euo pipefail

SCENARIO_ID="${1:-S01_BASELINE}"

if [[ "${PEQUIFLUX_IN_CONTAINER:-0}" == "1" ]]; then
  python -m app.cli.run_scenario --scenario "${SCENARIO_ID}"
  exit 0
fi

docker compose run --rm demo ./scripts/run_demo.sh "${SCENARIO_ID}"
