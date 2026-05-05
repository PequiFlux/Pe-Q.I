#!/usr/bin/env bash
set -euo pipefail

mkdir -p docs

status_line() {
  local tool="$1"
  local status="$2"
  local note="$3"
  echo "| $tool | $status | $note |"
}

{
  echo "# SETUP STATUS"
  echo
  echo "Atualizado em: $(date -Iseconds)"
  echo
  echo "## Ferramentas"
  echo
  echo "| Ferramenta | Status | Observação |"
  echo "|---|---|---|"

  if command -v serena >/dev/null 2>&1; then
    status_line "Serena" "ok" "CLI encontrada em $(command -v serena)"
  else
    status_line "Serena" "ausente" "Instalar globalmente antes de mudanças com busca simbólica obrigatória"
  fi

  if command -v graphify >/dev/null 2>&1; then
    status_line "Graphify" "ok" "CLI encontrada em $(command -v graphify)"
  else
    status_line "Graphify" "ausente" "Opcional; usar code-review-graph quando disponível"
  fi

  if command -v code-review-graph >/dev/null 2>&1; then
    status_line "code-review-graph" "ok" "CLI encontrada em $(command -v code-review-graph)"
  else
    status_line "code-review-graph" "ausente" "Grafo de revisão indisponível localmente"
  fi

  if command -v sonar-scanner >/dev/null 2>&1; then
    if [ -n "${SONAR_HOST_URL:-}" ] && [ -n "${SONAR_TOKEN:-}" ]; then
      status_line "SonarScanner" "ok" "CLI e variáveis SONAR_HOST_URL/SONAR_TOKEN disponíveis"
    else
      status_line "SonarScanner" "parcial" "CLI encontrada em $(command -v sonar-scanner); faltam SONAR_HOST_URL e/ou SONAR_TOKEN"
    fi
  else
    status_line "SonarScanner" "ausente" "Instalar scanner ou rodar via CI"
  fi

  echo
  echo "## Pendências"
  echo
  echo "- Atualizar este diagnóstico após mudanças no ambiente local."
  echo "- Ajustar credenciais/URL do SonarQube antes de usar Sonar como gate durável."
} > docs/SETUP_STATUS.md

echo "Bootstrap diagnosticado em docs/SETUP_STATUS.md"
