# Scenario Pack e Benchmark

## Objetivo

O pack sintético existe para tornar a submissão:

- reproduzível
- benchmarkável
- filmável
- publicável sem dados reais

## Estrutura esperada

```text
scenarios/
├─ manifest.json
├─ schemas/
├─ common/
│  ├─ policy_profile.json
│  └─ destinations.json
└─ cases/
   ├─ S01_BASELINE/
   ├─ S02_RAIN_OPEN/
   ├─ S03_WET_LOAD/
   ├─ S04_CONVEYOR_DOWN/
   ├─ S05_CONTRACT_PRIORITY/
   ├─ S06_DOCUMENT_BLOCK/
   ├─ S07_VEHICLE_INCOMPAT/
   ├─ S08_REDUCED_CAPACITY/
   ├─ S09_HUMAN_OVERRIDE/
   └─ S10_FIFO_BREAK_JUSTIFIED/
```

## Estrutura de dados por cenário

Cada cenário no diretório `scenarios/cases/<SCENARIO>/` deve conter os artefatos de entrada abaixo e a meta de aceitação separada:

```text
scenarios/cases/<SCENARIO>/
├─ ticket.(pdf|png|jpg|jpeg|txt)
├─ expected_ticket.json   # opcional para benchmark/CI de casos multimodais
├─ queue.csv
├─ operator_note.txt
├─ weather_state.json
├─ resource_state.json
└─ expected_decision.json
```

Regra de desenho: **ticket e nota** podem ser semiestruturados; **queue/weather/resource** devem ser estruturados e canônicos.

### `ticket.*`

Objetivo: fornecer evidência suficiente para o parser inferir: `ticket_id`, `truck_id`, `vehicle_type`, `document_status`, `document_block_flags`, `load_condition`, `contract_priority_flag`, `destination_constraints`.

Para tickets `pdf/png/jpg/jpeg`, o pack pode versionar `expected_ticket.json` como sidecar canônico do benchmark/CI. Ele não substitui a leitura multimodal do runtime real; só fixa o alvo esperado para comparação e testes sem GPU/Ollama.

Exemplos:

```txt
TCK-003 | TRK-007
vehicle_type: bitrem
document_status: clear
document_block_flags: []
load_condition: wet
contract_priority_flag: false
destination_constraints: DST-COV-01
```

`document_status`, `load_condition`, `vehicle_type` e a coerência da `truck_id` com a fila serão usados pela camada determinística.

### `operator_note.txt`

Nota curta e factual, útil como contexto de exceção, não como fonte de verdade principal.

```txt
Começou a chover e a moega aberta foi bloqueada. Priorizar rota coberta se houver elegível.
```

### `queue.csv`

Snapshot FIFO estável e determinístico.

```csv
truck_id,arrival_ts,vehicle_type,status,declared_destination
TRK-001,2026-04-04T08:01:00+00:00,bitrem,waiting,DST-OPEN-01
TRK-002,2026-04-04T08:06:00+00:00,truck,waiting,DST-COV-01
TRK-003,2026-04-04T08:09:00+00:00,bitrem,waiting,DST-OPEN-01
```

Regras:
- mínimo de campos do pack: `truck_id`, `arrival_ts`, `vehicle_type`, `status`, `declared_destination`;
- no normalizador, indispensáveis: `truck_id`, `arrival_ts`, `status`;
- `arrival_ts` precisa ser ISO-8601 com timezone explícito; timestamps sem offset são rejeitados;
- IDs de caminhão únicos por cenário.

### `weather_state.json`

Campos mínimos: `precipitation`, `severity`. `timestamp` é opcional e pode ser usado quando o cenário precisar fixar explicitamente o horário do snapshot.

```json
{
  "precipitation": "rain",
  "severity": "medium",
  "timestamp": "2026-04-04T10:18:00"
}
```

### `resource_state.json`

Campos mínimos: `resource_id`, `status`, `capacity_pct`, `exposure`, `allowed_vehicle_types`, `supported_load_conditions`.

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

### `expected_decision.json`

Não entra no fluxo de decisão, mas dita aceitabilidade de saída no benchmark.

```json
{
  "expected_status": "PREVIEW_READY",
  "acceptable_trucks": ["TRK-005"],
  "acceptable_destinations": ["DST-COV-01"],
  "required_constraints": ["HC-01"],
  "fifo_break_expected": true
}
```

Campos mínimos recomendados: `expected_status`, `acceptable_trucks`, `acceptable_destinations`, `required_constraints`, `fifo_break_expected`.

### Regra de integridade entre arquivos

- IDs sintéticos e estáveis: `TRK-001`, `DST-COV-01`, `TCK-003`;
- `truck_id` no ticket coincide com linha da fila, exceto cenários explícitos de conflito de verdade como `S13_TRUCK_ID_NOT_IN_QUEUE`;
- `resource_id` em `resource_state` e na decisão/expected devem ser compatíveis, exceto cenários explícitos de destino desconhecido como `S15_UNKNOWN_DESTINATION_IN_TICKET`.

## Catálogo humano dos cenários

O catálogo humano canônico fica em `scenarios/README.md`.

Use este documento para estrutura, contratos e integridade; use `scenarios/README.md` para a narrativa caso a caso.

Cobertura esperada do pack atual:

- `S01`-`S10`: base operacional e narrativa principal da submissão
- `S11`-`S12`: robustez multimodal
- `S13`-`S16`: conflitos de verdade e fail-closed
- `S17`-`S20`: governança de override, desempate e stress

## Variantes de benchmark

- `raw_fifo`: FIFO bruto por ordem de chegada e destino declarado, sem contexto nem hard constraints
- `fifo_safe`: variante operacional `fifo`, ou seja, FIFO entre pares elegíveis após hard constraints
- `heuristic`: downstream determinístico com interpretação simplificada
- `full`: Gemma + downstream determinístico completo

## Métricas principais

- `constraint_violation_rate`
- `decision_match_at_1`
- `exception_f1`
- `ticket_field_accuracy`
- `fifo_break_justified_precision`
- `latency_p50`
- `latency_p95`
- `audit_completeness`

O `summary.csv` ainda inclui colunas de auditoria do Gemma Tool Planner no variant `full`: `tool_call_count`, `tool_call_success`, `tool_path`, `tool_error_count` e `planner_step_count`. O `metrics.json` agrega essa trilha com `tool_call_success_rate`, `avg_tool_call_count`, `avg_planner_step_count`, `tool_error_count` e `tool_error_rate`. Variantes `raw_fifo`, `fifo_safe` e `heuristic` não registram tool calls.

Nota: a política atual do repositório remove o uso de fallback operacional. Se o benchmark precisar medir indisponibilidade, trate isso como `REVIEW_REQUIRED` ou `BLOCKED`, não como modo degradado.

## Saídas esperadas

Em `bench/reports/extended/<run_id>/`:

- `summary.csv`
- `per_scenario.json`
- `metrics.json` com `run_metadata` declarando runtime, manifest, contagem, variantes reportadas e nota de latência

`bench/reports/sample/` é evidência pública congelada e não deve ser usado como saída viva do benchmark. Para snapshots experimentais próximos do sample público, use `bench/reports/extended-sample/<run_id>` ou um diretório temporário local.

## Extensões futuras

`scenarios/cases/` e `scenarios/manifest.json` representam a vitrine pública congelada de 20 casos. Novos cenários devem ficar fora desse pack:

- `scenarios/extended/stress/` para filas maiores, latência, escala e robustez.
- `scenarios/extended/failure/` para entradas inválidas, documentos malformados, dependências ausentes e casos fail-closed.

Manifests estendidos, quando necessários, devem viver em `scenarios/extended/` e escrever relatórios em `bench/reports/extended/`, `bench/reports/extended-sample/` ou diretório temporário local.
