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
- Não colocar regra de domínio em `app/ui` ou `app/cli`; chamar orquestração/domínio existente.
- Não criar novo parser de ticket sem verificar `app/services/parser.py`, `app/services/structured_ticket_parser.py` e `app/adapters/document_adapter.py`.
- Fixtures textuais de ticket devem reutilizar `app/services/structured_ticket_parser.py`; `TextTicketRuntime` não deve extrair dados de frases do prompt.
- Casos multimodais do benchmark devem reutilizar o sidecar `expected_ticket.json`; não criar formato paralelo de fixture esperado por cenário.
- Não parsear `arrival_ts` fora de `app/adapters/csv_adapter.py`; timestamps de fila precisam ter timezone explícito e serem normalizados para UTC.
- Não criar novo formato de cenário sem atualizar `scenarios/manifest.json`, schemas e testes de cenário.
- Notas operacionais com termos de revisão (`revisar`, `conferir`) devem prevalecer sobre classificações automáticas como `WET_LOAD`.
- Judge Mode da UI deve reutilizar cenários do manifest e `DecisionOrchestrator`; não criar regra de decisão paralela para explicar FIFO vs Pe-Q.I.
- Screenshot do README deve usar `assets/screenshots/pequiflux-ui.png`; manter `docs/writeup_assets/pequiflux-ui.png` sincronizado quando usado em material de submissão.
- Visualizações de fila e heatmap na UI devem usar `queue_diff` e `AuditRecord`; não recriar validação de hard constraints no front-end.
- `queue_diff` deve representar a fila após a chamada: caminhão chamado usa `called` e `position_after=None`; demais itens usam `unchanged`, `shifted` ou `blocked`. Não reintroduzir `recommended/skipped` como estado de fila.
- Toda contribuição de score em `app/domain/ranking.py` deve adicionar `PolicyRule` correspondente em `fired_rules`; não deixar bônus/penalidade só em `reason_details`.
- Faixas de benchmark na UI devem ler `bench/reports`, reutilizar `bench/metrics.py` ou mostrar snapshot explícito do relatório versionado; não criar métrica de comparação paralela.
- O benchmark deve distinguir `raw_fifo` de `fifo_safe`; não chamar a variante operacional `fifo` de FIFO puro em relatório público.
- Validação de cenário/benchmark deve reutilizar `bench.validation.validate_payload`; não importar helpers privados de `app/cli`.
- Relatórios CSV de benchmark devem reutilizar `bench.reporting.render_summary_csv`; não montar CSV manualmente com `",".join(...)`.
- Atalhos de execução devem apontar para Docker/Compose, scripts existentes ou CLIs existentes; não criar novo runner paralelo para demo, teste ou benchmark.
- Caminhos reprodutíveis mínimos devem usar `demo-text`/`ui-text`; não fazer quickstart depender implicitamente do serviço `gemma`.
- Checks públicos devem reutilizar `pytest`, `black`, `app.cli.blueprint_audit` e `app.cli.run_benchmark`; não criar runner paralelo de CI para métricas ou auditoria.
- Finalização de ação humana deve reutilizar `SQLiteStore.save_operator_finalization`; não encadear `save_operator_action`, `save_decision_finalized` e `save_audit_record` com commits separados.
- Novos blocos da UI devem entrar em `app/ui/components/*`, `scenario_loader.py`, `ui_runner.py` ou `styles.py` conforme responsabilidade; não voltar a concentrar carregamento de cenário, orquestração, persistência e renderização em `streamlit_app.py`.
- Renderizadores e helpers compartilhados entre módulos de UI devem ser importados por nomes públicos sem `_`; prefixo `_` fica reservado para helpers internos do próprio arquivo.
- A UI deve obter `DecisionOrchestrator` via `app/ui/ui_runner.py` e `st.cache_resource`; não chamar `build_gemma_adapter()` diretamente em componente ou composição de tela.
- Novas mudanças no fluxo de decisão devem encaixar nas etapas `load_inputs`, `interpret_context`, `validate_and_rank`, `build_payload` ou `persist_and_log`; não voltar a concentrar o pipeline inteiro em `run_decision()`.
- Estados de orquestração só podem mudar por `WorkflowStateMachine.transition_to` ou `WorkflowStateMachine.force_terminal`; não atribuir `current_state` diretamente fora da máquina de estados.
