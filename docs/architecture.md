# Arquitetura do Monólito Modular

Esta é a visão arquitetural oficial do repositório. O código segue o desenho do monólito modular descrito no blueprint, mas adaptado à política atual de fail-closed sem fallback.

## Fronteiras de módulo

- `app/domain/`: modelos, enums, constraints, ranking e policy
- `app/adapters/`: leitura de CSV, documento, nota e estados locais
- `app/gemma/`: adaptador do runtime, prompts, schemas e gateway de tools
- `app/services/`: parsing, classificação, decisão e mensagem final
- `app/orchestration/`: orquestrador, máquina de estados e resolução de verdade
- `app/audit/`: construção do payload auditável
- `app/storage/`: SQLite, JSONL e migrações locais
- `app/ui/`: shell da UI em Streamlit
- `bench/`: execução de variantes e métricas
- `tests/`: verificação unitária, contratual e de fluxo

### 4.3 Responsabilidade de cada módulo

| Módulo | Responsabilidade |
|---|---|
| `ui` | Coletar entradas, renderizar a recomendação, expor ações humanas e mostrar a trilha auditável |
| `orchestration` | Coordenar o fluxo ponta a ponta, aplicar a máquina de estados e encadear os módulos |
| `gemma` | Isolar o runtime do modelo, validar saídas estruturadas e planejar a próxima tool permitida para o `FlowState`; execução continua no `ToolGateway` no fluxo `full` |
| `adapters` | Ler CSV, ticket, nota e estados locais, convertendo tudo para objetos canônicos |
| `domain` | Definir modelos, enums, regras duras, ranking, política e erros formais |
| `services` | Implementar parsing, classificação de exceção, composição da decisão e mensagem ao motorista |
| `audit` | Montar o payload auditável e preservar proveniência, rejeições e justificativas |
| `storage` | Persistir decisões e auditoria localmente em SQLite e JSONL |
| `bench` | Executar cenários, variantes e métricas para benchmark reproduzível |
| `tests` | Cobrir regras, contratos, integrações, falhas induzidas e comportamento fail-closed |

## Fluxo ponta a ponta

1. `adapters/*` convertem entradas brutas em `DecisionRequest` e artefatos canônicos.
2. `csv_adapter.normalize_queue_snapshot` fixa FIFO, IDs e tempos de espera.
3. `services.parser` chama `gemma.adapter` para obter `ParsedTicket`.
4. `services.exception_classifier` classifica a exceção operacional primária e acumula exceções secundárias/recursos afetados.
5. `orchestration.truth_resolver` aplica a hierarquia de verdade e materializa conflitos.
6. `domain.constraints.validate_hard_constraints` produz a matriz de elegibilidade.
   No variant `full`, esta etapa é solicitada pelo Gemma Tool Planner e executada pelo `ToolGateway`; em `fifo`/`heuristic`, é chamada diretamente.
7. `domain.ranking.rank_candidates` ordena somente pares elegíveis.
   No variant `full`, esta etapa é solicitada pelo Gemma Tool Planner e executada pelo `ToolGateway`; em `fifo`/`heuristic`, é chamada diretamente.
8. `services.decision_builder` monta `DecisionPreview` e `FrontEndPayload`.
   O builder permanece determinístico; ele consome apenas artefatos formais produzidos pelas etapas anteriores.
9. `audit.service` gera o payload reconstruível.
   No variant `full`, `generate_audit_payload` é solicitada pelo Gemma Tool Planner em `RANKED`/`REVIEW_REQUIRED` e executada pelo `ToolGateway`; em `fifo`/`heuristic` e bloqueios terminais fail-closed, a auditoria é gerada diretamente.
10. `storage/*` persiste decisão, auditoria e ação humana.

## Máquina de estados

Fluxo nominal:

`RECEIVED -> NORMALIZED -> PARSED -> INTERPRETED -> VALIDATED -> RANKED -> PREVIEW_READY -> HUMAN_FINALIZED`

Estados alternativos:

- `REVIEW_REQUIRED`
- `BLOCKED`
- `ERROR_TERMINAL`

Regras centrais:

- o fluxo nunca pula `VALIDATED`;
- `PREVIEW_READY` só existe com par elegível e auditoria gerável;
- `override` inválido não altera o preview;
- falha de contexto ou de runtime gera bloqueio formal ou revisão, nunca degradação.

## Persistência e observabilidade

Persistência local mínima:

- `decision_records`
- `audit_records`
- `operator_actions`
- `benchmark_runs`
- `artifact_index`

`app.orchestration.factory.build_decision_orchestrator()` configura persistência local por ponto de entrada. Quando `enable_storage=True`, injeta `SQLiteStore` usando `PEQUIFLUX_SQLITE_PATH` ou `var/db/pequiflux.db`; quando `enable_logging=True`, injeta `JsonlLogger` usando `PEQUIFLUX_JSONL_LOG_PATH` ou `logs/events.jsonl`.

O benchmark permanece arquivo-only por padrão: `app.cli.run_benchmark` grava `metrics.json`, `per_scenario.json` e `summary.csv` no diretório de saída, sem exigir SQLite.

Os logs em JSONL devem registrar request, cenário, módulo, evento, latências e status, sem persistir prompt cru, chain-of-thought ou documento bruto.

## Testabilidade

- unitário: hard constraints, ranking, tie-break e truth resolver
- contract: schemas e serialização Pydantic
- integration/e2e: fluxo com SQLite, JSONL e payload final
- failure: documento ilegível, conflito material, tool call inválida

## Guardrails

- decision safety is fail-closed
- não há fallback operacional
- o modelo não muta estado autoritativo
- ranking só enxerga pares já validados
- a UI consome um payload único e não infere segurança por conta própria
