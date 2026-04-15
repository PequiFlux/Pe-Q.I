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

## Cenários obrigatórios

- `S01_BASELINE`: prova que o sistema preserva FIFO em regime nominal
- `S02_RAIN_OPEN`: chuva bloqueia destino aberto e pode justificar quebra de FIFO
- `S03_WET_LOAD`: parsing documental muda a decisão
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

