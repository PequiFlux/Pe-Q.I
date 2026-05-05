# SURFACE MAP

Mapa da superfície pública/exportada do PequiFlux Yard Copilot.

## Superfície atual

| Símbolo | Tipo | Arquivo | Responsabilidade | Entradas | Saídas | Observações |
|---|---|---|---|---|---|---|
| `app.cli.run_scenario` | CLI module | `app/cli/run_scenario.py` | Executa um cenário sintético | Caminho/ID de cenário | Decisão e payload de execução | Entrada padrão para demo local; valida `required_policy_rules` quando o expected do cenário declarar |
| `app.cli.run_benchmark` | CLI module | `app/cli/run_benchmark.py` | Executa benchmark de cenários | Manifest e fixtures | Métricas/relatório | Usado por Docker/Compose |
| `app.cli.prewarm_gemma` | CLI module | `app/cli/prewarm_gemma.py` | Preaquece runtime Gemma/Ollama | Configuração de runtime | Status de prewarm | Não deve substituir runtime ausente |
| `app.cli.blueprint_audit` | CLI module | `app/cli/blueprint_audit.py` | Audita alinhamento com blueprint | Blueprint/docs | Relatório de auditoria | Apoia checks públicos |
| `app.ui.streamlit_app` | UI module | `app/ui/streamlit_app.py` | Composição da tela Streamlit em Judge Mode | Três cenários narrativos, relatório de benchmark versionado ou inputs técnicos | Tela principal, modo técnico, estado de sessão e ligação entre componentes | Deve permanecer fino; não carregar cenário, rodar orquestrador ou persistir ação diretamente; `PEQUIFLUX_UI_AUTORUN=1` carrega o caso selecionado para captura de screenshot/demo |
| `app.ui.scenario_loader` | UI service module | `app/ui/scenario_loader.py` | Carrega manifest/casos e monta `DecisionRequest` de inputs técnicos | Manifest, fixtures, upload/texto da UI, JSON de clima/recurso | `DecisionRequest` ou erro explícito de entrada | Escreve somente cache de sessão em `cache/ui_sessions`; sem regra de decisão |
| `app.ui.ui_runner` | UI service module | `app/ui/ui_runner.py` | Executa payload principal e baseline FIFO para a UI | `DecisionRequest` | `FrontEndPayload` full e FIFO | Único ponto da UI que instancia `DecisionOrchestrator`; orquestrador cacheado com `st.cache_resource` para evitar reconstruir adapter/runtime a cada rerun do Streamlit |
| `app.ui.components.decision_card` | UI component module | `app/ui/components/decision_card.py` | Renderiza decisão recomendada, FIFO vs Pe-Q.I, fila empilhada e restrições narrativas | `FrontEndPayload`, `DecisionRequest` | HTML seguro para Streamlit | Usa `queue_diff`/audit record; não recalcula regra de domínio |
| `app.ui.components.validation_matrix` | UI component module | `app/ui/components/validation_matrix.py` | Renderiza heatmap de validação de hard constraints | `FrontEndPayload.audit_record` | Componente Streamlit/HTML | Consome `hard_constraints_checked`; não revalida pares |
| `app.ui.components.audit_panel` | UI component module | `app/ui/components/audit_panel.py` | Renderiza auditoria, contexto interpretado, mensagem ao motorista e ação humana | `FrontEndPayload`, `DecisionRequest` | Componentes Streamlit e persistência de ação via governança | Persistência passa por `finalize_operator_decision` e `SQLiteStore` |
| `app.orchestration.orchestrator` | module | `app/orchestration/orchestrator.py` | Coordena fluxo de decisão e finalização auditável | `DecisionRequest`, estados, política | Decisão final/review/error com payload auditável | `run_decision()` delega para `load_inputs`, `interpret_context`, `validate_and_rank`, `build_payload` e `persist_and_log`; estados terminais usam finalização comum |
| `app.orchestration.truth_resolver` | module | `app/orchestration/truth_resolver.py` | Resolve divergências entre fontes | Ticket, nota, estados | Contexto reconciliado | Falhas devem ser explícitas |
| `app.orchestration.state_machine` | module | `app/orchestration/state_machine.py` | Controla estados terminais e transições | Estado atual, evento ou terminal forçado com motivo | Novo estado/erro | Fluxo normal usa `transition_to`; erro terminal controlado usa `force_terminal`, sem atribuição direta fora da máquina |
| `app.domain.constraints` | module | `app/domain/constraints.py` | Aplica hard constraints | Decisão candidata, contexto | Bloqueios/revisões | Não duplicar em serviços/UI |
| `app.domain.ranking` | module | `app/domain/ranking.py` | Ordena e pontua fila | Fila, política, contexto | Ranking | Reutilizar antes de criar scoring paralelo |
| `app.domain.policy` | module | `app/domain/policy.py` | Carrega/aplica perfil de política | Policy profile | Política validada | Alinha scenarios/common |
| `app.domain.enums.PolicyRule` | enum | `app/domain/enums.py` | Fonte única dos IDs `PR-01`..`PR-06` | Regras de política documentadas | IDs usados em ranking/auditoria/UI/testes | Evita desalinhamento entre blueprint, implementação e apresentação |
| `app.services.decision_builder` | module | `app/services/decision_builder.py` | Monta decisão e payload de saída | Resultado de domínio/orquestração | Front-end/audit payload | `queue_diff` usa semântica pós-chamada: `called`, `unchanged`, `shifted`, `blocked`, com `position_after=None` para caminhão chamado |
| `app.gemma.adapter` | module | `app/gemma/adapter.py` | Adapta runtime LLM para contrato do sistema | Prompt/contexto | Contexto interpretado ou erro | Sem fallback silencioso |
| `app.gemma.text_runtime.TextTicketRuntime` | runtime | `app/gemma/text_runtime.py` | Runtime determinístico para fixtures `text/plain` de CI/benchmark | Prompt livre para modelo e `metadata["extracted_text"]` como dado de fixture | `ParsedTicket`/`ExceptionAssessment` | Não parseia texto a partir de frase específica do prompt; reutiliza `parse_structured_ticket_text` |
| `app.gemma.runtime_factory` | module | `app/gemma/runtime_factory.py` | Constrói runtime configurado | Configuração | Runtime | Deve falhar se dependência obrigatória faltar |
| `app.services.structured_ticket_parser.parse_structured_ticket_text` | function | `app/services/structured_ticket_parser.py` | Parser determinístico de tickets textuais sintéticos para benchmark/teste | Texto extraído de fixture | `ParsedTicket` | Fonte reutilizável para variante heurística e `TextTicketRuntime` |
| `app.adapters.document_adapter` | module | `app/adapters/document_adapter.py` | Ingestão de documento/ticket | Arquivo sintético | Dados extraídos | Testes cobrem caminhos de documento |
| `app.adapters.csv_adapter` | module | `app/adapters/csv_adapter.py` | Carrega e normaliza fila CSV | `queue.csv` com `arrival_ts` timezone-aware | `RawQueueRow`/`QueueSnapshot` em UTC | Rejeita data inválida ou timestamp sem timezone com `PequiFluxError` |
| `app.storage.sqlite_store` | module | `app/storage/sqlite_store.py` | Persistência SQLite local | Payloads auditáveis | Registros persistidos | Usar migrations versionadas; finalização do operador deve usar `save_operator_finalization` para gravar ação, finalização e auditoria em uma transação |
| `bench.runner` | module | `bench/runner.py` | Executa suíte de cenários | Manifest/fixtures | Resultados agregados | Usado por Compose benchmark |
| `bench.metrics` | module | `bench/metrics.py` | Calcula métricas de benchmark | Resultados de casos | Métricas | Evitar métrica paralela sem decisão |
| `bench.validation.validate_payload` | function | `bench/validation.py` | Valida payload contra `expected_decision.json` | `FrontEndPayload`, expected de cenário | Sucesso ou `SystemExit` com erros | Reutilizado por `run_scenario`, `run_benchmark` e testes; não importar validação privada de CLI |
| `bench.reporting.render_summary_csv` | function | `bench/reporting.py` | Renderiza `summary.csv` do benchmark | Linhas por cenário/variante | CSV escapado via `csv.DictWriter` | Evita quebra quando mensagem, erro ou exceção contêm vírgula |
| `Makefile` | command surface | `Makefile` | Atalhos avaliáveis para demo, UI, testes, benchmark e auditoria | `make demo`, `make ui`, `make test`, `make bench`, `make audit` | Comandos Docker/Compose | Não substitui scripts existentes; apenas agrega entrada amigável |
| `scripts/check-quality.sh` | script | `scripts/check-quality.sh` | Executa testes, auditoria de blueprint e Sonar opcional | `--sonar`, `SONAR_HOST_URL`, `SONAR_TOKEN` | Status de checks | Usa pytest/python locais quando existem; senão usa Docker |

## Regras

- Atualizar este mapa quando método público/exportado, service, adapter, schema, DTO, endpoint, hook, componente ou contrato mudar.
- Registrar entradas, saídas e efeitos relevantes quando o contrato não for óbvio.
