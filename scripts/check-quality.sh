#!/usr/bin/env bash
set -euo pipefail

RUN_SONAR=false

for arg in "$@"; do
  case "$arg" in
    --sonar) RUN_SONAR=true ;;
    *)
      echo "Argumento desconhecido: $arg" >&2
      exit 2
      ;;
  esac
done

echo "==> pytest"
if command -v pytest >/dev/null 2>&1; then
  pytest
elif command -v docker >/dev/null 2>&1; then
  docker build --target test -t pequiflux-yard-copilot:test .
  docker run --rm pequiflux-yard-copilot:test
else
  echo "pytest e docker não encontrados. Não foi possível executar testes." >&2
  exit 1
fi

echo "==> expected_ticket leakage guard"
if command -v pytest >/dev/null 2>&1; then
  pytest -q tests/scenarios/test_no_expected_ticket_leakage.py
elif command -v docker >/dev/null 2>&1; then
  docker run --rm pequiflux-yard-copilot:test pytest -q tests/scenarios/test_no_expected_ticket_leakage.py
else
  echo "pytest e docker não encontrados. Não foi possível executar leakage guard." >&2
  exit 1
fi

echo "==> extended B1 pack schema"
if command -v pytest >/dev/null 2>&1; then
  pytest -q tests/scenarios/test_extended_pack_schema.py
elif command -v docker >/dev/null 2>&1; then
  docker run --rm pequiflux-yard-copilot:test pytest -q tests/scenarios/test_extended_pack_schema.py
else
  echo "pytest e docker não encontrados. Não foi possível validar o B1 extended pack." >&2
  exit 1
fi

echo "==> black"
if command -v black >/dev/null 2>&1; then
  black --check app bench tests scripts
elif command -v docker >/dev/null 2>&1; then
  docker run --rm pequiflux-yard-copilot:test python -m black --check app bench tests scripts
else
  echo "black e docker não encontrados. Não foi possível executar format check." >&2
  exit 1
fi

echo "==> blueprint audit"
if command -v python >/dev/null 2>&1; then
  python -m app.cli.blueprint_audit
elif command -v docker >/dev/null 2>&1; then
  docker run --rm pequiflux-yard-copilot:test python -m app.cli.blueprint_audit
else
  echo "python e docker não encontrados. Não foi possível executar blueprint audit." >&2
  exit 1
fi

echo "==> text-runtime benchmark validation"
if command -v python >/dev/null 2>&1; then
  PEQUIFLUX_GEMMA_RUNTIME=text python -m app.cli.run_benchmark --manifest scenarios/manifest.json --output-dir /tmp/pequiflux-benchmark-validate
elif command -v docker >/dev/null 2>&1; then
  docker run --rm -e PEQUIFLUX_GEMMA_RUNTIME=text pequiflux-yard-copilot:test python -m app.cli.run_benchmark --manifest scenarios/manifest.json --output-dir /tmp/pequiflux-benchmark-validate
else
  echo "python e docker não encontrados. Não foi possível executar benchmark validado." >&2
  exit 1
fi

if [ "$RUN_SONAR" = true ]; then
  echo "==> SonarQube"
  if command -v sonar-scanner >/dev/null 2>&1; then
    if [ -n "${SONAR_HOST_URL:-}" ] && [ -n "${SONAR_TOKEN:-}" ]; then
      sonar-scanner \
        -Dsonar.host.url="$SONAR_HOST_URL" \
        -Dsonar.token="$SONAR_TOKEN" \
        -Dsonar.qualitygate.wait=true
    else
      echo "SONAR_HOST_URL ou SONAR_TOKEN ausente. Pulando SonarQube."
    fi
  else
    echo "sonar-scanner não encontrado. Pulando SonarQube."
  fi
fi
