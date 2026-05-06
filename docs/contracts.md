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

### `PolicyRule`

IDs de política vivem em [`app/domain/enums.py`](../app/domain/enums.py) e devem ser usados em ranking, auditoria, UI e testes:

| Enum | ID | Significado |
|---|---|---|
| `FIFO_DEFAULT` | `PR-01` | FIFO é o padrão |
| `CONTRACT_PRIORITY_MAY_BREAK_FIFO` | `PR-02` | prioridade contratual pode quebrar FIFO entre pares elegíveis |
| `REDUCED_CAPACITY_PENALTY` | `PR-03` | capacidade acima do mínimo e abaixo do conforto penaliza ranking |
| `WAIT_SLA_PRESSURE` | `PR-04` | espera excessiva adiciona pressão limitada de SLA |
| `NO_VALID_PAIR_BLOCKS_AUTODISPATCH` | `PR-05` | ausência de par válido gera `BLOCKED` |
| `RESOURCE_FIT` | `PR-06` | destino alinhado à exceção ativa recebe bônus auditável no ranking completo |

### Detalhes de entrada (`DecisionRequest`)

- `queue_csv_ref`: caminho do arquivo `queue.csv` do cenário.
- `ticket_ref`: caminho/código da evidência documental (PDF, imagem ou texto).
- `ticket_content_type`: exatamente `application/pdf`, `image/png`, `image/jpeg` ou `text/plain`.
- `operator_note`: texto auxiliar do operador (obrigatório).
- `weather_state`: objeto sintético do cenário com precipitação e severidade.
- `resource_state`: lista de recursos com `resource_id`, `status`, `capacity_pct`, `exposure`, `allowed_vehicle_types` e `supported_load_conditions`.
- `variant`: `fifo`, `heuristic` ou `full`.
- `run_mode`: `interactive` ou `benchmark`.
- `policy_profile_version`: versão da política aplicada (ex.: `v1-demo`).
- `request_id` e `scenario_id`: IDs rastreáveis para auditoria.

Regras práticas:

- `ticket_ref` e `ticket_content_type` devem estar presentes sempre que `variant != "fifo"`.
- `operator_note` não pode ser vazio e é sanitizado (`strip` e compressão de espaços).
- valores fora de enumeração (tipos/campos permitidos) devem falhar com erro formal, não virar defaults.

### Camada 1 — ticket bruto (documento de entrada)

No ticket bruto (PDF/imagem, na entrada multimodal), o documento precisa conter evidência suficiente para inferir:

- identificação do ticket;
- identificação do caminhão, quando houver;
- tipo de veículo;
- status documental (claro, bloqueado, incompleto, desconhecido);
- bloqueios documentais explícitos;
- condição da carga (seca/úmida);
- indicador de prioridade contratual;
- restrições de destino, quando houver.

Isso é necessário para cobrir os cenários de submissão com carga úmida, bloqueio documental e prioridade contratual.

### Camada 2 — objeto estruturado (`ParsedTicket`)

O contrato esperado do parser é:

- `ticket_id`
- `truck_id`
- `vehicle_type`
- `document_status`
- `document_block_flags`
- `load_condition`
- `contract_priority_flag`
- `destination_constraints`
- `parse_confidence`
- `ambiguities`
- `evidence_refs`

Campos críticos obrigatórios para cálculo de decisão: `document_status`, `load_condition`, `vehicle_type` e `parse_confidence`.

`parse_confidence`, `ambiguities` e `evidence_refs` são metadados do parser, não precisam existir no ticket bruto.
Quando `parse_confidence` aparece no ticket estruturado textual, ele deve ser numérico; valor inválido falha fechado com `INVALID_STRUCTURED_TICKET_FIELD`.

### O que o ticket deve conter para viabilizar a decisão

Em termos práticos, o ticket para demo precisa ficar legível com:

- qual é o ticket;
- qual caminhão ele representa;
- qual o tipo do veículo;
- se a documentação está liberada, bloqueada ou incompleta;
- se há carimbo/flag de bloqueio;
- se a carga está seca ou úmida;
- se há prioridade contratual;
- se existe alguma restrição de destino.

Observações contratuais:

- em cada cenário com ticket, o parse deve resultar em JSON de `ParsedTicket` válido;
- se o material crítico ficar ambíguo/ilegível (`unknown`, `incomplete` ou baixa confiança), o fluxo não pode decidir automaticamente e deve gerar `REVIEW_REQUIRED`;
- `document_status` diferente de `clear` ou `document_block_flags` não vazio bloqueia despacho automático do caminhão.

### Nível de entrada do documento

- o arquivo precisa existir localmente no path informado;
- a whitelist aceita `application/pdf`, `image/png`, `image/jpeg` e `text/plain`;
- o contrato de parser usa `request_id`, `document_ref`, `content_type` e `candidate_truck_ids` opcional.

Observação prática:

- templates sintéticos robustos para o pack versionado devem incluir, no mínimo, estes campos visíveis no documento: `TCK-xxx`, `TRK-xxx`, `vehicle_type`, `document_status`, `document_block_flags` quando houver, `load_condition`, `contract_priority_flag` e `destination_constraints`.

### O que o operador pode escrever (`operator_note`)

- texto curto em linguagem natural com contexto operacional adicional;
- no máximo `2000` caracteres (após normalização);
- pode incluir indicações de revisão, por exemplo: `revisão`, `conferir` / `conferir manual`;
- pode registrar exceção observada em campo não capturada no ticket;
- não pode substituir regra dura (`hard constraints`) nem reverter estado local, nem liberar decisão insegura.

Quando houver conflito entre `operator_note` e fonte de maior hierarquia (estado local/documento), a saída esperada é revisão explícita ou bloqueio, nunca decisão automática.

### Estrutura recomendada do artefato de entrada por cenário

O desenho do pack deve ficar com **ticket/note semiestruturados** (ponto de entrada humano), mas com **fila, clima e recurso estritamente estruturados** (porque alimentam validação determinística, ranking e benchmark).

```text
DecisionRequest (entrada principal)
├─ scenario_id
├─ queue_csv_ref
├─ ticket_ref
├─ ticket_content_type
├─ operator_note
├─ weather_state
├─ resource_state
└─ expected_decision.json (meta de avaliação, não entrada operacional)
```

#### Exemplo 1 — ticket bruto (ou texto extraído)

Formato recomendado (texto ou imagem com os campos legíveis):

```txt
TCK-003 | TRK-007
vehicle_type: bitrem
document_status: clear
document_block_flags: []
load_condition: wet
contract_priority_flag: false
destination_constraints: DST-COV-01
```

Observação:
- pode haver ruído adicional, mas os campos acima precisam estar legíveis.
- `document_block_flags` pode ser vazio (`[]`) ou conter flags explícitas (`["seal_broken"]`).

#### Exemplo 2 — operador (`operator_note.txt`)

```txt
Começou a chover e a moega aberta foi bloqueada. Priorizar rota coberta se houver elegível.
```

- factual e curta.
- sem instruções de override.
- sem narrativa extensa.

#### Exemplo 3 — fila (`queue.csv`)

```csv
truck_id,arrival_ts,vehicle_type,status,declared_destination
TRK-001,2026-04-04T08:01:00+00:00,bitrem,waiting,DST-OPEN-01
TRK-002,2026-04-04T08:06:00+00:00,truck,waiting,DST-COV-01
TRK-003,2026-04-04T08:09:00+00:00,bitrem,waiting,DST-OPEN-01
```

Regras canônicas:
- snapshot FIFO estável por `arrival_ts`;
- `truck_id`, `arrival_ts`, `status` são indispensáveis no normalizador;
- `arrival_ts` deve ser ISO-8601 com timezone explícito; o adapter normaliza para UTC e rejeita timestamp sem offset;
- não pode haver `truck_id` duplicado no mesmo cenário.

#### Exemplo 4 — clima (`weather_state.json`)

```json
{
  "precipitation": "rain",
  "severity": "medium",
  "timestamp": "2026-04-04T10:18:00"
}
```

#### Exemplo 5 — estado de recurso (`resource_state.json`)

```json
[
  {
    "resource_id": "DST-OPEN-01",
    "status": "blocked",
    "capacity_pct": 0,
    "exposure": "open",
    "resource_type": "hopper",
    "allowed_vehicle_types": ["truck", "bitrem"],
    "supported_load_conditions": ["dry"]
  },
  {
    "resource_id": "DST-COV-01",
    "status": "available",
    "capacity_pct": 100,
    "exposure": "covered",
    "resource_type": "hopper",
    "allowed_vehicle_types": ["truck", "bitrem"],
    "supported_load_conditions": ["dry", "wet"]
  }
]
```

#### Exemplo 6 — baseline de aceitação do cenário (`expected_decision.json`)

```json
{
  "expected_status": "PREVIEW_READY",
  "acceptable_trucks": ["TRK-005"],
  "acceptable_destinations": ["DST-COV-01"],
  "required_constraints": ["HC-01"],
  "fifo_break_expected": true
}
```

Esse arquivo não entra no fluxo de decisão, mas é obrigatório para validar se a resposta do cenário foi aceitável no benchmark.

Regra de integridade:
- IDs sintéticos estáveis e coerentes entre arquivos (`TRK-xxx`, `DST-xxx`, `TCK-xxx`);
- `truck_id` do ticket deve bater com o da fila;
- `resource_id` citado em estado do recurso deve bater com os identificadores usados na decisão/expectativa.

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
- tool calls solicitadas/executadas/erro
- hashes de origem
- latências, incluindo timers separados `choose_tool_<tool>` e `tool_<tool>` no fluxo `full`

Referência:

- [`app/audit/payloads.py`](../app/audit/payloads.py)

### Tool intent e registro de tool call

`ToolCallIntent` representa a intenção mínima de uma tool permitida:

- `tool_name`: `validate_hard_constraints`, `rank_candidates` ou `generate_audit_payload`
- `request_id`
- `purpose` opcional, limitado a 240 caracteres

`app.gemma.prompts.build_tool_call_prompt()` monta o prompt contract-first para essa seleção: o modelo deve retornar exatamente um objeto JSON compatível com `ToolCallIntent`, usando somente tools permitidas para o estado atual e sem argumentos além de `request_id`. No fluxo operacional `full`, o orquestrador calcula `allowed_tools` com `available_tools_for_state(state)`; Gemma escolhe a próxima tool válida sob máquina de estados, e o loop é limitado a 4 tool steps.

`GemmaAdapter.choose_tool()` chama o runtime com esse prompt, valida `ToolCallIntent`, rejeita tool fora da allowlist com `MODEL_TOOL_NOT_ALLOWED` e rejeita `request_id` divergente com `MODEL_TOOL_REQUEST_ID_MISMATCH`.

No runtime textual de CI, `TextTicketRuntime` retorna a primeira tool em `allowed_tools` com `purpose="Deterministic CI tool intent."`; se `request_id` ou `allowed_tools` não vierem nos metadados, falha fechado com `TEXT_RUNTIME_TOOL_METADATA_REQUIRED`.

`app.gemma.tool_schemas.TOOL_SCHEMAS` define os schemas mínimos das tools solicitáveis pelo modelo. Cada schema aceita apenas `request_id`; o código local injeta fila, recursos, clima e política.

`ToolCallRecord` registra a execução auditável:

- `tool_name`
- `request_id`
- `state`
- `status`: `requested`, `executed` ou `error`
- `purpose`: motivo compacto retornado pelo Gemma para a tool solicitada
- `error_code` opcional

`AuditRecord.tool_calls` mantém a lista tipada desses registros.

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

O schema público deve espelhar `FrontEndPayload.model_json_schema()` com o `$id` versionado acima.

## Funções centrais

| Função | Papel |
|---|---|
| `normalize_queue_snapshot` | normalizar a fila e fixar FIFO |
| `parse_ticket_document` | obter `ParsedTicket` via Gemma sob contrato |
| `classify_exception` | produzir `ExceptionAssessment` com `primary_exception`, `secondary_exceptions` e `affected_resources` cumulativos |
| `resolve_truth` | aplicar a hierarquia de verdade |
| `validate_hard_constraints` | calcular elegibilidade por código puro |
| `rank_candidates` | ordenar somente pares elegíveis |
| `generate_audit_payload` | montar trilha reconstruível |
| `compose_driver_message` | gerar mensagem curta e segura |

## Regra de contrato

- output estruturado ou erro formal;
- nenhuma função central altera estado autoritativo por efeito colateral;
- dado ausente ou inválido nunca vira default silencioso.
