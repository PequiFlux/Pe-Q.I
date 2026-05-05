# CODEMAP

Mapa vivo do repositório PequiFlux Yard Copilot.

## Módulos principais

| Módulo | Caminho | Responsabilidade | Dependências principais | Observações |
|---|---|---|---|---|
| UI | `app/ui` | Interface Streamlit em Judge Mode para demonstrar cenários narrativos e a legitimidade da quebra de FIFO antes dos detalhes técnicos | `app/orchestration`, `app/adapters`, `bench/reports` | `streamlit_app.py` compõe a tela com imports públicos de componentes; `benchmark_summary.py` valida schema leve do relatório antes da faixa pública; `scenario_loader.py` carrega fixtures e prepara `DecisionRequest`; `ui_runner.py` chama `DecisionOrchestrator` com cache de recurso Streamlit; `components/decision_card.py`, `components/validation_matrix.py` e `components/audit_panel.py` concentram cartões, heatmap e ação/auditoria; `components/common.py` concentra helpers compartilhados de apresentação; `styles.py` concentra CSS. CSV/JSON ficam no Modo técnico |
| CLI | `app/cli` | Entrypoints para cenário, benchmark, prewarm e auditoria de blueprint | `app/orchestration`, `bench`, `scenarios` | Deve continuar executável via Docker; `demo-text`/`ui-text` cobrem reprodutibilidade mínima sem serviço `gemma` |
| Orquestração | `app/orchestration` | Fluxo de decisão, resolução de verdade e máquina de estados | `app/domain`, `app/services`, `app/audit` | `DecisionOrchestrator.run_decision()` é fachada; etapas internas são `load_inputs`, `interpret_context`, `validate_and_rank`, `build_payload` e `persist_and_log`, coordenando camadas sem substituir regras determinísticas; terminais excepcionais passam por `WorkflowStateMachine.force_terminal` |
| Domínio | `app/domain` | Modelos, enums, constraints, ranking e política determinística | `scenarios/common` | Regras hard-constraint vivem aqui; `PolicyRule` é a fonte única dos IDs `PR-01`..`PR-06` usados em ranking, auditoria, UI e testes |
| Serviços | `app/services` | Builders, parsers, governança operacional, classificação de exceções, FIFO bruto e mensagens | `app/domain`, `app/gemma` | Adaptam dados para decisão sem fallback silencioso; `raw_fifo.py` centraliza a chamada FIFO bruta usada por UI e benchmark |
| Gemma | `app/gemma` | Runtime, adapter, schemas, prompts e gateway da camada LLM | `app/domain`, runtime externo | Interpretação deve falhar fechado quando inválida; `TextTicketRuntime` consome texto de fixture por metadata e, em casos multimodais de CI, `expected_ticket.json` sidecar |
| Adapters | `app/adapters` | Leitura de CSV, estados, notas e documentos | `app/domain`, arquivos de cenário | Entrada de dados sintéticos e públicos |
| Storage | `app/storage` | SQLite, migrations e log JSONL | `app/audit`, `app/domain` | Persistência local e auditável; finalização humana usa transação única em `SQLiteStore.save_operator_finalization` |
| Audit | `app/audit` | Payloads e serviço de auditoria | `app/domain`, `app/orchestration` | Preserva rastreabilidade de decisões |
| Benchmarks | `bench` | Validação, montagem de linhas, relatórios, nomes públicos de variantes e métricas do pacote de cenários | `scenarios`, `app/cli` | `app.cli.run_benchmark` orquestra a execução chamada por Compose/CI; `bench.rows` monta linhas `raw_fifo`/`fifo_safe`/payload, match esperado e violação de constraint; `bench.variants` normaliza `fifo` para `fifo_safe`; `bench.validation` valida payload esperado; `bench.reporting` renderiza `summary.csv` com `csv.DictWriter`; reporta `raw_fifo`, `fifo_safe`, `heuristic` e `full`; casos multimodais podem fixar `expected_ticket.json` |
| CI | `.github/workflows`, `Makefile`, `scripts/check-quality.sh` | Quality gate público e reprodutível | `requirements-all.txt`, `app/cli`, `tests`, `bench` | GitHub Actions roda Black no escopo formatado, `pytest -q`, blueprint audit e benchmark smoke com `PEQUIFLUX_GEMMA_RUNTIME=text`; `make quality` espelha Black/test/audit/benchmark smoke via Docker |
| Evidências | `assets/screenshots`, `bench/reports/sample`, `docs/DEMO_SCRIPT.md`, `docs/HACKATHON_SUBMISSION.md`, `docs/LIMITATIONS.md`, `docs/UI_DECISIONS.md` | Artefatos de avaliação para GitHub/hackathon | `app/ui`, `bench`, `docs` | Mantém demo, benchmark, limites e decisões de UI encontráveis em até dois minutos |
| Scenarios | `scenarios` | Fixtures sintéticas, manifest, schemas JSON e README narrativo por cenário | `tests/scenarios`, `bench` | Fonte de casos de validação; S01-S10 formam o pack obrigatório original e S11+ ampliam robustez multimodal, conflitos de verdade e stress; casos `pdf/png/jpg/jpeg` podem carregar `expected_ticket.json` sidecar |
| Tests | `tests` | Testes unitários e de cenário | `app`, `bench`, `scenarios` | Cobrem constraints, auditoria, runtime e E2E |

## Fluxos importantes

- Cenário CLI/UI: adapters carregam fixtures; `DecisionOrchestrator` executa `load_inputs -> interpret_context -> validate_and_rank -> build_payload -> persist_and_log`; domínio aplica constraints/ranking quando há verdade suficiente; serviços constroem decisão; auditoria registra resultado terminal.
- Benchmark: `app.cli.run_benchmark` executa casos de `scenarios/manifest.json`; `bench.rows`, `bench.variants`, `bench.validation`, `bench.reporting` e `bench.metrics` concentram montagem, nomes públicos, validação, CSV e métricas.
- LLM: `app/gemma` interpreta contexto; saída ausente ou inválida deve gerar erro/revisão explícita, nunca fallback de decisão.

## Áreas sensíveis

- Não duplicar regras de `app/domain/constraints.py`, `app/domain/ranking.py` ou `app/domain/policy.py`.
- Não introduzir fallback model, fallback heuristic, retry silencioso ou modo degradado.
- Não commitar dados reais, credenciais ou identificadores operacionais fora dos placeholders sintéticos.
- Não tratar `.code-review-graph/` como código-fonte.
