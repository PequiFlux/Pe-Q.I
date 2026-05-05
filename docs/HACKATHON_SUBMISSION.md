# Hackathon Submission

Mapa dos criterios esperados da submissao para evidencias versionadas no repositorio.

| Criterio | Evidencia no repo | Como verificar |
|---|---|---|
| Uso claro de Gemma | `app/gemma/`, `docs/gemma.md`, `docs/adr/ADR-0002-gemma-as-interpretation-layer.md` | Gemma interpreta documento; regras deterministicas decidem |
| Problema real e delimitado | `README.md`, `docs/product.md`, `docs/LIMITATIONS.md` | Escopo: despacho de patio sob excecao operacional |
| Demo avaliavel | `app/ui/streamlit_app.py`, `assets/screenshots/pequiflux-ui.png`, `docs/DEMO_SCRIPT.md` | `make ui` ou `docker compose --profile ui up ui` |
| Benchmark comparativo | `app/cli/run_benchmark.py`, `bench/metrics.py`, `bench/reports/sample/` | `make bench` gera `metrics.json`, `summary.csv`, `per_scenario.json` |
| Reprodutibilidade | `Dockerfile`, `compose.yaml`, `Makefile`, `config/env.example` | `make demo`, `make test`, `make audit` |
| Auditoria e explicabilidade | `app/audit/`, `app/services/decision_builder.py`, schemas em `scenarios/schemas/` | Payload final inclui `AuditRecord`, regras disparadas e hashes |
| Operador no controle | `app/services/operator_governance.py`, `docs/UI_DECISIONS.md` | UI mostra aprovar, bloquear ou sobrescrever com motivo |
| Falha fechada | `app/gemma/fallback.py`, `tests/unit/test_no_fallbacks.py` | Ausencia de dependencia gera erro/revisao, nunca substituicao silenciosa |

## Claim Principal

Pe-Q.I torna mensuravel quando e por que o FIFO puro deve ser quebrado: o sistema mostra quem seria chamado por FIFO, quem o Pe-Q.I recomenda, quais restricoes bloquearam alternativas, o que o documento trouxe e qual acao humana ainda falta.

## Evidencia Rapida

- UI final: `assets/screenshots/pequiflux-ui.png`
- Benchmark sample: `bench/reports/sample/metrics.json`
- Roteiro de video: `docs/DEMO_SCRIPT.md`
- Limitacoes publicas: `docs/LIMITATIONS.md`
