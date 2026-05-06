# DUPLICATION GUARD

## Termos equivalentes do domínio

- fila, queue, ranking, FIFO, priority, prioridade, score
- destino, destination, yard, pátio, blocked destination
- chuva, rain, wet load, weather state
- recurso, resource, conveyor, vehicle, capacity
- ticket, document, PDF, operator note, interpreted context
- decisão, decision, review state, error state, audit payload
- política, policy profile, hard constraint, rule id

## Antes de criar algo novo

Procurar:

- símbolos próximos com Serena;
- módulos relacionados em `.code-review-graph/` ou `code-review-graph`;
- docs em `docs/CODEMAP.md` e `docs/SURFACE_MAP.md`;
- testes unitários em `tests/unit`;
- cenários em `scenarios/cases`;
- contratos JSON em `scenarios/schemas`;
- regras publicadas no blueprint e docs de decisão.

## Itens que não devem ser duplicados

- Hard constraints: reutilizar `app/domain/constraints.py`.
- Ranking/FIFO/prioridade: reutilizar `app/domain/ranking.py`.
- FIFO bruto para comparação narrativa: reutilizar `app/services/raw_fifo.py`.
- Policy profile: reutilizar `app/domain/policy.py` e `scenarios/common/policy_profile.json`.
- IDs de regras de política: reutilizar `app/domain/enums.py::PolicyRule`; não escrever `PR-01`..`PR-06` como string solta em ranking, auditoria, UI ou testes.
- Resolução de verdade entre ticket, nota e estado: reutilizar `app/orchestration/truth_resolver.py`.
- Transições e estados terminais: reutilizar `app/orchestration/state_machine.py`.
- Construção de payload/decisão: reutilizar `app/services/decision_builder.py`.
- Finalização terminal com driver message, payload, persistência e log: reutilizar `DecisionOrchestrator.persist_and_log` / `_finalize_payload`.
- Gateway e contrato LLM: reutilizar `app/gemma/*`.
- Métricas de benchmark: reutilizar `bench/metrics.py`.

## Regras adicionadas

- Não criar fallback model, fallback heuristic, retry silencioso ou substituição automática de dependência.
- Não manter scripts soltos de teste manual de Gemma na raiz; contratos de runtime/adapter devem ficar em `tests/unit` ou CLIs oficiais.
- Manter apenas `technical_blueprint.md` da raiz como blueprint longo; `docs/technical_blueprint.md` deve permanecer uma ponte curta para evitar drift.
- Não colocar regra de domínio em `app/ui` ou `app/cli`; chamar orquestração/domínio existente.
- Não criar novo parser de ticket sem verificar `app/services/parser.py`, `app/services/structured_ticket_parser.py` e `app/adapters/document_adapter.py`.
- Fixtures textuais de ticket devem reutilizar `app/services/structured_ticket_parser.py`; `TextTicketRuntime` não deve extrair dados de frases do prompt.
- Casos multimodais do benchmark devem reutilizar o sidecar `expected_ticket.json`; não criar formato paralelo de fixture esperado por cenário.
- `scenarios/cases/` e `scenarios/manifest.json` estão congelados em 20 casos de vitrine; expansões futuras devem ir para `scenarios/extended/stress/` ou `scenarios/extended/failure/`, não para o sample principal.
- Não parsear `arrival_ts` fora de `app/adapters/csv_adapter.py`; timestamps de fila precisam ter timezone explícito e serem normalizados para UTC.
- Leitura canônica de `queue.csv` deve passar por `app/adapters/csv_adapter.load_queue_rows`; não manter leitor paralelo de fila para UI ou FIFO bruto.
- Não criar novo formato de cenário sem atualizar `scenarios/manifest.json`, schemas e testes de cenário.
- Notas operacionais com termos de revisão (`revisar`, `conferir`) devem prevalecer sobre classificações automáticas como `WET_LOAD`.
- Classificação de exceções deve acumular sinais em `secondary_exceptions` e `affected_resources`; não voltar a early return por primeira condição em `app/services/exception_classifier.py`.
- Quando `MANUAL_REVIEW_HINT` aparecer em achados de classificação, mesmo como secundária, `needs_human_review` deve ser `true`; não depender apenas da exceção primária.
- Combinações críticas de hierarquia devem ficar como testes unitários em `tests/unit/test_exception_classifier.py`, `tests/unit/test_constraints.py` e `tests/unit/test_truth_resolver.py`; não expandir o sample público congelado só para cobrir variantes de regra.
- Judge Mode da UI deve reutilizar cenários do manifest e `DecisionOrchestrator`; não criar regra de decisão paralela para explicar FIFO vs Pe-Q.I.
- Screenshot do README deve usar `assets/screenshots/pequiflux-ui.png`; manter `docs/writeup_assets/pequiflux-ui.png` sincronizado quando usado em material de submissão.
- Visualizações de fila e heatmap na UI devem usar `queue_diff` e `AuditRecord`; não recriar validação de hard constraints no front-end.
- `queue_diff` deve representar a fila após a chamada: caminhão chamado usa `called` e `position_after=None`; demais itens usam `unchanged`, `shifted` ou `blocked`. Não reintroduzir `recommended/skipped` como estado de fila.
- Toda contribuição de score em `app/domain/ranking.py` deve adicionar `PolicyRule` correspondente em `fired_rules`; não deixar bônus/penalidade só em `reason_details`.
- Faixas de benchmark na UI devem usar `app.ui.benchmark_summary.load_benchmark_summary`; não recriar `_benchmark_summary`, `_latest_benchmark_report_dir` ou métrica de comparação dentro de `streamlit_app.py`.
- O benchmark deve distinguir `raw_fifo` de `fifo_safe`; não chamar a variante operacional `fifo` de FIFO puro em relatório público.
- Nomes públicos de variante do benchmark devem passar por `bench.variants.report_variant_name`; não espalhar tradução `fifo` -> `fifo_safe` em CLI, UI ou docs de execução.
- Montagem de linhas, match esperado, violação de constraint e acurácia de ticket do benchmark devem reutilizar `bench.rows`; não recolocar essa lógica em `app/cli/run_benchmark.py`.
- Completude de auditoria do benchmark deve ser status-aware em `bench.rows.audit_complete`; `PREVIEW_READY` exige matriz de validação, e `BLOCKED`/`REVIEW_REQUIRED` exigem razão terminal, contexto observado, proveniência e todos os hashes de entrada gerados pelo orquestrador.
- Validação de violação do FIFO bruto deve tratar par caminhão-destino ausente da matriz como inválido em `bench.rows.pair_rejected`; não interpretar destino desconhecido como “sem violação”.
- Validação de cenário/benchmark deve reutilizar `bench.validation.validate_payload`; não importar helpers privados de `app/cli`.
- Relatórios CSV de benchmark devem reutilizar `bench.reporting.render_summary_csv`; não montar CSV manualmente com `",".join(...)`.
- Atalhos de execução devem apontar para Docker/Compose, scripts existentes ou CLIs existentes; não criar novo runner paralelo para demo, teste ou benchmark.
- Caminhos reprodutíveis mínimos devem usar `demo-text`/`ui-text`; não fazer quickstart depender implicitamente do serviço `gemma`.
- Checks públicos devem reutilizar `pytest`, `black`, `app.cli.blueprint_audit` e `app.cli.run_benchmark`; não criar runner paralelo de CI para métricas ou auditoria.
- Format check público deve rodar `black --check app bench tests scripts`; não voltar a listas manuais de arquivos em CI, Makefile ou `scripts/check-quality.sh`.
- Consistência do sample público deve ficar em `tests/unit/test_public_sample_consistency.py`; não criar validação paralela entre README, `metrics.json` e `summary.csv`.
- A imagem de teste deve incluir apenas `bench/reports/sample/` entre relatórios versionados; não remover as exceções correspondentes em `.dockerignore` sem mover o teste de contrato público.
- O benchmark público congelado deve continuar em `bench/reports/sample/` com 20 cenários; runs maiores ou exploratórios devem ir para `bench/reports/extended/`, não para novos snapshots públicos.
- `bench/reports/sample/` é evidência pública congelada e não pode ser usado como `--output-dir`; novos snapshots de teste devem ir para `bench/reports/extended-sample/<run_id>` ou diretório local temporário.
- O catálogo humano canônico do scenario pack deve ficar em `scenarios/README.md`; `README.md` e `docs/scenario-pack.md` devem resumir e apontar para ele, não repetir a lista completa.
- Finalização de ação humana deve reutilizar `SQLiteStore.save_operator_finalization`; não encadear `save_operator_action`, `save_decision_finalized` e `save_audit_record` com commits separados.
- Novos blocos da UI devem entrar em `app/ui/components/*`, `scenario_loader.py`, `ui_runner.py` ou `styles.py` conforme responsabilidade; não voltar a concentrar carregamento de cenário, orquestração, persistência e renderização em `streamlit_app.py`.
- Renderizadores e helpers compartilhados entre módulos de UI devem ser importados por nomes públicos sem `_`; prefixo `_` fica reservado para helpers internos do próprio arquivo.
- Comparação FIFO bruta da UI deve importar `raw_fifo_call` e `raw_queue_rows` de `app.services.raw_fifo`; não recriar wrappers ou leitura de CSV em `app/ui/components/common.py`.
- A UI deve obter `DecisionOrchestrator` via `app/ui/ui_runner.py` e `st.cache_resource`; não chamar `build_gemma_adapter()` diretamente em componente ou composição de tela.
- Novas mudanças no fluxo de decisão devem encaixar nas etapas `load_inputs`, `interpret_context`, `validate_and_rank`, `build_payload` ou `persist_and_log`; não voltar a concentrar o pipeline inteiro em `run_decision()`.
- Estados de orquestração só podem mudar por `WorkflowStateMachine.transition_to` ou `WorkflowStateMachine.force_terminal`; não atribuir `current_state` diretamente fora da máquina de estados.
