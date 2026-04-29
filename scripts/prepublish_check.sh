#!/usr/bin/env bash
set -euo pipefail

if [[ "${PEQUIFLUX_IN_CONTAINER:-0}" == "1" ]]; then
  python -m compileall -q app tests
  pytest -q
  python -m app.cli.blueprint_audit --json >/dev/null
  python -m app.cli.run_benchmark \
    --manifest scenarios/manifest.json \
    --output-dir /tmp/pequiflux-prepublish-benchmark >/dev/null
  exit 0
fi

docker build --target test -t pequiflux-yard-copilot:test .
docker run --rm pequiflux-yard-copilot:test ./scripts/prepublish_check.sh
