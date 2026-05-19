# DECISIONS

Registrar apenas decisões duráveis. Este arquivo não é changelog.

## Decisões

### 2026-05-06 — Sample público inclui contrato de Gemma Tool Planner

Contexto:
O variant `full` passou a usar Gemma Tool Planner sob `ToolGateway`, mas o snapshot público ainda mostrava apenas métricas clássicas de decisão, constraints, exceção, acurácia e latência. Isso enfraquecia a evidência versionada da tese de tools.

Decisão:
Regenerar `bench/reports/sample/` com o mesmo pack congelado de 20 cenários, adicionando colunas de tool calling no `summary.csv` e métricas agregadas no `metrics.json`. Manter o bloqueio do CLI contra escrita direta em `bench/reports/sample/`; novas regenerações devem continuar passando por diretório temporário ou `extended-sample` e revisão explícita.

Alternativas rejeitadas:
Deixar a prova de tools apenas na UI e em runs `extended`, mantendo o sample público sem o novo contrato.

Impacto:
A evidência pública passa a mostrar `tool_call_success_rate`, médias de calls/steps, erros e `tool_path` por linha, sem expandir o scenario pack congelado.

Arquivos/módulos afetados:
- `bench/metrics.py`
- `bench/reports/sample/`
- `tests/unit/test_public_sample_consistency.py`
- `README.md`

### 2026-05-05 — Benchmark público congelado e trilho extended interno

Contexto:
O sample público do benchmark cresceu para 20 cenários e já cobre a tese principal da submissão. Continuar expandindo esse mesmo snapshot aumentaria o peso da página pública e misturaria evidência de submissão com exploração interna.

Decisão:
Congelar `bench/reports/sample/` como snapshot público de 20 cenários usado por README, CI e evidência versionada. Fazer execuções normais de benchmark escreverem em `bench/reports/extended/<run_id>/` por padrão e tratar esse trilho como espaço de desenvolvimento interno. O CLI de benchmark deve recusar `bench/reports/sample/` como `--output-dir`; novos snapshots de teste devem ir para `bench/reports/extended-sample/<run_id>` ou diretório temporário local.

Alternativas rejeitadas:
Continuar publicando todo crescimento em `sample/` ou manter novos runs diretamente em `bench/reports/<run_id>/` sem separar o contrato público do trilho exploratório.

Impacto:
A superfície pública fica estável e leve, enquanto o benchmark interno pode crescer sem alterar o contrato validado pelo teste de consistência do sample.

Arquivos/módulos afetados:
- `app/cli/run_benchmark.py`
- `tests/unit/test_public_sample_consistency.py`
- `README.md`
- `docs`

### 2026-05-05 — Catálogo humano do scenario pack fica em `scenarios/README.md`

Contexto:
O repositório passou a repetir a lista completa de cenários no `README.md`, em `docs/scenario-pack.md` e em `scenarios/README.md`. Isso aumenta drift documental toda vez que o pack cresce.

Decisão:
Tratar `scenarios/README.md` como catálogo humano canônico do scenario pack. Manter `README.md` como resumo público curto e `docs/scenario-pack.md` focado em estrutura, contratos e integridade.

Alternativas rejeitadas:
Repetir a tabela/lista completa em múltiplos docs ou mover a descrição humana caso a caso para o `README.md`, inflando a superfície pública principal.

Impacto:
O pack pode evoluir sem exigir sincronização manual de uma lista completa em mais de um documento.

Arquivos/módulos afetados:
- `README.md`
- `scenarios/README.md`
- `docs/scenario-pack.md`
- `docs`

### 2026-05-05 — Blueprint canônico fica na raiz

Contexto:
O repositório mantinha `technical_blueprint.md` e `docs/technical_blueprint.md` como documentos longos. Isso já produzia diferença entre os arquivos e criava risco permanente de drift em uma superfície pública da submissão.

Decisão:
Manter `technical_blueprint.md` na raiz como fonte canônica longa. Transformar `docs/technical_blueprint.md` em ponte curta para a fonte canônica e fazer `app.cli.blueprint_audit` validar que a ponte continua curta e aponta para `../technical_blueprint.md`.

Alternativas rejeitadas:
Manter duas cópias longas sincronizadas manualmente ou mover a fonte canônica para `docs/` agora, o que exigiria ajustar o caminho já usado por Docker/CI e README sem ganho prático.

Impacto:
Reduz drift documental e preserva compatibilidade com a imagem Docker e o audit existente.

Arquivos/módulos afetados:
- `technical_blueprint.md`
- `docs/technical_blueprint.md`
- `app/cli/blueprint_audit.py`
- `README.md`
- `docs`

### 2026-05-05 — Audit completeness é status-aware

Contexto:
Casos `BLOCKED` e `REVIEW_REQUIRED` corretos podem parar antes da matriz de validação, mas ainda precisam ser auditáveis. Exigir `hard_constraints_checked` para todos os status subestimava `audit_completeness` no sample.

Decisão:
Manter matriz de validação obrigatória para `PREVIEW_READY`. Para `BLOCKED` e `REVIEW_REQUIRED`, considerar a auditoria completa quando houver razão terminal, status, contexto observado, proveniência, hashes de `queue_csv_ref`, `ticket_ref`, `operator_note`, `weather_state` e `resource_state`, e audit record coerente.

Alternativas rejeitadas:
Forçar matriz vazia ou artificial em estados terminais apenas para satisfazer métrica agregada.

Impacto:
A métrica passa a medir auditabilidade real por tipo de estado sem mascarar ausência de validação em previews automáticos.

Atualização 2026-05-06:
Essa rigidez é intencional para payloads que entram no benchmark comparativo. `audit_completeness` não é um indicador universal de toda falha catastrófica: falhas antes da ingestão completa, como arquivo ausente antes da interpretação, podem não ter latências, proveniência ou hashes completos. Nesses casos o requisito é falhar fechado com erro explícito, não manter `audit_completeness = 1.0`.

Arquivos/módulos afetados:
- `bench/rows.py`
- `tests/unit/test_benchmark_rows.py`
- `bench/reports/sample`
- `docs`

### 2026-05-05 — FIFO bruto fora da matriz é inválido no benchmark

Contexto:
`raw_fifo` não aplica hard constraints, mas o benchmark ainda precisa diferenciar par bruto elegível de par bruto impossível. Quando o destino declarado na fila não existe em `resource_state`, o par não aparece na matriz de validação e não deve ser contado como sem violação.

Decisão:
Em `bench.rows.pair_rejected`, considerar violação quando o par caminhão-destino informado pelo FIFO bruto não aparece em `audit_record.hard_constraints_checked`. Pares sem destino continuam como chamada FIFO incompleta/review, não como violação material.

Alternativas rejeitadas:
Classificar destino desconhecido como não violação por ausência de rejeição explícita em `rejected_candidates`.

Impacto:
S15 passa a exercitar FIFO bruto com destino inexistente, e o benchmark marca essa chamada como inválida/violação.

Arquivos/módulos afetados:
- `bench/rows.py`
- `tests/unit/test_benchmark_rows.py`
- `scenarios/cases/S15_UNKNOWN_DESTINATION_IN_TICKET/queue.csv`

### 2026-05-05 — Scenario Pack consolida S01-S20 como vitrine

Contexto:
O sample já tinha um caso multimodal (`S03_WET_LOAD`), mas a tese de valor do Gemma fica mais forte quando o benchmark cobre variações multimodais, conflitos de verdade e invariantes operacionais.

Decisão:
Consolidar S01-S20 no mesmo `scenarios/manifest.json` como pack público congelado. S17/S18 também têm testes unitários de governança de override, porque a validade final do override acontece após o preview.

Alternativas rejeitadas:
Criar um manifest paralelo de robustez ou tratar override como fixture de benchmark sem o fluxo de finalização do operador.

Impacto:
O benchmark passa a exercitar imagem rotacionada, PDF escaneado, conflitos entre documento/fila/nota/estado local, ausência de par elegível, override governado, desempate determinístico e fila com 100 caminhões sem alterar o contrato público de cenário.

Adendo 2026-05-06:
O pack principal em `scenarios/cases/` fica congelado em S01-S20 como vitrine pública. Novos casos devem ir para `scenarios/extended/stress/` ou `scenarios/extended/failure/` e não devem ser adicionados ao `scenarios/manifest.json` principal sem decisão explícita de mudar o contrato público.

Arquivos/módulos afetados:
- `scenarios/manifest.json`
- `scenarios/cases/S11_*`..`S20_*`
- `scenarios/extended/`
- `tests/scenarios`
- `tests/unit/test_operator_governance.py`
- `docs`

### 2026-05-05 — CI público usa runtime textual e quality gate mínimo

Contexto:
O repositório não tinha workflow GitHub Actions visível, então pushes públicos não retornavam status checks. A trilha completa com Gemma/Ollama exige serviço externo/modelo, mas a avaliação precisa de um caminho CI reprodutível. Depois que o Gemma Tool Planner virou claim central, o benchmark sem validação deixou de ser suficiente para o quality gate público.

Decisão:
Adicionar `.github/workflows/ci.yml` com Python 3.11, instalação de `requirements-all.txt`, `black --check app bench tests scripts`, `pytest -q`, `python -m app.cli.blueprint_audit` e benchmark textual validado com `PEQUIFLUX_GEMMA_RUNTIME=text`, sem `--no-validate`. Fazer `make check` incluir Black, testes, auditoria e o mesmo benchmark validado.

Alternativas rejeitadas:
Rodar `black --check .`, porque isso inclui documentação, assets e artefatos fora do escopo Python. Rodar benchmark via Ollama no CI, porque introduziria dependência de GPU/modelo.

Impacto:
GitHub passa a mostrar status checks úteis em push/PR sem depender de GPU. O endurecimento para Black no repositório inteiro fica separado de uma mudança futura puramente mecânica.

Arquivos/módulos afetados:
- `.github/workflows/ci.yml`
- `Makefile`
- `scripts/check-quality.sh`
- `docs`

### 2026-05-05 — Quickstart usa runtime textual sem depender de Ollama

Contexto:
O quickstart indicava `docker run --rm pequiflux-yard-copilot:local`, mas o runtime padrão da aplicação procurava Ollama em `http://gemma:11434`. Em um `docker run` isolado esse host não existe, e o caminho Compose completo também depende do serviço `gemma` com `gpus: all`.

Decisão:
Definir `PEQUIFLUX_GEMMA_RUNTIME=text` na imagem Docker standalone e adicionar serviços/atalhos `demo-text` e `ui-text` sem `depends_on: gemma`. Manter `demo`, `ui` e `benchmark` como modo completo Ollama/Gemma.

Alternativas rejeitadas:
Remover o modo Ollama do Compose ou alterar o default global do código para `text`, o que tornaria menos explícita a diferença entre runtime mínimo e runtime completo.

Impacto:
Avaliadores sem GPU/modelo local conseguem rodar CLI e UI antes do setup de Gemma, enquanto a trilha completa continua disponível para demonstrar parsing multimodal real.

Arquivos/módulos afetados:
- `Dockerfile`
- `compose.yaml`
- `Makefile`
- `README.md`
- `docs/docker.md`
- `docs/gemma.md`

### 2026-05-05 — Benchmark separa `raw_fifo` de `fifo_safe`

Contexto:
A variante operacional `fifo` ainda passa por `validate_hard_constraints`, então ela não representa FIFO puro. O README misturava essa linha com a comparação simplificada, enquanto a UI já mostrava separadamente o "FIFO chamaria" pela fila bruta.

Decisão:
Manter o contrato interno `DecisionVariant="fifo"` por compatibilidade, mas reportar essa saída no benchmark como `fifo_safe`. Adicionar uma linha `raw_fifo` calculada por `app.services.raw_fifo`, sem hard constraints, para a comparação narrativa de FIFO puro.

Alternativas rejeitadas:
Renomear o enum `fifo` para `fifo_safe`, o que exigiria migração de schema, UI, fixtures e payloads sem alterar a decisão operacional.

Impacto:
O relatório público passa a distinguir FIFO bruto de FIFO seguro entre pares elegíveis, e a UI reutiliza a mesma fonte de FIFO bruto que o benchmark.

Arquivos/módulos afetados:
- `app/cli/run_benchmark.py`
- `app/services/raw_fifo.py`
- `app/ui/components/common.py`
- `bench/reports/sample`
- `README.md`
- `docs`

### 2026-05-05 — Benchmark multimodal usa `expected_ticket.json` como sidecar canônico

Contexto:
O sample versionado do benchmark empatava `full` e `heuristic` nas métricas principais porque todos os tickets do pack eram legíveis como `text/plain`. Assim, a submissão não provava valor real da leitura multimodal do Gemma.

Decisão:
Converter `S03_WET_LOAD` para ticket em imagem e adotar `expected_ticket.json` no mesmo diretório do caso como sidecar canônico para benchmark/CI. O runtime real continua lendo a imagem; o sidecar só fixa o ticket esperado para `run_benchmark.py`, `TextTicketRuntime` e testes sem Ollama/GPU.

Alternativas rejeitadas:
Criar um segundo manifest só para benchmark, manter tickets multimodais fora do pack principal ou introduzir um formato paralelo de fixture esperado.

Impacto:
O relatório sample passa a mostrar delta observável entre `full` e `heuristic` em `ticket_field_accuracy`, `exception_f1` e `decision_match_at_1` sem quebrar o fail-closed do baseline textual.

Arquivos/módulos afetados:
- `scenarios/cases/S03_WET_LOAD`
- `scenarios/manifest.json`
- `app/services/structured_ticket_parser.py`
- `app/gemma/text_runtime.py`
- `app/cli/run_benchmark.py`
- `tests/scenarios`
- `tests/unit`

### 2026-05-05 — Componentes da UI expõem renderizadores públicos

Contexto:
`streamlit_app.py` importava renderizadores de componentes com prefixo `_`, e parte dos helpers compartilhados de `components/common.py` também era importada como se fosse privada. A demo funcionava, mas a superfície parecia menos madura para avaliação pública.

Decisão:
Renomear renderizadores e helpers compartilhados de UI para nomes públicos sem underscore e reservar `_` para funções internas ao próprio módulo. Adicionar Black ao ambiente dev e ao check de qualidade.

Alternativas rejeitadas:
Manter imports privados apenas por convenção local ou criar novos wrappers duplicados para preservar os nomes antigos.

Impacto:
`streamlit_app.py` fica mais limpo como composição de tela, componentes têm superfície reutilizável explícita e `scripts/check-quality.sh` passa a validar formatação.

Arquivos/módulos afetados:
- `app/ui/streamlit_app.py`
- `app/ui/components`
- `pyproject.toml`
- `scripts/check-quality.sh`

### 2026-05-05 — Resource fit vira regra auditável `PR-06`

Contexto:
O ranking somava `policy_profile.weights.resource_fit` quando o destino aparecia em `exception_assessment.affected_resources`, mas registrava apenas `reason_details`. A pontuação influenciava a decisão sem aparecer como regra disparada.

Decisão:
Adicionar `PolicyRule.RESOURCE_FIT = "PR-06"` e dispará-la no ranking completo quando o bônus de aderência ao recurso for aplicado.

Alternativas rejeitadas:
Reorganizar IDs `PR-01`..`PR-05`, o que quebraria contratos, cenários e documentação já publicados.

Impacto:
Toda contribuição de score relevante passa a ter regra auditável em `fired_rules`; auditoria e UI enxergam o bônus de recurso como política explícita.

Arquivos/módulos afetados:
- `app/domain/enums.py`
- `app/domain/ranking.py`
- `tests/unit/test_ranking.py`

### 2026-05-05 — Bloqueio por erro usa terminal controlado da state machine

Contexto:
`DecisionOrchestrator._build_blocked_payload()` ainda atribuía `state_machine.current_state = FlowState.BLOCKED` diretamente, desviando do contrato da máquina de estados.

Decisão:
Adicionar `WorkflowStateMachine.force_terminal(terminal_state, reason=...)` para terminais excepcionais controlados e usar esse método no caminho de erro do orquestrador.

Alternativas rejeitadas:
Permitir qualquer terminal em `transition_to` ou manter atribuição direta no orquestrador.

Impacto:
Transições normais continuam restritas por `transition_to`; bloqueios fail-closed registram motivo e não burlam a máquina de estados.

Arquivos/módulos afetados:
- `app/orchestration/state_machine.py`
- `app/orchestration/orchestrator.py`
- `tests/unit/test_state_machine.py`

### 2026-05-05 — Screenshot canonico mostra a prova FIFO vs Pe-Q.I

Contexto:
O README ja exibia imagem da UI, mas apontava para `docs/writeup_assets/pequiflux-ui.png`. Para avaliacao, o artefato canonico versionado fica em `assets/screenshots/pequiflux-ui.png`.

Decisão:
Fazer o README embutir `assets/screenshots/pequiflux-ui.png`, manter o asset de writeup sincronizado e trazer a comparacao `FIFO chamaria` versus `Pe-Q.I recomenda` antes da fila nos resultados. A UI tambem aceita `PEQUIFLUX_UI_AUTORUN=1` para capturas de demo.

Alternativas rejeitadas:
Adicionar uma segunda imagem no README ou deixar o screenshot principal apontando para caminho secundario.

Impacto:
A primeira imagem do GitHub fica alinhada ao asset de evidencia da submissao e privilegia o conflito de legitimidade da decisao.

Arquivos/módulos afetados:
- `README.md`
- `app/ui/streamlit_app.py`
- `app/ui/styles.py`

### 2026-05-05 — Finalização humana é persistida em transação única

Contexto:
`finalize_operator_decision()` gravava ação do operador, decisão finalizada e auditoria atualizada por chamadas separadas do `SQLiteStore`, cada uma com seu próprio commit. Uma falha no meio podia deixar estado parcial.

Decisão:
Adicionar `SQLiteStore.save_operator_finalization()` para gravar os três efeitos em uma única transação SQLite e chamar esse método na governança do operador.

Alternativas rejeitadas:
Manter commits separados ou mover transação para a UI.

Impacto:
Finalização humana passa a ser atômica: se a auditoria atualizada falhar, ação e finalização também são revertidas.

Arquivos/módulos afetados:
- `app/storage/sqlite_store.py`
- `app/services/operator_governance.py`
- `tests/unit/test_operator_governance.py`

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
Criar `PolicyRule` em `app/domain/enums.py` como fonte única dos IDs de política e usar o enum no ranking, no bloqueio por ausência de candidato e nos testes.

Alternativas rejeitadas:
Manter IDs de política como strings soltas espalhadas pelo domínio.

Impacto:
Auditoria, UI e testes passam a consumir os mesmos IDs documentados. Esta decisão foi estendida depois por `PR-06 RESOURCE_FIT`, mantendo `resource_fit` como peso do perfil `A-05` com regra auditável própria.

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

### 2026-05-06 — Classificação de exceções acumula sinais combinados

Contexto:
O classificador de exceções retornava na primeira condição encontrada. Isso preservava uma exceção primária, mas escondia exceções reais simultâneas como recurso indisponível, chuva em destino aberto, documento bloqueado, indicação humana de revisão e carga úmida.

Decisão:
Manter a prioridade de `primary_exception`, mas acumular os demais sinais em `secondary_exceptions`, `affected_resources`, `ambiguities` e `needs_human_review`. Quando a classificação contextual via Gemma é usada sem exceção determinística alta, enriquecer a resposta do adapter com sinais determinísticos.

Alternativas rejeitadas:
Substituir `primary_exception` por uma lista sem prioridade ou manter early returns que descartam sinais reais.

Impacto:
Payloads e ranking passam a receber uma visão mais completa do contexto operacional sem alterar o contrato de primária esperado pelo benchmark público.

Atualização 2026-05-06:
Quando `MANUAL_REVIEW_HINT` aparece nos achados acumulados, mesmo como exceção secundária, `needs_human_review` deve ser `true`. Um pedido explícito do operador para revisar ou conferir não pode ficar inerte apenas porque chuva, recurso indisponível ou documento bloqueado mantiveram a prioridade de `primary_exception`.

Arquivos/módulos afetados:
- `app/services/exception_classifier.py`
- `tests/unit/test_exception_classifier.py`
- `docs`

### 2026-05-06 — Tools determinísticas passam pelo ToolGateway

Contexto:
O repositório já tinha `ToolGateway`, mas o fluxo `full` ainda chamava constraints, ranking e auditoria diretamente pelo orquestrador. Isso deixava a documentação de tool calling sem prova operacional no pipeline.

Decisão:
Executar `validate_hard_constraints`, `rank_candidates` e `generate_audit_payload` via `ToolGateway` no fluxo `full`, preservando regras determinísticas, whitelist, ordem por `FlowState`, validação de IDs locais e log estruturado. Em cada etapa, o orquestrador passa uma única tool permitida em `allowed_tools`; Gemma solicita essa tool válida sob contrato, sem escolher livremente entre comandos. `compose_driver_message` permanece serviço determinístico fora da whitelist solicitável pelo modelo.

Alternativas rejeitadas:
Manter o gateway apenas como camada futura ou deixar o modelo decidir hard constraints.

Impacto:
O orquestrador continua sendo a fachada do fluxo, mas as tools críticas do variant `full` agora são executadas por um gateway auditável. Gemma interpreta documentos e ajuda em classificação ambígua; hard constraints e ranking seguem determinísticos.

Arquivos/módulos afetados:
- `app/orchestration/orchestrator.py`
- `app/gemma/tool_gateway.py`
- `docs`

### 2026-05-06 — Gemma Tool Planner sob máquina de estados

Contexto:
O primeiro fluxo com `ToolGateway` passava uma única tool fixa em `allowed_tools` a cada etapa. Isso era seguro, mas limitava a evidência de planejamento do Gemma.

Decisão:
Evoluir o variant `full` para um Gemma Tool Planner. O orquestrador calcula `available_tools_for_state(state)` e o Gemma escolhe a próxima tool válida, fornecendo `purpose`; o `ToolGateway` continua validando whitelist, JSON Schema, `FlowState` e IDs locais. O loop é limitado a 4 tool steps e variants `fifo`/`heuristic` continuam sem `tool_calls`. Estados `BLOCKED` por erro terminal não expõem `generate_audit_payload` ao planner; usam auditoria direta fail-closed.

Atualização 2026-05-06:
A sessão e a execução do planner ficam em `app/orchestration/tool_planner.py` (`ToolPlanSession`, `execute_planned_tool`, plano de validação/ranking e plano de auditoria). `DecisionOrchestrator` permanece a fachada do fluxo, mas só monta callbacks determinísticos, previews, auditoria final, persistência e log.

Impacto:
Hard constraints, ranking e auditoria permanecem determinísticos. O modelo não altera estado autoritativo, não recebe argumentos além de `request_id` e não executa comandos livres.
