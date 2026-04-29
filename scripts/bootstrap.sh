#!/usr/bin/env bash
set -euo pipefail

mkdir -p cache bench/reports var/log var/db

if [[ "${PEQUIFLUX_IN_CONTAINER:-0}" == "1" ]]; then
  python -m app.cli.run_scenario --scenario S01_BASELINE >/dev/null
  exit 0
fi

docker build -t pequiflux-yard-copilot:local .
docker build --target test -t pequiflux-yard-copilot:test .
docker compose run --rm test ./scripts/prepublish_check.sh
