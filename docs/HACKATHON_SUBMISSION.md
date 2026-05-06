# Hackathon Submission

Mapa dos criterios esperados da submissao para evidencias versionadas no repositorio.

| Criterio | Evidencia no repo | Como verificar |
|---|---|---|
| Uso claro de Gemma | `app/gemma/`, `docs/gemma.md`, `docs/adr/ADR-0002-gemma-as-interpretation-layer.md` | Gemma interpreta documento; regras deterministicas decidem |
| Problema real e delimitado | `README.md`, `docs/product.md`, `docs/LIMITATIONS.md` | Escopo: despacho de patio sob excecao operacional |
| Demo avaliavel | `app/ui/streamlit_app.py`, `assets/screenshots/pequiflux-ui.png`, `docs/DEMO_SCRIPT.md` | `make ui-text` sem GPU; `make ui` para Gemma/Ollama completo |
| Benchmark comparativo | `app/cli/run_benchmark.py`, `bench/metrics.py`, `bench/reports/sample/`, `bench/reports/extended/` | `make bench` gera `metrics.json`, `summary.csv`, `per_scenario.json` em `extended`; o sample público fica congelado e não é saída viva |
| Reprodutibilidade | `Dockerfile`, `compose.yaml`, `Makefile`, `config/env.example` | `make demo-text`, `make ui-text`, `make test`, `make audit` |
| Auditoria e explicabilidade | `app/audit/`, `app/services/decision_builder.py`, schemas em `scenarios/schemas/` | Payload final inclui `AuditRecord`, regras disparadas e hashes |
| Operador no controle | `app/services/operator_governance.py`, `docs/UI_DECISIONS.md` | UI mostra aprovar, bloquear ou sobrescrever com motivo |
| Falha fechada | `app/gemma/fallback.py`, `tests/unit/test_no_fallbacks.py` | Ausencia de dependencia gera erro/revisao, nunca substituicao silenciosa |

## Claim Principal

Pe-Q.I torna mensuravel quando e por que o FIFO puro deve ser quebrado: o benchmark preserva a comparacao entre variantes, enquanto a UI operacional mostra status, caminhao, destino, restricoes bloqueantes, documento interpretado, mensagem ao motorista e acao humana.

## Evidencia Rapida

- UI final: `assets/screenshots/pequiflux-ui.png`
- Benchmark sample publico congelado: `bench/reports/sample/metrics.json`
- Benchmark extended interno: `bench/reports/extended/<run_id>/metrics.json`
- Roteiro de video: `docs/DEMO_SCRIPT.md`
- Limitacoes publicas: `docs/LIMITATIONS.md`
