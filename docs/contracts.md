# Contratos

Os modelos centrais vivem em [`app/domain/models.py`](../app/domain/models.py). Os schemas versionados do pack e do front-end vivem em [`scenarios/schemas/`](../scenarios/schemas/).

## Payloads principais

### `DecisionRequest`

Define a entrada formal do fluxo:

- identificadores de request e cenário
- variante (`fifo`, `heuristic`, `full`)
- referências da fila e do ticket
- nota do operador
- clima e recurso
- versão da policy
- modo de execução

Referências:

- [`app/domain/models.py`](../app/domain/models.py)
- [`scenarios/schemas/DecisionRequest.schema.json`](../scenarios/schemas/DecisionRequest.schema.json)

### `InterpretedContext`

Consolida:

- `ParsedTicket`
- `ExceptionAssessment`
- resolução de verdade
- proveniência
- necessidade de revisão

Referências:

- [`app/orchestration/truth_resolver.py`](../app/orchestration/truth_resolver.py)
- [`scenarios/schemas/InterpretedContext.schema.json`](../scenarios/schemas/InterpretedContext.schema.json)

### `ValidationResult`

Representa a matriz de elegibilidade caminhão-destino com falhas explícitas por constraint.

Referências:

- [`app/domain/constraints.py`](../app/domain/constraints.py)
- [`scenarios/schemas/ValidationMatrix.schema.json`](../scenarios/schemas/ValidationMatrix.schema.json)

### `AuditRecord`

Registra:

- constraints avaliadas
- regras disparadas
- candidatos rejeitados
- par recomendado
- proveniência
- hashes de origem
- latências

Referência:

- [`app/audit/payloads.py`](../app/audit/payloads.py)

### `FrontEndPayload`

É o payload único consumido pela UI:

- status da decisão
- recomendação
- restrições consideradas
- resumo e detalhes da razão
- mensagem ao motorista
- ações humanas permitidas
- trilha auditável visível

Referências:

- [`app/services/decision_builder.py`](../app/services/decision_builder.py)
- [`scenarios/schemas/FrontEndPayload.schema.json`](../scenarios/schemas/FrontEndPayload.schema.json)

## Funções centrais

| Função | Papel |
|---|---|
| `normalize_queue_snapshot` | normalizar a fila e fixar FIFO |
| `parse_ticket_document` | obter `ParsedTicket` via Gemma sob contrato |
| `classify_exception` | produzir `ExceptionAssessment` |
| `resolve_truth` | aplicar a hierarquia de verdade |
| `validate_hard_constraints` | calcular elegibilidade por código puro |
| `rank_candidates` | ordenar somente pares elegíveis |
| `generate_audit_payload` | montar trilha reconstruível |
| `compose_driver_message` | gerar mensagem curta e segura |

## Regra de contrato

- output estruturado ou erro formal;
- nenhuma função central altera estado autoritativo por efeito colateral;
- dado ausente ou inválido nunca vira default silencioso.

