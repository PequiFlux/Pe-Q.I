#!/usr/bin/env bash
set -euo pipefail

if [[ "${PEQUIFLUX_IN_CONTAINER:-0}" == "1" ]]; then
  python -m app.cli.prewarm_gemma
  exit 0
fi

docker compose run --rm demo ./scripts/prewarm_models.sh
