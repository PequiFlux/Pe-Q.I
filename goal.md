# GOAL.md — Pe-Q.I. Hackathon Submission Goal

Data: 2026-05-12  
Repositório-alvo: `PequiFlux/Pe-Q.I`  
Competição: The Gemma 4 Good Hackathon, Kaggle  
Objetivo operacional: transformar o Pe-Q.I. em uma submissão tecnicamente defensável, mensurável e demonstrável para a hackathon, preservando a arquitetura atual e removendo fragilidades de avaliação.

---

## 1. Objetivo mensurável principal

Entregar uma versão `submission-ready` do Pe-Q.I. como copiloto local-first, multimodal e auditável para despacho seguro de caminhões em terminal/porto sob exceções operacionais.

O sistema deve receber filas, tickets/documentos ruidosos, notas de operador, estado de clima e estado de recursos; deve extrair campos com Gemma 4, resolver conflitos com regras determinísticas, aplicar hard constraints, produzir uma decisão operacional e gerar trilha de auditoria reconstruível.

Meta de submissão em benchmark limpo, sem vazamento de rótulo:

| Métrica | Meta mínima | Bloqueio |
|---|---:|---|
| `constraint_violation_rate` | `0.000` | Qualquer violação reprova |
| `audit_completeness` | `1.000` | Qualquer cenário incompleto reprova |
| `decision_match_at_1` | `>= 0.92` | Abaixo disso não submeter como claim principal |
| `ticket_field_accuracy` global | `>= 0.95` | Abaixo disso tratar parser como frágil |
| `ticket_field_accuracy` em PDF/imagem degradada | `>= 0.90` | Abaixo disso não alegar robustez multimodal |
| `exception_macro_f1` | `>= 0.90` | Abaixo disso ablação obrigatória |
| `fifo_break_justified_precision` | `>= 0.95` | Abaixo disso política de fila não é confiável |
| `tool_call_success_rate` | `>= 0.98` | Abaixo disso tool planning não é claim central |
| `latency_p50` com Gemma 4 E4B | `<= 6 s` | Acima disso otimizar antes da demo |
| `latency_p95` com Gemma 4 E4B | `<= 12 s` | Acima disso limitar escopo da demo |
| `timeout_rate` | `< 1%` | Acima disso reduzir pipeline/modelo |

Resultado final esperado: um juiz deve conseguir rodar o projeto, ver a demo, abrir o dashboard, inspecionar o relatório de métricas e verificar que a melhoria é real, não efeito de fixture permissiva.

---

## 2. Posição estratégica da submissão

Narrativa de produto:

> Pe-Q.I. é um copiloto operacional local-first para terminais logísticos: lê documentos ruidosos com Gemma 4, interpreta exceções, chama ferramentas permitidas, aplica regras de segurança e entrega uma decisão de despacho explicável, auditável e executável mesmo em ambiente de baixa conectividade.

O projeto não deve ser vendido como sistema produtivo validado em campo. O claim correto é:

> protótipo funcional, mensurável e reproduzível de decisão operacional auditável em cenário sintético realista, com uso substantivo de Gemma 4 em percepção documental, classificação de exceções e tool planning controlado.

Não fazer claims de produção, integração real com porto, validação regulatória, segurança industrial certificada ou dados reais se isso não existir.

---

## 3. Estado atual assumido

Baseline histórico atual, a partir do relatório de pesquisa:

| Variante | `decision_match_at_1` | `exception_f1` | `ticket_field_accuracy` | `constraint_violation_rate` | Uso |
|---|---:|---:|---:|---:|---|
| `raw_fifo` | `0.25` | `0.00` | `0.00` | `0.35` | baseline fraco |
| `fifo_safe` | `0.75` | `0.735` | `0.00` | `0.00` | baseline operacional |
| `heuristic` | `0.85` | `0.678` | `0.85` | `0.00` | baseline determinístico |
| `full` | `1.00` | `1.00` | `0.969` | `0.00` | snapshot de contrato, não prova final |

Problema central: o snapshot atual mede consistência interna e contrato, mas não prova generalização multimodal robusta. O runtime textual e o uso de sidecars como `expected_ticket.json` em fixtures não textuais enfraquecem a evidência.

Linha de ação: manter a arquitetura e fortalecer a prova. Não reescrever o sistema.

---

## 4. Regras não negociáveis

1. A decisão final continua passando por hard constraints determinísticas.
2. Gemma 4 não pode decidir livremente uma ação insegura.
3. A variante `full` em benchmark multimodal não pode ler `expected_ticket.json`.
4. Todo cenário avaliado precisa gerar log de auditoria completo.
5. Toda métrica pública precisa sair de script reproduzível.
6. Toda melhoria precisa ser comparada contra `heuristic` e `fifo_safe`.
7. Se houver falha, classificar por tipo: percepção, conflito de verdade, exceção, ranking, auditoria, tool path ou latência.
8. Não criar uma segunda identidade de produto. Melhorar Pe-Q.I.; não começar outro software.
9. Não trocar a stack inteira. Implementar incrementos pequenos e testáveis.
10. Não esconder limitações: dados sintéticos, sem validação de campo, sem integração produtiva real.

---

## 5. Contrato de arquitetura

Arquitetura desejada:

```text
Documento bruto
  -> preprocessamento visual
  -> OCR hints / texto extraído
  -> extração por campo com Gemma 4
  -> evidência por campo
  -> verificação de schema e conflito
  -> calibração de confiança
  -> truth resolver
  -> hard constraints
  -> ranking
  -> audit builder
  -> UI, benchmark, dashboard e relatório
```

Gemma 4 deve ser usado onde gera vantagem real:

1. parsing multimodal de tickets e notas;
2. classificação de exceções ambíguas;
3. tool planning dentro de whitelist;
4. geração de explicação curta baseada em evidências.

Gemma 4 não deve substituir:

1. validação de schema;
2. hard constraints;
3. ranking determinístico;
4. auditoria final;
5. cálculo de métricas.

Runtime principal de demo: `gemma4:e4b` ou equivalente local disponível.  
Runtime auxiliar opcional: `gemma4:26b` como teacher/oráculo para pseudo-rótulos e stress tests.  
Runtime textual atual: manter apenas para contrato, CI barato e regressão.

---

## 6. Dados e benchmark

Criar benchmark B1 limpo.

Estrutura sugerida:

```text
scenarios/
  sample/                         # B0 histórico, manter
  extended/
    public_train/
    public_dev/
    public_test_frozen/
    private_holdout/
```

Cada cenário deve conter, no mínimo:

```text
queue.csv
ticket.{txt|pdf|png|jpg}
operator_note.txt
weather_state.json
resource_state.json
expected_decision.json
metadata.json
```

`metadata.json` deve registrar:

```json
{
  "scenario_id": "string",
  "scenario_family": "string",
  "document_template_id": "string",
  "modality": "txt|pdf|png|jpg",
  "perturbation_recipe": ["rotation", "blur", "ocr_noise"],
  "created_by": "generator|manual",
  "label_quality": "auto|reviewed",
  "sha256": "string"
}
```

Tamanho mínimo aceitável:

| Split | Tamanho mínimo | Uso |
|---|---:|---|
| `public_train` | `180` cenários | prompts, LoRA, thresholds |
| `public_dev` | `60` cenários | seleção de modelo e configuração |
| `public_test_frozen` | `60` cenários | score público reprodutível |
| `private_holdout` | `60` cenários | validação final interna |

Se o prazo apertar, mínimo defensável:

| Split | Tamanho mínimo emergencial |
|---|---:|
| `public_train` | `80` |
| `public_dev` | `30` |
| `public_test_frozen` | `30` |
| `private_holdout` | `30` |

Augmentações obrigatórias:

1. rotação `±90°`;
2. skew leve;
3. blur;
4. compressão JPEG;
5. baixa resolução;
6. ruído de OCR;
7. abreviações pt-BR;
8. campos ausentes;
9. conflito entre ticket e nota;
10. destino inexistente;
11. recurso bloqueado;
12. clima incompatível com tipo de carga.

Proibição crítica:

```text
expected_ticket.json NÃO pode existir ou ser lido em public_dev,
public_test_frozen ou private_holdout para avaliação da variante full.
```

Pode existir em `public_train` apenas se for usado como rótulo de treino, nunca como entrada de inferência.

---

## 7. Métricas formais

Implementar ou consolidar estas métricas em `bench/metrics.py` ou equivalente.

### 7.1 `constraint_violation_rate`

```text
n_decisions_with_hard_constraint_violation / n_total_decisions
```

Deve ser `0.000`.

### 7.2 `decision_match_at_1`

```text
n_final_decisions_matching_expected_decision / n_total_scenarios
```

Comparar contra `heuristic`, `fifo_safe` e `raw_fifo`.

### 7.3 `ticket_field_accuracy`

```text
n_correct_required_ticket_fields / n_required_ticket_fields
```

Calcular globalmente e por modalidade:

```text
txt, pdf_text, pdf_scanned, png, jpg
```

Campos mínimos:

```text
truck_id
cargo_type
destination
arrival_time
ticket_time
priority_code
exception_hint
document_confidence
```

### 7.4 `exception_macro_f1`

Macro F1 por classe de exceção primária.

Classes mínimas:

```text
none
weather_risk
resource_unavailable
document_conflict
capacity_limit
priority_override
destination_unknown
unsafe_dispatch
manual_review_required
```

### 7.5 `fifo_break_justified_precision`

```text
n_fifo_breaks_with_valid_policy_reason / n_predicted_fifo_breaks
```

Se não houver quebra de FIFO, reportar `null` e não mascarar.

### 7.6 `audit_completeness`

Um cenário tem auditoria completa se o log contém:

1. inputs consumidos;
2. campos extraídos;
3. evidências por campo;
4. score/confiança por campo;
5. resolução de conflitos;
6. hard constraints avaliadas;
7. candidatos rejeitados e motivo;
8. ranking final;
9. decisão final;
10. explicação curta;
11. runtime/model/config/seed.

```text
n_scenarios_with_complete_audit / n_total_scenarios
```

Deve ser `1.000`.

### 7.7 `tool_call_success_rate`

```text
n_tool_calls_valid_and_successful / n_tool_calls_attempted
```

Tool call válido exige:

1. tool em whitelist;
2. argumentos compatíveis com schema;
3. resposta parseável;
4. sem fallback silencioso.

### 7.8 Latência

Medir end-to-end, por cenário:

```text
latency_ms_preprocess
latency_ms_model
latency_ms_rules
latency_ms_audit
latency_ms_total
```

Reportar:

```text
p50, p75, p90, p95, max, timeout_rate
```

---

## 8. Validação estatística

Criar `bench/stats.py`.

Comparações obrigatórias:

1. `full_clean` vs `heuristic`;
2. `full_clean` vs `fifo_safe`;
3. `full_clean` vs `full_text_contract`;
4. ablações entre si.

Métodos:

```text
McNemar exato para decision_match_at_1 em cenários pareados.
Bootstrap estratificado por scenario_family para:
  - ticket_field_accuracy
  - exception_macro_f1
  - fifo_break_justified_precision
  - latency deltas
```

Configuração:

```text
bootstrap_samples = 10000
confidence_interval = 95%
random_seed = 42
```

Critério de promoção:

```text
p < 0.05 em McNemar
e/ou limite inferior do IC 95% do delta > 0
```

Se a significância não fechar, a submissão ainda pode usar a melhoria como evidência exploratória, mas não como claim forte.

---

## 9. Implementações P0

P0 significa obrigatório para submissão defensável.

### P0.1 Guard contra vazamento de `expected_ticket`

Arquivos sugeridos:

```text
bench/clean_eval.py
tests/scenarios/test_no_expected_ticket_leakage.py
```

Critério de aceite:

1. qualquer tentativa de rodar `full` multimodal com `expected_ticket.json` em split de avaliação deve falhar;
2. teste automatizado deve criar fixture com sidecar proibido e verificar falha;
3. CI deve executar esse teste.

### P0.2 Benchmark estendido limpo

Arquivos sugeridos:

```text
scripts/build_extended_pack.py
scenarios/extended/**
tests/scenarios/test_extended_pack_schema.py
```

Critério de aceite:

1. pelo menos `60` novos cenários se prazo estiver crítico; ideal `300+`;
2. splits separados;
3. manifesto com SHA256;
4. validação de schema em todos os cenários;
5. distribuição por modalidade e família registrada.

### P0.3 Preprocessamento visual

Arquivos sugeridos:

```text
app/document/preprocess.py
tests/unit/test_document_preprocess.py
```

Funções mínimas:

```python
render_pdf_pages(...)
normalize_image(...)
generate_document_views(...)
detect_rotation_hint(...)
```

Critério de aceite:

1. suportar PDF, PNG e JPG;
2. gerar múltiplas views quando necessário;
3. não modificar o documento original;
4. registrar no audit log qual view foi usada.

### P0.4 OCR hints locais

Arquivos sugeridos:

```text
app/document/ocr_hints.py
tests/unit/test_ocr_hints.py
```

Critério de aceite:

1. OCR é hint, não fonte soberana;
2. output entra no prompt com marcação explícita;
3. falha de OCR não derruba pipeline;
4. audit log registra presença/ausência de OCR.

### P0.5 Extração por campo com evidência

Arquivos sugeridos:

```text
app/gemma/field_extractor.py
app/gemma/prompts.py
tests/unit/test_field_extractor_schema.py
```

Saída mínima:

```json
{
  "fields": {
    "truck_id": {
      "value": "TRK-001",
      "confidence": 0.94,
      "evidence": ["line:...", "view:page_1_crop_2"],
      "source": "gemma4:e4b"
    }
  },
  "needs_review": false,
  "reason": "string"
}
```

Critério de aceite:

1. JSON válido sempre que possível;
2. fallback controlado para `manual_review_required`;
3. evidência obrigatória por campo crítico;
4. schema Pydantic ou equivalente;
5. teste de documento conflitante deve acionar revisão ou resolver por política explícita.

### P0.6 Calibração e revisão humana

Arquivos sugeridos:

```text
app/gemma/calibration.py
tests/unit/test_calibration_thresholds.py
```

Regra mínima:

```text
confidence < threshold por campo crítico
ou conflito de fontes
ou OCR/model discordante
=> manual_review_required
```

Critério de aceite:

1. thresholds configuráveis;
2. thresholds versionados;
3. impacto medido no benchmark;
4. revisar não pode virar fuga para melhorar métrica artificialmente: contar taxa de revisão.

Métrica adicional:

```text
manual_review_rate <= 0.15 no public_test_frozen
```

### P0.7 Estatística, relatório e artefatos

Arquivos sugeridos:

```text
bench/stats.py
bench/reporting.py
bench/plots.py
```

Critério de aceite:

1. gerar `artifacts/latest/metrics.json`;
2. gerar `artifacts/latest/summary.csv`;
3. gerar `artifacts/latest/error_analysis.csv`;
4. gerar `artifacts/latest/report.md`;
5. gerar gráficos simples para dashboard/write-up;
6. registrar model, runtime, seed e commit hash.

Contrato de `metrics.json`:

```json
{
  "benchmark_id": "B1_clean_public_test_frozen",
  "commit": "string",
  "timestamp_utc": "string",
  "runtime": "gemma4:e4b",
  "scenario_count": 60,
  "metrics": {
    "constraint_violation_rate": 0.0,
    "audit_completeness": 1.0,
    "decision_match_at_1": 0.92,
    "ticket_field_accuracy": 0.95,
    "exception_macro_f1": 0.90,
    "fifo_break_justified_precision": 0.95,
    "tool_call_success_rate": 0.98,
    "latency_p50_ms": 6000,
    "latency_p95_ms": 12000,
    "timeout_rate": 0.0,
    "manual_review_rate": 0.15
  },
  "gates": {
    "submission_ready": true,
    "failed_gates": []
  }
}
```

### P0.8 Dashboard e notebooks mínimos

Arquivos sugeridos:

```text
notebooks/01_baselines.ipynb
notebooks/02_multimodal_parsing_eval.ipynb
notebooks/03_robustness.ipynb
app/ui/pages/benchmark_dashboard.py
```

Critério de aceite:

1. juiz consegue ver baseline vs full;
2. heatmap campo x modalidade;
3. matriz de confusão de exceção;
4. latência por variante;
5. exemplos de 3 falhas e 3 acertos fortes;
6. auditoria de uma decisão mostrada na UI.

---

## 10. Implementações P1

P1 significa alto retorno, mas só depois dos P0.

### P1.1 QLoRA/LoRA em Gemma 4 E4B

Arquivos sugeridos:

```text
app/train/train_parser_lora.py
app/train/train_exception_lora.py
configs/train/parser_e4b.yaml
configs/train/exception_e4b.yaml
```

Hiperparâmetros iniciais:

```yaml
lora_r: [8, 16, 32]
lora_alpha: [16, 32, 64]
learning_rate: [5e-5, 1e-4, 2e-4]
epochs: [2, 3, 5]
effective_batch_size: [16, 32]
seed: 42
```

Critério de aceite:

1. só promover LoRA se melhorar `public_dev`;
2. medir contra prompt-only;
3. não treinar no `public_test_frozen`;
4. salvar adapter, config, logs e hash de dataset;
5. se a latência piorar demais, usar LoRA apenas em análise offline.

### P1.2 Teacher com Gemma 4 26B

Arquivos sugeridos:

```text
scripts/generate_teacher_labels.py
artifacts/teacher_labels/**
```

Critério de aceite:

1. teacher gera pseudo-rótulos apenas para treino ou análise;
2. pseudo-rótulo nunca entra como ground truth de teste;
3. divergências teacher vs label humano geram fila de revisão.

### P1.3 CI multimodal manual/schedule

Arquivos sugeridos:

```text
.github/workflows/eval.yml
```

Critério de aceite:

1. job manual para benchmark com runtime Gemma;
2. job barato de contrato roda em todo PR;
3. artefatos ficam disponíveis no workflow;
4. falha se gates primários quebram.

---

## 11. Implementações P2

P2 só entra se P0 e P1 estiverem estáveis.

1. `gemma4:31b` como oráculo offline;
2. página extra de diagnóstico por campo;
3. release package com manifesto completo;
4. integração com Kaggle Notebook;
5. demo edge em dispositivo físico, se já houver hardware.

Não sacrificar P0 por P2.

---

## 12. Testes obrigatórios

Adicionar ou garantir testes:

```text
tests/unit/test_document_preprocess.py
tests/unit/test_ocr_hints.py
tests/unit/test_field_extractor_schema.py
tests/unit/test_calibration_thresholds.py
tests/integration/test_clean_multimodal_eval.py
tests/scenarios/test_no_expected_ticket_leakage.py
tests/scenarios/test_extended_pack_schema.py
tests/failure/test_conflicting_truth_routes_to_review.py
tests/e2e/test_e4b_ui_scenario_pack.py
```

Casos de falha obrigatórios:

1. ticket PDF escaneado sem texto extraível;
2. imagem rotacionada;
3. blur + compressão forte;
4. conflito entre ticket e fila;
5. nota operacional enganosa;
6. destino inexistente;
7. recurso bloqueado;
8. carga úmida com destino aberto;
9. tool call fora de whitelist;
10. JSON inválido retornado pelo modelo.

---

## 13. Comandos de validação esperados

Codex deve adaptar aos entrypoints reais do repo, mas manter estes alvos.

### 13.1 Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-all.txt
```

### 13.2 Qualidade básica

```bash
python -m black --check app bench tests scripts
python -m pytest -q
```

Se Ruff/mypy forem adicionados:

```bash
python -m ruff check app bench tests scripts
python -m mypy app bench
```

### 13.3 Auditoria de blueprint

```bash
python -m scripts.blueprint_audit
```

Se o entrypoint tiver outro nome, descobrir o comando real e documentar em `README.md`.

### 13.4 Benchmark textual de contrato

```bash
python -m bench.run \
  --variant full \
  --runtime text \
  --scenario-dir scenarios/sample \
  --output artifacts/latest/text_contract
```

### 13.5 Benchmark multimodal limpo

```bash
python -m bench.clean_eval \
  --variant full \
  --runtime gemma4:e4b \
  --scenario-dir scenarios/extended/public_test_frozen \
  --output artifacts/latest/clean_public_test \
  --fail-on-leakage
```

### 13.6 Comparação estatística

```bash
python -m bench.stats \
  --baseline artifacts/latest/heuristic_public_test/metrics.json \
  --candidate artifacts/latest/clean_public_test/metrics.json \
  --output artifacts/latest/stats_report.json
```

### 13.7 Relatório

```bash
python -m bench.reporting \
  --metrics artifacts/latest/clean_public_test/metrics.json \
  --stats artifacts/latest/stats_report.json \
  --errors artifacts/latest/error_analysis.csv \
  --output artifacts/latest/report.md
```

---

## 14. Gates de submissão

Criar `bench/gates.py` ou incorporar em `bench/reporting.py`.

A submissão só é marcada como pronta se:

```text
constraint_violation_rate == 0.0
audit_completeness == 1.0
decision_match_at_1 >= 0.92
ticket_field_accuracy >= 0.95
ticket_field_accuracy_pdf_or_image_degraded >= 0.90
exception_macro_f1 >= 0.90
fifo_break_justified_precision >= 0.95 or null with explicit no-break case
tool_call_success_rate >= 0.98
latency_p50_ms <= 6000
latency_p95_ms <= 12000
timeout_rate < 0.01
manual_review_rate <= 0.15
no_expected_ticket_leakage == true
```

Se algum gate falhar, gerar:

```json
{
  "submission_ready": false,
  "failed_gates": [
    {
      "metric": "ticket_field_accuracy_pdf_or_image_degraded",
      "actual": 0.84,
      "target": 0.90,
      "recommended_action": "improve preprocess/OCR/self_consistency"
    }
  ]
}
```

---

## 15. Análise de erro obrigatória

Gerar `artifacts/latest/error_analysis.csv` com colunas:

```text
scenario_id
scenario_family
modality
perturbation_recipe
expected_decision
predicted_decision
decision_correct
primary_failure_type
failed_field
confidence
manual_review_flag
latency_ms_total
notes
```

Categorias de `primary_failure_type`:

```text
perception_failure
truth_conflict_failure
exception_classification_failure
hard_constraint_failure
ranking_failure
audit_failure
tool_path_failure
latency_failure
label_issue
unknown
```

A cada falha, Codex deve tentar corrigir na ordem:

1. vazamento/bug de avaliação;
2. schema/validação;
3. prompt/extração por campo;
4. preprocessing/OCR;
5. calibração;
6. regra de domínio;
7. modelo/LoRA.

---

## 16. UI e demo

A UI precisa mostrar um fluxo filmável:

1. carregar cenário;
2. mostrar fila e documento;
3. exibir campos extraídos com confiança;
4. exibir conflito, se existir;
5. exibir hard constraints;
6. exibir ranking;
7. exibir decisão final;
8. exibir auditoria reconstruível;
9. exibir comparação com baseline;
10. exibir métricas agregadas.

Demo mínima para vídeo:

```text
Caso 1: decisão FIFO simples.
Caso 2: quebra de FIFO justificada por restrição operacional.
Caso 3: documento ruidoso/imagem onde Gemma extrai campos.
Caso 4: conflito detectado e enviado para revisão.
Caso 5: tool planning dentro da whitelist.
```

O vídeo deve provar utilidade em menos de 3 minutos:

```text
0:00-0:20 problema operacional
0:20-0:50 input ruidoso e fila
0:50-1:30 Gemma extrai e classifica
1:30-2:10 regras seguras + auditoria
2:10-2:40 métricas e melhoria contra baseline
2:40-3:00 por que é local-first e relevante
```

---

## 17. Write-up da hackathon

O write-up deve conter:

1. problema real e usuário-alvo;
2. por que local-first importa;
3. arquitetura;
4. onde Gemma 4 entra;
5. hard constraints;
6. benchmark e splits;
7. métricas;
8. resultados;
9. ablações;
10. falhas conhecidas;
11. limitações honestas;
12. próximos passos.

Não escrever um texto genérico de IA para o bem. O diferencial é decisão auditável sob restrição.

---

## 18. Cronograma de execução

Se houver poucos dias, executar nesta ordem.

### Dia 1

1. rodar testes existentes;
2. congelar B0;
3. implementar guard contra `expected_ticket`;
4. criar estrutura B1;
5. criar 30-60 cenários limpos iniciais;
6. gerar `metrics.json` inicial.

### Dia 2

1. preprocessamento visual;
2. OCR hints;
3. field extractor com evidência;
4. testes unitários;
5. primeiro benchmark `public_dev`.

### Dia 3

1. calibração;
2. análise de erros;
3. dashboard inicial;
4. ablação sem OCR, sem preprocess, sem self-consistency.

### Dia 4

1. expandir benchmark;
2. rodar `public_test_frozen`;
3. estatística;
4. corrigir falhas P0.

### Dia 5

1. notebooks;
2. UI de demo;
3. relatório final;
4. vídeo;
5. dry-run completo.

Se restar tempo, fazer P1 LoRA/teacher. Se não restar, não arriscar.

---

## 19. Ordem de trabalho para Codex

Codex deve trabalhar em PRs ou blocos sequenciais pequenos.

### Bloco 0 — inspeção

Objetivo: mapear entrypoints reais.

Tarefas:

1. ler `README`, `requirements`, `app`, `bench`, `tests`, `scenarios`;
2. identificar comandos existentes;
3. rodar testes;
4. registrar baseline atual em `artifacts/baseline_b0/`.

Saída esperada:

```text
artifacts/baseline_b0/metrics.json
artifacts/baseline_b0/notes.md
```

### Bloco 1 — blindagem de avaliação

Objetivo: impedir avaliação contaminada.

Tarefas:

1. implementar `bench/clean_eval.py`;
2. implementar teste de leakage;
3. atualizar CI;
4. documentar regra no README.

Gate:

```bash
python -m pytest tests/scenarios/test_no_expected_ticket_leakage.py -q
```

### Bloco 2 — benchmark B1

Objetivo: criar dados limpos e validados.

Tarefas:

1. gerar splits;
2. criar manifestos;
3. validar schemas;
4. gerar distribuição por família/modalidade.

Gate:

```bash
python -m pytest tests/scenarios/test_extended_pack_schema.py -q
```

### Bloco 3 — parser multimodal

Objetivo: extrair campos com evidência.

Tarefas:

1. preprocessamento;
2. OCR hints;
3. field extractor;
4. schema;
5. audit log.

Gate:

```bash
python -m pytest tests/unit/test_document_preprocess.py tests/unit/test_ocr_hints.py tests/unit/test_field_extractor_schema.py -q
```

### Bloco 4 — benchmark e estatística

Objetivo: transformar execução em evidência.

Tarefas:

1. métricas;
2. latência;
3. bootstrap;
4. McNemar;
5. relatório.

Gate:

```bash
python -m bench.clean_eval --variant full --runtime gemma4:e4b --scenario-dir scenarios/extended/public_test_frozen --output artifacts/latest --fail-on-leakage
python -m bench.reporting --metrics artifacts/latest/metrics.json --output artifacts/latest/report.md
```

### Bloco 5 — UI, notebooks e submissão

Objetivo: tornar apresentável.

Tarefas:

1. dashboard;
2. notebooks;
3. exemplos de demo;
4. roteiro de vídeo;
5. README final.

Gate:

```bash
python -m pytest -q
python -m black --check app bench tests scripts
```

---

## 20. Definition of Done

O projeto está pronto para submissão quando existir:

```text
GOAL.md
README.md atualizado
artifacts/latest/metrics.json
artifacts/latest/report.md
artifacts/latest/error_analysis.csv
artifacts/latest/summary.csv
notebooks/01_baselines.ipynb
notebooks/02_multimodal_parsing_eval.ipynb
notebooks/03_robustness.ipynb
app/ui/pages/benchmark_dashboard.py
scenarios/extended/public_test_frozen/manifest.json
tests/scenarios/test_no_expected_ticket_leakage.py
```

E quando estes comandos passarem:

```bash
python -m pytest -q
python -m black --check app bench tests scripts
python -m bench.clean_eval --variant full --runtime gemma4:e4b --scenario-dir scenarios/extended/public_test_frozen --output artifacts/latest --fail-on-leakage
python -m bench.reporting --metrics artifacts/latest/metrics.json --output artifacts/latest/report.md
```

E quando `artifacts/latest/metrics.json` indicar:

```json
{
  "submission_ready": true
}
```

---

## 21. Riscos fatais e contramedidas

| Risco | Custo | Contramedida |
|---|---|---|
| Métrica perfeita por vazamento | submissão desacreditada | guard contra `expected_ticket`, holdout, manifesto |
| Demo bonita sem benchmark | perde em technical depth | dashboard + métricas + ablação |
| Benchmark pequeno demais | claim fraco | ampliar cenários ou reduzir claim |
| LoRA atrasar tudo | custo alto | P1, não P0 |
| Latência ruim | demo fraca | E4B, cache, views limitadas |
| Alucinação de parser | decisão insegura | schema, evidência, revisão, hard constraints |
| Claim produtivo falso | perda de credibilidade | declarar sintético e protótipo |
| UI sem fluxo claro | vídeo fraco | cinco casos de demo pré-definidos |

---

## 22. Critério prático de priorização

Quando houver conflito, usar esta ordem:

1. segurança e hard constraints;
2. benchmark limpo;
3. auditabilidade;
4. parsing multimodal;
5. dashboard e vídeo;
6. LoRA;
7. features extras.

Regra final:

```text
Melhoria que não aparece em métrica, teste, dashboard ou vídeo não conta para a hackathon.
```
