# Hackathon Submission

Mapa dos critérios esperados da submissão para evidências versionadas no repositório.

| Critério | Evidência no repo | Como verificar |
|---|---|---|
| Uso claro de Gemma | `app/gemma/`, `docs/gemma.md`, `docs/adr/ADR-0002-gemma-as-interpretation-layer.md` | Gemma interpreta documento; regras determinísticas decidem |
| Problema real e delimitado | `README.md`, `docs/product.md`, `docs/LIMITATIONS.md` | Escopo: despacho de pátio sob exceção operacional |
| Demo avaliável | `app/ui/streamlit_app.py`, `assets/screenshots/pequiflux-ui.png`, `assets/screenshots/pequiflux-ui-0*.png`, `docs/DEMO_SCRIPT.md` | `make demo-ready` para pré-voo completo com Gemma/Ollama; `make ui` para a demo real; `make ui-text` apenas para teste reproduzível sem modelo |
| Benchmark comparativo | `app/cli/run_benchmark.py`, `bench/metrics.py`, `bench/reports/sample/`, `bench/reports/extended/` | `make bench` gera `metrics.json`, `summary.csv`, `per_scenario.json` em `extended`; o sample público fica congelado e não é saída viva |
| Reprodutibilidade | `Dockerfile`, `compose.yaml`, `Makefile`, `config/env.example` | `make demo-text`, `make ui-text`, `make test`, `make audit` |
| Auditoria e explicabilidade | `app/audit/`, `app/services/decision_builder.py`, schemas em `scenarios/schemas/` | Payload final inclui `AuditRecord`, regras disparadas e hashes |
| Operador no controle | `app/services/operator_governance.py`, `docs/UI_DECISIONS.md` | UI mostra aprovar, bloquear ou sobrescrever com motivo |
| Falha fechada | `app/gemma/fallback.py`, `tests/unit/test_no_fallbacks.py` | Ausência de dependência gera erro/revisão, nunca substituição silenciosa |

## Claim Principal

Pe-Q.I torna mensurável quando e por que o FIFO puro deve ser quebrado: o benchmark preserva a comparação entre variantes, enquanto a UI operacional mostra status, caminhão, destino, restrições bloqueantes, documento interpretado, mensagem ao motorista e ação humana.

## Evidência Rápida

- UI final: `assets/screenshots/pequiflux-ui.png`
- Fluxo visual da UI: `assets/screenshots/pequiflux-ui-01-initial.png`, `assets/screenshots/pequiflux-ui-02-inputs-loaded.png`, `assets/screenshots/pequiflux-ui-03-decision-result.png`, `assets/screenshots/pequiflux-ui-04-evidence-and-operator.png`, `assets/screenshots/pequiflux-ui-05-tool-audit.png`
- Asset de writeup sincronizado: `docs/writeup_assets/pequiflux-ui.png`
- Benchmark sample público congelado: `bench/reports/sample/metrics.json`
- Benchmark extended interno: `bench/reports/extended/<run_id>/metrics.json`
- Roteiro de video: `docs/DEMO_SCRIPT.md`
- Limitacoes publicas: `docs/LIMITATIONS.md`
