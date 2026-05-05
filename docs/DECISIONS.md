# DECISIONS

Registrar apenas decisões duráveis. Este arquivo não é changelog.

## Decisões

### 2026-05-05 — Benchmark usa validação e relatório públicos

Contexto:
`run_benchmark.py` importava `_validate_payload` de `run_scenario.py`, acoplando benchmark a helper privado do CLI. O `summary.csv` também era montado com `",".join(...)`, quebrando campos com vírgula.

Decisão:
Mover validação para `bench.validation.validate_payload` e renderização CSV para `bench.reporting.render_summary_csv` com `csv.DictWriter`.

Alternativas rejeitadas:
Manter função privada em CLI ou escapar CSV manualmente.

Impacto:
`run_scenario`, `run_benchmark` e testes usam contrato público compartilhado; `summary.csv` fica robusto para erros, justificativas e mensagens com vírgula.

Arquivos/módulos afetados:
- `app/cli/run_benchmark.py`
- `app/cli/run_scenario.py`
- `bench/validation.py`
- `bench/reporting.py`

### 2026-05-05 — Runtime textual não depende de frase do prompt

Contexto:
`TextTicketRuntime` extraía fixtures procurando a frase `Extracted text, if available:` no prompt. Isso acoplava benchmark/testes ao wording usado para o modelo.

Decisão:
Passar `extracted_text` por metadata do runtime e reutilizar `parse_structured_ticket_text` como parser determinístico de fixture.

Alternativas rejeitadas:
Manter parsing por marcador textual no prompt ou duplicar o parser dentro do runtime fake.

Impacto:
Prompts podem ser ajustados para o modelo sem quebrar fixtures `text/plain`; testes e benchmark continuam usando o contrato estruturado.

Arquivos/módulos afetados:
- `app/gemma/adapter.py`
- `app/gemma/text_runtime.py`
- `app/services/structured_ticket_parser.py`
- `tests/unit/test_gemma_adapter.py`

### 2026-05-05 — Timestamps da fila são timezone-aware e normalizados para UTC

Contexto:
`load_queue_rows()` usava `datetime.fromisoformat()` diretamente. Datas inválidas escapavam como `ValueError` e timestamps sem timezone podiam quebrar a subtração em `normalize_queue_snapshot()` quando `reference_time` era aware.

Decisão:
Rejeitar `arrival_ts` inválido ou sem timezone com `PequiFluxError` explícito e normalizar todos os timestamps aceitos para UTC.

Alternativas rejeitadas:
Assumir timezone local ou aceitar timestamp naive silenciosamente.

Impacto:
Fixtures e inputs interativos precisam fornecer ISO-8601 com offset, por exemplo `2026-04-04T08:00:00+00:00`.

Arquivos/módulos afetados:
- `app/adapters/csv_adapter.py`
- `tests/unit/test_csv_adapter.py`
- `docs/contracts.md`
- `docs/scenario-pack.md`

### 2026-05-05 — IDs de política centralizados em `PolicyRule`

Contexto:
O ranking emitia `PR-03` para ajuste de destino por exceção ativa e `PR-05` para penalidade de capacidade, enquanto blueprint e docs definem `PR-03` como penalidade por capacidade reduzida e `PR-05` como bloqueio por ausência de par válido.

Decisão:
Criar `PolicyRule` em `app/domain/enums.py` como fonte única dos IDs `PR-01`..`PR-05` e usar o enum no ranking, no bloqueio por ausência de candidato e nos testes.

Alternativas rejeitadas:
Manter IDs de política como strings soltas espalhadas pelo domínio.

Impacto:
Auditoria, UI e testes passam a consumir os mesmos IDs documentados; `resource_fit` continua como peso de score do perfil `A-05`, mas não reutiliza `PR-03`.

Arquivos/módulos afetados:
- `app/domain/enums.py`
- `app/domain/ranking.py`
- `app/services/decision_builder.py`
- `app/orchestration/orchestrator.py`
- `tests/unit/test_ranking.py`
- `tests/unit/test_policy_profiles.py`

### 2026-05-05 — `queue_diff` representa fila pós-chamada

Contexto:
O diff antigo marcava o caminhão selecionado como posição 1 e removia semanticamente caminhões acima dele, gerando uma fila depois da decisão impossível em que a chamada parecia promoção artificial.

Decisão:
Modelar `queue_diff` como estado pós-chamada: `called` para o caminhão que sai da fila com `position_after=None`; `unchanged` para quem permanece na mesma posição; `shifted` para quem avança após a saída; `blocked` para quem fica aguardando por restrição dura.

Alternativas rejeitadas:
Manter `recommended/skipped` como estados de fila operacional.

Impacto:
UI e auditoria passam a falar a mesma linguagem operacional da fila, sem simular uma posição 1 para caminhão já chamado.

Arquivos/módulos afetados:
- `app/services/decision_builder.py`
- `app/ui/components/common.py`
- `app/ui/components/decision_card.py`
- `tests/unit/test_queue_diff.py`

### 2026-05-05 — Orquestrador como pipeline nomeado

Contexto:
`DecisionOrchestrator.run_decision()` concentrava carregamento de entradas, parsing, classificação, resolução de verdade, validação, ranking, preview, auditoria, persistência e logging.

Decisão:
Manter `run_decision()` como fachada pública e dividir o fluxo em etapas internas nomeadas: `load_inputs`, `interpret_context`, `validate_and_rank`, `build_payload` e `persist_and_log`.

Alternativas rejeitadas:
Mover regras de domínio para a UI/CLI ou criar um segundo runner paralelo para demo.

Impacto:
Novas regras de decisão continuam em domínio/serviços existentes; o orquestrador apenas coordena etapas testáveis e preserva finalização auditável comum.

Arquivos/módulos afetados:
- `app/orchestration/orchestrator.py`
- `docs/CODEMAP.md`
- `docs/SURFACE_MAP.md`
- `docs/DUPLICATION_GUARD.md`

### 2026-05-05 — UI Streamlit dividida por responsabilidade

Contexto:
`app/ui/streamlit_app.py` concentrava carregamento de cenário, preparação de arquivos temporários, montagem de `DecisionRequest`, execução do orquestrador, renderização visual, ação humana e persistência SQLite.

Decisão:
Manter `streamlit_app.py` como composição da tela e dividir responsabilidades em `scenario_loader.py`, `ui_runner.py`, `components/decision_card.py`, `components/validation_matrix.py`, `components/audit_panel.py` e `styles.py`.

Alternativas rejeitadas:
Continuar adicionando novos blocos no arquivo principal da UI.

Impacto:
Novas telas ou blocos reutilizáveis da UI devem entrar no módulo correspondente, sem duplicar regra de domínio nem instanciar orquestrador fora de `ui_runner.py`.

Arquivos/módulos afetados:
- `app/ui/streamlit_app.py`
- `app/ui/scenario_loader.py`
- `app/ui/ui_runner.py`
- `app/ui/components`
- `app/ui/styles.py`

### 2026-05-05 — Infraestrutura de agente versionada

Contexto:
O repositório já continha implementação Python e documentação de produto/arquitetura, mas não continha os mapas vivos exigidos pelo protocolo global de engenharia.

Decisão:
Manter `docs/CODEMAP.md`, `docs/SURFACE_MAP.md`, `docs/DUPLICATION_GUARD.md` e `docs/SETUP_STATUS.md` como documentação viva para orientar alterações futuras, evitar duplicação e registrar pendências de ferramenta.

Alternativas rejeitadas:
Depender apenas do blueprint técnico e do README para orientar mudanças de código.

Impacto:
Mudanças em módulos, contratos públicos, regras reutilizáveis ou decisões duráveis devem atualizar a documentação afetada no mesmo diff.

Arquivos/módulos afetados:
- `docs/CODEMAP.md`
- `docs/SURFACE_MAP.md`
- `docs/DUPLICATION_GUARD.md`
- `docs/SETUP_STATUS.md`

### 2026-05-05 — Estados terminais sempre auditáveis

Contexto:
Os caminhos `PREVIEW_READY`, `REVIEW_REQUIRED` e `BLOCKED` montavam payload, mensagem, persistência e log em fluxos separados, e caminhos de revisão/bloqueio podiam sair sem registro auditável persistido.

Decisão:
Centralizar a finalização terminal no orquestrador e exigir payload de auditoria também para revisão e bloqueio explícitos.

Alternativas rejeitadas:
Manter auditoria apenas para decisões automáticas prontas para preview.

Impacto:
Novos estados terminais devem passar por `DecisionOrchestrator._finalize_payload`.

Arquivos/módulos afetados:
- `app/orchestration/orchestrator.py`
- `app/audit`
- `app/storage`

### 2026-05-05 — Indicação humana de revisão prevalece sobre classificação automática

Contexto:
Notas operacionais com termos como `conferir` e `revisar` representam pedido explícito de revisão humana, mas podiam ser ignoradas quando o ticket também indicava carga úmida.

Decisão:
Classificar indicação humana de revisão antes de classificações automáticas como `WET_LOAD`.

Alternativas rejeitadas:
Permitir decisão automática quando a nota operacional pede conferência manual.

Impacto:
Cenários com `operator_note` pedindo conferência retornam `REVIEW_REQUIRED` até que a revisão seja resolvida.

Arquivos/módulos afetados:
- `app/services/exception_classifier.py`
- `scenarios/cases/S03_WET_LOAD/expected_decision.json`
