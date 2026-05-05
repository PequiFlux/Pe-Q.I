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
├─ queue.csv
├─ operator_note.txt
├─ weather_state.json
├─ resource_state.json
└─ expected_decision.json
```

Regra de desenho: **ticket e nota** podem ser semiestruturados; **queue/weather/resource** devem ser estruturados e canônicos.

### `ticket.*`

Objetivo: fornecer evidência suficiente para o parser inferir: `ticket_id`, `truck_id`, `vehicle_type`, `document_status`, `document_block_flags`, `load_condition`, `contract_priority_flag`, `destination_constraints`.

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
TRK-001,2026-04-04T08:01:00,bitrem,waiting,DST-OPEN-01
TRK-002,2026-04-04T08:06:00,truck,waiting,DST-COV-01
TRK-003,2026-04-04T08:09:00,bitrem,waiting,DST-OPEN-01
```

Regras:
- mínimo de campos do pack: `truck_id`, `arrival_ts`, `vehicle_type`, `status`, `declared_destination`;
- no normalizador, indispensáveis: `truck_id`, `arrival_ts`, `status`;
- `arrival_ts` precisa ser ISO-8601 parseável;
- IDs de caminhão únicos por cenário.

### `weather_state.json`

Campos mínimos: `precipitation`, `severity`, `timestamp`.

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
- `truck_id` no ticket coincide com linha da fila;
- `resource_id` em `resource_state` e na decisão/expected devem ser compatíveis.

## Cenários obrigatórios

- `S01_BASELINE`: prova que o sistema preserva FIFO em regime nominal
- `S02_RAIN_OPEN`: chuva bloqueia destino aberto e pode justificar quebra de FIFO
- `S03_WET_LOAD`: parsing documental identifica carga úmida, mas nota com conferência manual exige `REVIEW_REQUIRED`
- `S04_CONVEYOR_DOWN`: estado local bloqueia recurso
- `S05_CONTRACT_PRIORITY`: política publicada pode romper FIFO
- `S06_DOCUMENT_BLOCK`: bloqueio documental torna caminhão inelegível
- `S07_VEHICLE_INCOMPAT`: incompatibilidade física é binária
- `S08_REDUCED_CAPACITY`: separa bloqueio duro de penalidade
- `S09_HUMAN_OVERRIDE`: prova governança e trilha de override
- `S10_FIFO_BREAK_JUSTIFIED`: cenário narrativo principal da submissão

## Variantes de benchmark

- `fifo`: baseline ingênuo por ordem de chegada
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

Nota: a política atual do repositório remove o uso de fallback operacional. Se o benchmark precisar medir indisponibilidade, trate isso como `REVIEW_REQUIRED` ou `BLOCKED`, não como modo degradado.

## Saídas esperadas

Em `bench/reports/<run_id>/`:

- `summary.csv`
- `per_scenario.json`
- `metrics.json`
- gráficos de latência e comparação
- amostras de payload auditável
