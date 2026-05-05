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
- Policy profile: reutilizar `app/domain/policy.py` e `scenarios/common/policy_profile.json`.
- Resolução de verdade entre ticket, nota e estado: reutilizar `app/orchestration/truth_resolver.py`.
- Transições e estados terminais: reutilizar `app/orchestration/state_machine.py`.
- Construção de payload/decisão: reutilizar `app/services/decision_builder.py`.
- Finalização terminal com driver message, payload, persistência e log: reutilizar `DecisionOrchestrator._finalize_payload`.
- Gateway e contrato LLM: reutilizar `app/gemma/*`.
- Métricas de benchmark: reutilizar `bench/metrics.py`.

## Regras adicionadas

- Não criar fallback model, fallback heuristic, retry silencioso ou substituição automática de dependência.
- Não colocar regra de domínio em `app/ui` ou `app/cli`; chamar orquestração/domínio existente.
- Não criar novo parser de ticket sem verificar `app/services/parser.py`, `app/services/structured_ticket_parser.py` e `app/adapters/document_adapter.py`.
- Não criar novo formato de cenário sem atualizar `scenarios/manifest.json`, schemas e testes de cenário.
- Notas operacionais com termos de revisão (`revisar`, `conferir`) devem prevalecer sobre classificações automáticas como `WET_LOAD`.
- Judge Mode da UI deve reutilizar cenários do manifest e `DecisionOrchestrator`; não criar regra de decisão paralela para explicar FIFO vs Pe-Q.I.
- Visualizações de fila e heatmap na UI devem usar `queue_diff` e `AuditRecord`; não recriar validação de hard constraints no front-end.
- Faixas de benchmark na UI devem ler `bench/reports`, reutilizar `bench/metrics.py` ou mostrar snapshot explícito do relatório versionado; não criar métrica de comparação paralela.
- Atalhos de execução devem apontar para Docker/Compose, scripts existentes ou CLIs existentes; não criar novo runner paralelo para demo, teste ou benchmark.
