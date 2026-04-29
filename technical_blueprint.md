# PequiFlux Yard Copilot — Technical Blueprint

**Path alvo no repositório:** `docs/technical_blueprint.md`  
**Status:** blueprint técnico para implementação da submissão da Gemma 4 Good Hackathon  
**Escopo congelado:** recorte do **PequiFlux Yard Copilot**, não o PequiFlux completo  
**Fonte factual primária:** dossiê técnico de submissão anexado ao projeto  
**Princípio operacional:** Gemma 4 interpreta; regras determinísticas decidem; humano aprova, bloqueia ou faz override; tudo fica auditável  
**Princípio de verdade:** estado local validado prevalece sobre documento parseado; documento parseado prevalece sobre nota textual livre; conflitos materiais geram bloqueio ou `REVIEW_REQUIRED`  

## Registro de assunções controladas

Quando um ponto operacional, técnico ou de hardware não está definido explicitamente no material-base, ele é marcado como **ASSUNÇÃO**. Essas assunções são deliberadas, rastreáveis e devem permanecer publicadas como tal no repositório.

| ID | ASSUNÇÃO | Impacto |
|---|---|---|
| A-01 | Haverá hardware local capaz de executar Gemma 4 **E4B** ou **E2B** com latência interativa aceitável após warmup. Se isso falhar, o benchmark principal usa o menor modelo local viável e o sistema entra em BLOCKED/REVIEW_REQUIRED conforme política de fail-closed. | Afeta latência, escolha do modelo e vídeo-demo. |
| A-02 | Stack-base do monólito: **Python 3.11**, **Streamlit** para UI única, **Pydantic 2** para contratos, **SQLite** para persistência local, **pytest** para testes. | Afeta estrutura do repositório e scripts de bootstrap. |
| A-03 | O runtime local do Gemma 4 fica atrás de um adaptador, sem acoplamento a um backend único. O backend concreto pode ser trocado desde que preserve multimodalidade local, output estruturado e function calling. | Evita dependência não comprovada de um único runtime. |
| A-04 | Limiar de confiança para campos documentais críticos: `>= 0.75` para confiar diretamente; `0.60–0.74` exige corroboração ou marca ambiguidade; `< 0.60` em campo material gera `REVIEW_REQUIRED`. | Afeta parsing, política de verdade e modo de falha fechada. |
| A-05 | Perfil de ranking genérico publicado no repositório: `FIFO=40`, `CONTRACT_PRIORITY=30`, `RESOURCE_FIT=15`, `CAPACITY_HEADROOM=10`, `WAIT_SLA=5`; `MIN_OPERATIONAL_CAPACITY_PCT=20`; `COMFORT_CAPACITY_PCT=50`. | Afeta cenários S05, S08 e S10. |
| A-06 | No Scenario Pack sintético, `weather_state.json` e `resource_state.json` são considerados snapshots autoritativos e frescos do cenário. | Simplifica benchmark e elimina ambiguidade temporal artificial. |
| A-07 | O pack sintético trabalhará com filas pequenas e filmáveis: até 10 caminhões e até 4 destinos por cenário. | Mantém demo clara e validação local barata. |
| A-08 | Override humano será sempre registrado com um identificador sintético de operador, como `OP-DEMO-01`, nunca com dado pessoal real. | Afeta LGPD, auditabilidade e repositório público. |
| A-09 | Pesos, thresholds e labels publicados serão **genéricos** e deliberadamente não calibrados como política operacional real de um cliente. | Protege IP e evita promessas indevidas. |

---

## 1. Tese de submissão

### 1.1 Tese em uma frase

O **PequiFlux Yard Copilot** é um copiloto multimodal, local-first e auditável que usa **Gemma 4** para transformar ticket/documento, nota operacional e estados de pátio em contexto operacional estruturado; em seguida, um motor determinístico valida restrições críticas, ranqueia candidatos e produz uma recomendação justificável de despacho, com o humano como autoridade final.

### 1.2 O que exatamente está sendo submetido

A submissão não é uma plataforma logística ampla. Ela é um **artefato vertical** com fronteira nítida:

- uma **UI única** e filmável;
- um **fluxo ponta a ponta** com entradas multimodais;
- um **rules engine determinístico**;
- um **Gemma 4** central, porém delimitado;
- um **Scenario Pack sintético** com 10 cenários obrigatórios;
- um **benchmark** contra FIFO puro e baseline heurístico sem Gemma;
- um **repositório público sanitizado**, reproduzível e offline após setup/cache.

### 1.3 Problema que a submissão resolve

O problema não é “otimizar toda a operação”. O problema é mais estreito e, por isso, julgável: **quem deve ser chamado agora, para qual destino, quando a exceção operacional quebra a legitimidade do FIFO puro**.

Em regime nominal, chamar o primeiro caminhão da fila é simples. Em regime de exceção, a ordem de chegada passa a competir com:

- restrições físicas do destino;
- indisponibilidade de recurso;
- bloqueio documental;
- condição da carga;
- incompatibilidade de veículo;
- prioridade contratual;
- necessidade de explicar por que a fila foi quebrada.

O sistema existe para resolver essa tensão sem deslocar a autoridade operacional para o modelo.

### 1.4 Por que este recorte é o recorte correto para a hackathon

Este recorte maximiza densidade demonstrável por unidade de escopo. Ele permite provar, no mesmo fluxo:

1. entrada multimodal realista;
2. interpretação útil com Gemma 4;
3. governança determinística da decisão;
4. auditabilidade da quebra de FIFO;
5. robustez com fail-closed;
6. reprodutibilidade em repositório público.

A submissão perde força se tentar cobrir ERP, balança, mensageria, múltiplas unidades, telemetria ou o PequiFlux completo. Isso dilui a centralidade do Gemma 4, aumenta risco de engenharia, complica sanitização e enfraquece benchmark.

### 1.5 O que Gemma 4 prova nesta submissão

Gemma 4 não está aqui para “embelezar a saída”. Ele precisa agregar valor em três pontos que um baseline heurístico tradicional resolve mal:

1. **parsing multimodal do ticket/documento**;
2. **classificação da exceção quando documento, nota e estado precisam ser reconciliados**;
3. **explicação final controlada em linguagem natural, ancorada em decisão formal**.

Se o sistema só ganhasse em texto bonito e não em `ticket_field_accuracy`, `exception_f1` e `decision_match_at_1`, a tese falharia.

### 1.6 O que esta submissão explicitamente não afirma

Este blueprint não afirma, nem deve insinuar, os pontos abaixo:

- validação de campo em operação real;
- integração produtiva com ERP, balança, WhatsApp, telemetria ou sistema legado;
- otimização global do pátio;
- uso de dados reais de cliente;
- fine-tuning do Gemma 4;
- métricas de negócio não medidas;
- prontidão produtiva para ambiente crítico.

A narrativa correta é: **working proof-of-concept técnico, reproduzível, auditável e benchmarkável**.

---

## 2. PRD orientado à hackathon

### 2.1 Problema de produto

O operador precisa decidir rapidamente **quem chamar** e **para onde despachar** quando o FIFO é insuficiente para preservar segurança operacional e legitimidade organizacional. A dor não é apenas decidir; é **defender a decisão** quando ela quebra a ordem aparente da fila.

### 2.2 Usuários e stakeholders

| Ator | Objetivo | Dor dominante | O que precisa ver |
|---|---|---|---|
| Operador de pátio | Despachar com segurança e rapidez | Exceção quebra a simplicidade do FIFO | Recomendação, destino, motivo, ação disponível |
| Supervisor | Validar ou corrigir decisão | Quebra de FIFO sem trilha gera conflito | Regras disparadas, rejeitados, override |
| Engenharia | Entregar demo robusta em 4 semanas | Escopo cresce e benchmark fica opaco | Contratos, testes, scripts, ADRs |
| Juiz da hackathon | Avaliar inovação, execução e impacto | Demo genérica ou cosmética | Gemma visível, benchmark claro, reprodutibilidade |

### 2.3 Job to be done dominante

Quando houver exceção operacional, o operador quer identificar o próximo caminhão e destino válidos, com justificativa curta e verificável, sem automatizar erro e sem perder a autoridade de bloquear ou sobrescrever a sugestão.

### 2.4 Objetivo funcional mínimo do produto

Dado:

- um `queue.csv`,
- um ticket em PDF ou imagem,
- uma nota do operador,
- um `weather_state.json`,
- um `resource_state.json`,

o sistema deve devolver:

- caminhão recomendado;
- destino recomendado;
- restrições consideradas;
- justificativa auditável;
- mensagem curta ao motorista;
- ação humana disponível (`approve`, `block`, `override`).

### 2.5 Escopo incluído

| Item | Incluído |
|---|---|
| Ingestão de CSV da fila | Sim |
| Ingestão de ticket PDF/imagem | Sim |
| Nota textual do operador | Sim |
| Estado de clima e recurso | Sim |
| Parsing multimodal com Gemma 4 | Sim |
| Classificação de exceção | Sim |
| Tool calling controlado | Sim |
| Validação determinística de hard constraints | Sim |
| Ranking explicável | Sim |
| Audit payload imutável | Sim |
| UI única filmável | Sim |
| Benchmark com 3 variantes | Sim |
| Fail-closed explicito | Sim |

### 2.6 Fora de escopo

| Item | Fora de escopo |
|---|---|
| ERP, balança, WhatsApp, telemetria real | Sim |
| Otimizador global de pátio como núcleo da submissão | Sim |
| PequiFlux completo, multiunidade, multiusuário | Sim |
| Fine-tuning do modelo | Sim |
| Dados reais de operação | Sim |
| Validação em campo | Sim |

### 2.7 Critérios de sucesso do produto

| Dimensão | Critério |
|---|---|
| Segurança operacional | `constraint_violation_rate = 0` para o sistema completo |
| Valor de IA | Ganho sobre o baseline heurístico em `ticket_field_accuracy`, `exception_f1` e `decision_match_at_1` |
| Auditabilidade | 100% das quebras de FIFO e overrides com trilha reconstruível |
| Operabilidade | UI permite aprovar, bloquear ou sobrescrever |
| Reprodutibilidade | Terceiro executa bootstrap, demo e benchmark a partir do repositório |
| Robustez | Falha induzida gera BLOCKED ou REVIEW_REQUIRED; nunca travamento opaco |

### 2.8 Definição de pronto da submissão

A submissão só é considerada pronta quando todos os itens abaixo forem verdadeiros ao mesmo tempo:

1. os 10 cenários obrigatórios executam em lote sem edição manual;
2. o fluxo completo roda localmente após setup/cache;
3. o benchmark exporta relatório comparando `fifo`, `heuristic` e `full`;
4. a UI mostra acima da dobra a recomendação, as restrições, a ação humana e um painel curto que torne a centralidade do Gemma visível;
5. toda quebra de FIFO e todo override têm trilha auditável persistida;
6. o repositório público contém somente dados e artefatos sintéticos.

---

## 3. Requisitos funcionais e não funcionais verificáveis

### 3.1 Hard constraints publicadas

As hard constraints são o núcleo normativo do artefato. Elas devem residir em código versionado, não em prompt.

| ID | Nome | Regra | Tipo |
|---|---|---|---|
| HC-01 | `OPEN_DESTINATION_BLOCKED_BY_RAIN` | Se `weather_state.precipitation != "none"` e o destino tiver `exposure="open"`, o par caminhão-destino é inelegível. | Hard |
| HC-02 | `WET_LOAD_REQUIRES_COMPATIBLE_DESTINATION` | Se `parsed_ticket.load_condition="wet"`, o destino deve ser compatível com carga úmida; caso contrário, o par é inelegível. | Hard |
| HC-03 | `DOWN_OR_BLOCKED_RESOURCE_CANNOT_RECEIVE` | Se o recurso/destino estiver `down` ou `blocked`, nenhum despacho pode usar esse recurso. | Hard |
| HC-04 | `DOCUMENT_BLOCK_PREVENTS_DISPATCH` | Se `document_status != "clear"` ou `document_block_flags` não estiver vazio, o caminhão é inelegível para despacho automático. | Hard |
| HC-05 | `VEHICLE_DESTINATION_COMPATIBILITY` | O `vehicle_type` do caminhão deve estar em `allowed_vehicle_types` do destino/recurso. | Hard |
| HC-06 | `MIN_OPERATIONAL_CAPACITY_REQUIRED` | Se `capacity_pct < MIN_OPERATIONAL_CAPACITY_PCT`, o destino é inelegível. Entre `MIN_OPERATIONAL_CAPACITY_PCT` e `COMFORT_CAPACITY_PCT`, aplica-se penalidade de ranking, não bloqueio absoluto. | Hard + Soft |
| HC-07 | `OVERRIDE_CANNOT_BYPASS_HARD_CONSTRAINTS` | Override humano exige justificativa explícita e só pode selecionar pares que não falhem HC-01..HC-06. Se o operador tentar forçar par inelegível, o sistema responde `REVIEW_REQUIRED` ou mantém bloqueio. | Hard de governança |

### 3.2 Regras de política não hard

As regras abaixo são publicadas como política versionada. Elas podem justificar quebra de FIFO, mas nunca podem anular HC-01..HC-07.

| ID | Nome | Regra |
|---|---|---|
| PR-01 | `FIFO_DEFAULT` | Na ausência de vantagem técnica relevante, a fila deve ser preservada. |
| PR-02 | `CONTRACT_PRIORITY_MAY_BREAK_FIFO` | Caminhão com `contract_priority_flag=true` pode superar FIFO entre candidatos elegíveis. |
| PR-03 | `REDUCED_CAPACITY_PENALTY` | Destino com capacidade acima do mínimo mas abaixo do conforto perde score. |
| PR-04 | `WAIT_SLA_PRESSURE` | Caminhões com espera excessiva podem receber pequeno bônus, sem anular hard constraints. |
| PR-05 | `NO_VALID_PAIR_BLOCKS_AUTODISPATCH` | Se não houver par elegível e a evidência for suficiente, o resultado é `BLOCKED`, não improvisação. |

### 3.3 Requisitos funcionais

| ID | Requisito | Critério de aceite |
|---|---|---|
| RF-01 | Ingerir `queue.csv` e produzir snapshot canônico com posições FIFO estáveis | 100% das linhas válidas entram; linhas inválidas produzem erro formal |
| RF-02 | Ingerir ticket PDF/imagem e produzir `ParsedTicket` com campos críticos e confiança | Cada cenário com ticket gera JSON válido contendo pelo menos `document_status`, `load_condition`, `vehicle_type`, `parse_confidence` |
| RF-03 | Capturar nota do operador, clima e recurso como entradas formais | As três entradas aparecem na trilha de auditoria |
| RF-04 | Classificar exceção primária e secundárias | Retorna `primary_exception`, `severity`, `affected_resources`, `ambiguities`, `needs_human_review` |
| RF-05 | Validar hard constraints por código determinístico antes de qualquer despacho | Nenhuma decisão final existe sem `hard_constraints_checked` |
| RF-06 | Ranquear candidatos elegíveis e propor um par caminhão-destino | Toda execução retorna recomendação única, `BLOCKED` ou `REVIEW_REQUIRED` |
| RF-07 | Permitir `approve`, `block` e `override` | A UI registra ação e motivo; override inválido não comita |
| RF-08 | Gerar justificativa auditável e `reason_summary` | Toda decisão inclui regras disparadas, rejeitados e proveniência |
| RF-09 | Gerar mensagem curta ao motorista | Mensagem <= 220 caracteres e coerente com `decision_status` |
| RF-10 | Persistir decisão, evidência, regras e ação humana | Cada fluxo recebe `decision_id` e registro imutável correspondente |
| RF-11 | Rodar Scenario Pack completo por CLI | Um comando único executa os 10 cenários e exporta relatório |

### 3.4 Requisitos não funcionais

| ID | Requisito | Meta verificável |
|---|---|---|
| RNF-01 | Latência mediana do fluxo completo | `p50 <= 8s` em hardware de referência (**ASSUNÇÃO A-01**) |
| RNF-02 | Latência `p95` do fluxo completo | `p95 <= 15s` |
| RNF-03 | Tempo do rules engine | `p95 <= 300ms` por cenário |
| RNF-04 | Violação de hard constraints no sistema completo | `0%` |
| RNF-05 | Reprodutibilidade em ambiente limpo | Bootstrap + run em `<= 20 min` após obtenção/caching dos pesos |
| RNF-06 | Disponibilidade da demo no pack obrigatório | `10/10` cenários executam sequencialmente |
| RNF-07 | Operação local-first | Após setup/cache, o pack roda sem internet |
| RNF-08 | Falha do modelo não paralisa o fluxo | 100% das falhas induzidas produzem `BLOCKED` ou `REVIEW_REQUIRED` |
| RNF-09 | Logs estruturados | 100% dos fluxos geram log JSONL com campos mínimos |
| RNF-10 | Audit completeness | `100%` dos payloads finais contêm os campos obrigatórios |

### 3.5 Requisitos de segurança e sanitização

| ID | Requisito | Critério de aceite |
|---|---|---|
| SEC-01 | Repositório público só com dados sintéticos | Checklist pré-publicação concluído |
| SEC-02 | Prompts crus, chain-of-thought e documentos reais não persistem por padrão | Inspeção de logs confirma ausência |
| SEC-03 | IDs visíveis são sintéticos e estáveis | Nenhum identificador reversível |
| SEC-04 | Segredos e endpoints produtivos não entram no repo | `0 findings` em secret scan |

### 3.6 Distinção entre `BLOCKED` e `REVIEW_REQUIRED`

Essa distinção precisa ser consistente em todo o sistema.

- **`BLOCKED`**: o sistema tem evidência suficiente para concluir que **não existe despacho automático seguro/permitido no momento**. Exemplo: documento bloqueado, recurso indisponível, fila vazia, nenhum par elegível sob fatos claros.
- **`REVIEW_REQUIRED`**: o sistema **não tem verdade suficiente** para automatizar. Exemplo: documento ilegível em campo material, conflito grave entre documento e estado local, tentativa de override para par inelegível, falha persistente do modelo sem estado seguro de revisao.

---

## 4. Arquitetura de software

### 4.1 Direcionadores arquiteturais

1. **Determinismo onde existe risco operacional.** Toda elegibilidade crítica precisa ser calculável por código puro e testável.
2. **Gemma sob contrato.** O modelo produz contexto estruturado, tool intents e explicação natural, mas não muta estado autoritativo.
3. **Fail-closed para decisão automática.** Quando a verdade é insuficiente, o sistema exige revisão.
4. **Proveniência explícita.** Todo campo relevante precisa apontar sua origem.
5. **Reprodutibilidade por design.** Cenários, métricas e saídas precisam ser reexecutáveis por um terceiro.
6. **Monólito modular.** Menor overhead operacional e maior velocidade de entrega para a janela da hackathon.

### 4.2 Arquitetura alvo do monólito modular

```text
repo/
├─ app/
│  ├─ ui/
│  │  └─ streamlit_app.py
│  ├─ orchestration/
│  │  ├─ orchestrator.py
│  │  ├─ state_machine.py
│  │  └─ truth_resolver.py
│  ├─ gemma/
│  │  ├─ adapter.py
│  │  ├─ prompts.py
│  │  ├─ schemas.py
│  │  ├─ tool_gateway.py
│  │  └─ fallback.py        # guarda que proibe fallback operacional
│  ├─ adapters/
│  │  ├─ csv_adapter.py
│  │  ├─ document_adapter.py
│  │  ├─ note_adapter.py
│  │  └─ state_adapter.py
│  ├─ domain/
│  │  ├─ models.py
│  │  ├─ enums.py
│  │  ├─ constraints.py
│  │  ├─ ranking.py
│  │  ├─ policy.py
│  │  └─ errors.py
│  ├─ audit/
│  │  ├─ payloads.py
│  │  └─ service.py
│  ├─ storage/
│  │  ├─ sqlite_store.py
│  │  ├─ jsonl_logger.py
│  │  └─ migrations.sql
│  └─ services/
│     ├─ parser.py
│     ├─ exception_classifier.py
│     ├─ decision_builder.py
│     └─ driver_message.py
├─ scenarios/
│  ├─ manifest.json
│  ├─ schemas/
│  ├─ common/
│  └─ cases/
├─ bench/
│  ├─ runner.py
│  ├─ metrics.py
│  └─ reports/
├─ tests/
│  ├─ unit/
│  ├─ contract/
│  ├─ golden/
│  ├─ integration/
│  ├─ e2e/
│  └─ failure/
├─ scripts/
│  ├─ bootstrap.sh
│  ├─ prewarm_models.sh
│  ├─ run_demo.sh
│  ├─ run_benchmark.sh
│  └─ prepublish_check.sh
└─ docs/
   ├─ technical_blueprint.md
   ├─ architecture.md
   ├─ adr/
   └─ writeup_assets/
```

### 4.3 Responsabilidade de cada módulo

| Módulo | Responsabilidade |
|---|---|
| `ui` | Coletar entradas, renderizar recomendação, permitir ação humana, exibir trilha de auditoria |
| `orchestration` | Coordenar o fluxo ponta a ponta, controlar estados, chamar módulos e encerrar em `BLOCKED` ou `REVIEW_REQUIRED` quando faltar verdade operacional |
| `gemma` | Empacotar prompts, validar outputs estruturados, controlar tool calling, isolar runtime |
| `adapters` | Ler CSV, ticket/documento, nota e estados, produzindo insumos internos canônicos |
| `domain` | Modelos de domínio, enums, hard constraints, ranking, policy profile, códigos de erro |
| `services` | Parsing, classificação de exceção, composição de decisão e de mensagem |
| `audit` | Construir payloads auditáveis e formatar trilha de evidência |
| `storage` | Persistência local em SQLite e JSONL |
| `bench` | Executar variantes e métricas, exportar relatórios |
| `tests` | Garantir correção dos módulos, contratos, cenários e falhas induzidas |

### 4.4 Fluxo ponta a ponta: ingestão -> normalização -> interpretação com Gemma -> validação determinística -> ranking -> auditoria -> UI -> ação humana

#### 4.4.1 Visão geral do fluxo

| Etapa | Módulo(s) | Entrada | Saída | Invariantes |
|---|---|---|---|---|
| 1. Ingestão | `adapters/*` | arquivos do cenário + nota + estados | `DecisionRequest` bruto | Nenhum estado autoritativo é alterado |
| 2. Normalização | `normalize_queue_snapshot` | linhas do CSV | `QueueSnapshot` | FIFO explícito e IDs únicos |
| 3. Parsing documental | `parse_ticket_document` + `gemma.adapter` | `DocumentBundle` | `ParsedTicket` | Output schema-bound ou erro formal |
| 4. Classificação de exceção | `classify_exception` | ticket parseado + nota + clima + recurso + fila | `ExceptionAssessment` | Label canônica ou `needs_human_review=true` |
| 5. Resolução de verdade | `truth_resolver` | fontes reconciliadas | `InterpretedContext` | Hierarquia de fontes aplicada e conflitos materializados |
| 6. Validação determinística | `validate_hard_constraints` | contexto + destinos candidatos | `ValidationMatrix` | Só o código decide elegibilidade |
| 7. Ranking | `rank_candidates` | matriz validada + policy profile | `RankedCandidates` | Nenhum par fora da matriz entra no ranking |
| 8. Composição da decisão | `decision_builder` | ranking + contexto | `DecisionPreview` | Status coerente com evidência e regras |
| 9. Auditoria | `generate_audit_payload` | contexto + validação + ranking + preview | `AuditRecord` | Toda quebra de FIFO fica reconstruível |
| 10. Explicação/mensagem | `gemma` e/ou templates controlados | decisão formal | `reason_summary` + `DriverMessage` | Sem chain-of-thought; sem score interno |
| 11. UI | `ui` | payload final | tela única renderizada | Acima da dobra mostra recomendação, restrições e ações |
| 12. Ação humana | `ui` + `storage` | `approve`/`block`/`override` | `DecisionFinalized` | Override exige motivo e não pode burlar HC |

#### 4.4.2 Detalhe operacional por fronteira

**Fronteira A — `Input Adapters -> Orchestrator`**

Entrada: artefatos brutos do cenário ou da UI.  
Saída: `DecisionRequest` com referências, hashes e estados estruturados.  
Contrato: nenhum parser downstream lê arquivo arbitrário diretamente da UI; o orquestrador recebe um objeto formal com paths já validados.

**Fronteira B — `Adapters -> Queue Normalizer`**

Entrada: linhas do `queue.csv`.  
Saída: `QueueSnapshot` com `queue_position`, `arrival_ts`, `wait_minutes`, `status`, `vehicle_type` e demais campos necessários.  
Contrato: o normalizador é a única etapa autorizada a ordenar a fila.

**Fronteira C — `Document Adapter -> Gemma Parser`**

Entrada: `DocumentBundle` contendo referência do arquivo, tipo de conteúdo, hash, texto extraído quando existir e imagens/renderizações de página quando aplicável.  
Saída: `ParsedTicket`.  
Contrato: o parser multimodal não escreve em SQLite, não gera decisão e não executa tool call operacional. Seu papel é apenas transformar documento em estrutura confiável.

**Fronteira D — `ParsedTicket + Note + States -> Exception Classifier`**

Entrada: `ParsedTicket`, nota do operador, clima, recurso e resumo da fila.  
Saída: `ExceptionAssessment`.  
Contrato: a classificação indica o quadro contextual dominante, mas não autoriza despacho.

**Fronteira E — `InterpretedContext -> Tool Gateway`**

Entrada: `InterpretedContext` já reconciliado.  
Saída: execução validada de tools permitidas.  
Contrato: o gateway bloqueia tool name fora da whitelist, argumentos fora do schema, IDs inexistentes, ordem indevida e qualquer tentativa de acesso arbitrário a paths/comandos.

**Fronteira F — `Rules Engine -> Ranking`**

Entrada: `ValidationMatrix`.  
Saída: candidatos elegíveis e score explicável.  
Contrato: o ranking só enxerga pares já validados. Não existe “atalho” do modelo para inserir candidato novo.

**Fronteira G — `DecisionPreview -> Audit Service`**

Entrada: decisão formal, rejeitados, regras, proveniência.  
Saída: `AuditRecord` persistível.  
Contrato: a UI nunca inventa narrativa própria; tudo vem do payload auditável.

**Fronteira H — `UI -> Operator Action Handler`**

Entrada: ação humana e motivo quando exigido.  
Saída: `DecisionFinalized`.  
Contrato: `block` e `override` exigem motivo; `override` só aceita pares elegíveis.

### 4.5 Orquestrador e máquina de estados

#### 4.5.1 Estados do fluxo

```text
RECEIVED
  -> NORMALIZED
  -> PARSED
  -> INTERPRETED
  -> VALIDATED
  -> RANKED
  -> PREVIEW_READY
  -> HUMAN_FINALIZED
```

Estados alternativos:

```text
RECEIVED -> BLOCKED
RECEIVED -> REVIEW_REQUIRED
ANY -> BLOCKED
ANY -> ERROR_TERMINAL (somente para falha de sistema, nunca para resultado operacional silencioso)
```

#### 4.5.2 Regras da máquina de estados

- O fluxo **não** pode pular `VALIDATED`.
- `PREVIEW_READY` só existe se houver pelo menos um par elegível e audit payload gerável.
- `BLOCKED` exige razão formal.
- `REVIEW_REQUIRED` exige pelo menos um código de revisão.
- `HUMAN_FINALIZED` só existe após `approve`, `block` ou `override`.
- `override` inválido não altera preview e gera `REVIEW_REQUIRED` ou erro formal de UI.

#### 4.5.3 Pseudocódigo de referência

```python
def run_decision(request: DecisionRequest) -> FrontEndPayload:
    normalized_queue = normalize_queue_snapshot(request.queue_rows)

    parsed_ticket = parse_ticket_document(
        document_ref=request.ticket_ref,
        content_type=request.ticket_content_type,
        candidate_truck_ids=[row.truck_id for row in normalized_queue.waiting_rows]
    )

    exception = classify_exception(
        parsed_ticket=parsed_ticket,
        operator_note=request.operator_note,
        weather_state=request.weather_state,
        resource_state=request.resource_state,
        queue_snapshot=normalized_queue
    )

    interpreted_context = resolve_truth(
        queue_snapshot=normalized_queue,
        parsed_ticket=parsed_ticket,
        exception_assessment=exception,
        operator_note=request.operator_note,
        weather_state=request.weather_state,
        resource_state=request.resource_state
    )

    if interpreted_context.needs_human_review:
        return build_review_required_payload(interpreted_context)

    validation = validate_hard_constraints(
        normalized_queue=normalized_queue,
        parsed_ticket=interpreted_context.parsed_ticket,
        weather_state=request.weather_state,
        resource_state=request.resource_state,
        candidate_destinations=request.candidate_destinations
    )

    ranking = rank_candidates(
        validation_matrix=validation.validation_matrix,
        policy_profile=request.policy_profile,
        queue_snapshot=normalized_queue,
        exception_assessment=interpreted_context.exception_assessment
    )

    preview = build_decision_preview(
        interpreted_context=interpreted_context,
        validation=validation,
        ranking=ranking
    )

    audit = generate_audit_payload(
        interpreted_context=interpreted_context,
        validation_matrix=validation.validation_matrix,
        ranked_decision=preview,
        operator_action=None
    )

    driver_message = compose_driver_message(
        decision_status=preview.decision_status,
        recommended_truck=preview.recommended_truck,
        recommended_destination=preview.recommended_destination,
        reason_summary=preview.reason_summary
    )

    return build_frontend_payload(preview, audit, driver_message)
```

### 4.6 Persistência local

A persistência deve ser simples, auditável e local.

#### 4.6.1 SQLite

Tabelas mínimas:

| Tabela | Campos principais | Função |
|---|---|---|
| `decision_records` | `decision_id`, `request_id`, `scenario_id`, `variant`, `decision_status`, `recommended_truck_id`, `recommended_destination_id`, `created_at` | Registro principal da decisão |
| `audit_records` | `decision_id`, `audit_json`, `hash_sha256`, `created_at` | Payload auditável imutável |
| `operator_actions` | `action_id`, `decision_id`, `action_type`, `reason`, `before_json`, `after_json`, `actor_id`, `created_at` | Trilha de aprovação, bloqueio e override |
| `benchmark_runs` | `run_id`, `variant`, `scenario_id`, `metrics_json`, `success_flag`, `created_at` | Resultados experimentais |
| `artifact_index` | `artifact_ref`, `sha256`, `content_type`, `created_at` | Integridade e proveniência dos arquivos |

Princípios:

- nunca persistir documento real por padrão;
- persistir **hash**, **ref local** e **metadados mínimos**;
- guardar `audit_json` como payload completo para inspeção;
- jamais depender de DB externo ou serviço gerenciado.

#### 4.6.2 JSONL de logs

Cada linha deve conter, no mínimo:

```json
{
  "ts": "2026-04-04T10:22:00Z",
  "level": "INFO",
  "request_id": "REQ-2026-0007",
  "scenario_id": "S02_RAIN_OPEN",
  "module": "tool_gateway",
  "event_type": "tool_call_executed",
  "tool_name": "validate_hard_constraints",
  "latency_ms": 41,
  "model_id": "gemma4-e4b",
  "decision_status": "PREVIEW_READY",
  "error_code": null
}
```

Campos proibidos por padrão:

- prompt cru;
- chain-of-thought;
- documento bruto;
- nota real de operador fora do pack sintético;
- conteúdo que permita reidentificação.

### 4.7 Observabilidade mínima

Sem depender de APM externo, o sistema deve expor e gravar pelo menos:

| Indicador | Origem | Uso |
|---|---|---|
| `tool_call_error_total` | `tool_gateway` | provar robustez do schema e da state machine |
| `review_or_block_total` | `orchestrator` | medir degradação |
| `invalid_recommendation_total` | `decision_builder` | alvo operacional = 0 |
| `latency_model_ms` | `gemma.adapter` | monitorar custo do Gemma |
| `latency_rules_ms` | `validate_hard_constraints` | provar previsibilidade do motor |
| `latency_end_to_end_ms` | `orchestrator` | benchmark local |
| `audit_completeness_ratio` | `audit.service` | garantir submissão julgável |

### 4.8 Testes

| Camada | O que testar |
|---|---|
| Unitário | cada HC, ranking, tie-break, truth resolver, driver message templates |
| Contract | JSON Schemas, enums, tool payloads, serialização Pydantic |
| Golden | parsing de ticket e classificação nos 10 cenários |
| Integração | fluxo e2e com SQLite, JSONL e UI payload |
| Falha induzida | timeout, tool call inválida, documento ilegível, conflito material |
| Benchmark | rerun das variantes e export de métricas |

Princípio: todo módulo crítico precisa ter teste que prove tanto o caminho feliz quanto o fail-closed.

### 4.9 Estratégia de reprodutibilidade

1. fixar `manifest.json`, `policy_profile.json` e seeds não essenciais;
2. manter scripts únicos para bootstrap, demo, benchmark e prepublish;
3. separar pesos do modelo do Git;
4. versionar os schemas do pack e do front-end;
5. gerar relatórios reproduzíveis em `bench/reports/`;
6. garantir que o repositório rode offline após setup/cache.

---

## 5. Arquitetura específica de Gemma 4

### 5.1 Papel exato do Gemma 4

Gemma 4 é a **camada de interpretação e explicação**, não o sistema de registro nem o árbitro final da elegibilidade operacional.

Ele faz:

1. interpretar ticket PDF/imagem e produzir `ParsedTicket`;
2. ajudar na classificação da exceção quando o contexto é ambíguo;
3. solicitar tools permitidas sob schema e ordem controlados;
4. sintetizar `reason_summary` em linguagem natural a partir da decisão formal;
5. expor ambiguidade explicitamente quando a verdade não é suficiente.

Ele **não** faz:

1. decidir hard constraints;
2. decidir elegibilidade final;
3. persistir estado autoritativo;
4. executar comandos arbitrários;
5. alterar a fila;
6. aprovar override humano;
7. produzir decisão operacional sem validação externa.

### 5.2 Escolha de modelo

De acordo com o recorte descrito no dossiê, a escolha operacional é:

| Papel | Modelo | Justificativa |
|---|---|---|
| Primário | **Gemma 4 E4B** | melhor equilíbrio entre capacidade multimodal, function calling e custo local |
| Fail-closed de modelo | **Gemma 4 E2B** | menor custo e maior tolerância em hardware restrito |
| Ablação opcional | **Gemma 4 26B A4B** | útil apenas se houver hardware sobrando; não deve ser dependência do vídeo |
| Não padrão | **Gemma 4 31B** | pouco aderente ao objetivo local-first da demo |

### 5.3 Adaptador de runtime

O sistema não deve assumir um backend único. O contrato a ser implementado é:

```python
class GemmaRuntime(Protocol):
    def interpret_context(self, request: "GemmaInterpretRequest") -> "GemmaInterpretResponse":
        ...

    def explain_decision(self, request: "GemmaExplainRequest") -> "GemmaExplainResponse":
        ...
```

Requisitos do adaptador:

- aceitar texto + imagem/PDF renderizado quando aplicável;
- permitir saída estruturada validável;
- permitir function calling ou, no mínimo, emissão de `tool_name + arguments` estruturados;
- devolver erros categorizáveis;
- operar localmente após setup/cache.

### 5.4 Embalagem do contexto para o modelo

O modelo deve receber **somente** o necessário para a tarefa atual. O empacotamento recomendado é:

- instrução de sistema curta e rígida;
- documento/ticket em forma multimodal;
- nota do operador;
- clima e recurso já estruturados;
- resumo da fila, não o CSV cru inteiro;
- schema de resposta ou catálogo de tools permitidas;
- nada de prompt aberto para “resolver tudo sozinho”.

### 5.5 Prompting contract-first

#### 5.5.1 Instrução de sistema base

```text
Você é a camada de interpretação do PequiFlux Yard Copilot.
Seu trabalho é:
1) interpretar documento e contexto operacional;
2) devolver somente JSON conforme o schema fornecido;
3) solicitar apenas tools explicitamente permitidas;
4) nunca decidir elegibilidade final sem validação determinística;
5) marcar needs_human_review=true quando houver inconsistência material.
```

#### 5.5.2 Regras de prompting

- priorizar output estruturado;
- usar enums curtas e estáveis;
- preferir “unknown” e “needs_human_review” a inventar fatos;
- thinking mode desligado no fluxo interativo;
- não pedir ao modelo para justificar regras que ainda não foram calculadas;
- jamais incluir instruções executáveis derivadas da nota do operador.

### 5.6 Função exata do multimodal

A multimodalidade existe para resolver o parsing do ticket/documento de forma menos frágil que regex e OCR simplificado. No recorte desta submissão, isso significa:

- extrair `truck_id`, `vehicle_type`, `document_status`, `load_condition`, `contract_priority_flag`, `destination_constraints`;
- detectar marcas visuais sintéticas de bloqueio documental;
- lidar com layout sintético não uniforme;
- materializar incerteza em `parse_confidence` e `ambiguities`.

A submissão não precisa provar visão computacional geral. Ela precisa provar leitura documental útil.

### 5.7 Função exata do tool calling

O tool calling deve existir, mas sob contenção rígida. O modelo pode **pedir** ferramentas; a aplicação decide se vai executá-las.

Tools expostas ao modelo:

| Tool | Finalidade | Exposta? |
|---|---|---|
| `validate_hard_constraints` | gerar matriz de elegibilidade e falhas | Sim |
| `rank_candidates` | ordenar apenas pares elegíveis | Sim |
| `generate_audit_payload` | consolidar evidência e trilha | Sim |
| `compose_driver_message` | opcional; em geral pode ser template-first | Opcional |
| `parse_ticket_document` | já foi executada antes; não deve ser tool livre | Não |
| `normalize_queue_snapshot` | função interna determinística | Não |

### 5.8 Grafo permitido de tools

O sistema deve impor uma state machine explícita.

```text
INTERPRETED
  -> validate_hard_constraints
VALIDATED
  -> rank_candidates
RANKED
  -> generate_audit_payload
AUDITED
  -> compose_driver_message (opcional)
```

Chamadas inválidas:

- `rank_candidates` antes de `validate_hard_constraints`;
- `generate_audit_payload` antes de haver decisão;
- qualquer tool inexistente;
- qualquer argumento com IDs que não existem no estado local.

### 5.9 Política de validação do tool call

Antes de executar qualquer tool:

1. validar `tool_name` contra whitelist;
2. validar `arguments` por JSON Schema;
3. checar enums, cardinalidade, tipos;
4. verificar se todos os IDs referidos existem em `QueueSnapshot` ou `resource_state`;
5. verificar se a tool é permitida no estado atual;
6. registrar tentativa em log estruturado;
7. só então executar.

### 5.10 Tratamento de erro de tool call

Categorias mínimas:

- `UNKNOWN_TOOL`
- `SCHEMA_ERROR`
- `DOMAIN_VALIDATION_ERROR`
- `TOOL_ORDER_ERROR`
- `TIMEOUT`
- `EXECUTION_ERROR`

Política:

- falha de nome ou schema: devolver erro estruturado ao modelo e permitir **uma única tentativa de reparo**;
- segunda falha: abandonar cadeia agentic para o caso e entrar em `BLOCKED` ou `REVIEW_REQUIRED`;
- `TIMEOUT` ou `DOMAIN_VALIDATION_ERROR`: falha fechada imediata, sem loop;
- falha repetida nunca gera “tentativa infinita”.

### 5.11 Política fail-closed

Não existe caminho operacional degradado. Se uma entrada, serviço, tool call ou saída do Gemma for materialmente inválida, o sistema não substitui o componente por heurística automática e não continua com comportamento reduzido.

#### Caminho normal

Gemma interpreta, tool calling validado, regras determinísticas decidem e a UI apresenta `PREVIEW_READY`, `BLOCKED` ou `REVIEW_REQUIRED` com trilha auditável.

#### `BLOCKED`

Ativado quando há verdade suficiente para impedir despacho automático sem escolher um par operacional. Exemplos:

- fila vazia;
- nenhum destino elegível;
- documento explicitamente bloqueado;
- recurso indisponível;
- tentativa de override para par inelegível.

Em `BLOCKED`, não há parser alternativo, modelo substituto, retry silencioso ou mudança de lógica decisória.

#### `REVIEW_REQUIRED`
Ativado quando:

- campo documental material permanece incerto após fail-closed;
- conflito material entre fontes não pode ser resolvido;
- tentativa de override viola hard constraint;
- audit payload não pode ser concluído com integridade;
- não há base suficiente para despacho seguro.

### 5.12 Quando o sistema deve retornar `REVIEW_REQUIRED`

O sistema **deve** retornar `REVIEW_REQUIRED` nos casos abaixo:

1. `parse_confidence < 0.60` em campo que afeta HC-02, HC-04 ou HC-05;
2. documento diz uma coisa, estado local autoritativo diz outra e a divergência afeta elegibilidade;
3. a nota do operador aponta risco relevante, mas o estado local necessário para resolver o conflito está ausente;
4. a cadeia de tools falha de forma persistente;
5. o operador tenta override para um par inelegível;
6. o sistema não consegue construir um audit payload íntegro;
7. o `vehicle_type`, `document_status` ou `load_condition` fica materialmente indeterminado.

### 5.13 O que o front-end pode mostrar do Gemma sem poluir a interface

O front-end deve mostrar **resultados do Gemma**, não chat. O painel visível ao juiz deve conter, no máximo:

- `vehicle_type`;
- `document_status`;
- `load_condition`;
- `primary_exception`;
- `parse_confidence`;
- `needs_human_review`;
- badges das tools chamadas com status `ok/error`.

Não exibir:

- prompt cru;
- tokens;
- chain-of-thought;
- mensagens internas extensas.

---

## 6. Contratos de função / tools

### 6.1 Enums e identificadores básicos

```json
{
  "DecisionStatus": ["PREVIEW_READY", "BLOCKED", "REVIEW_REQUIRED", "APPROVED", "OVERRIDDEN"],
  "OperatorAction": ["approve", "block", "override"],
  "DocumentStatus": ["clear", "blocked", "incomplete", "unknown"],
  "LoadCondition": ["dry", "wet", "unknown"],
  "VehicleType": ["bitrem", "rodotrem", "truck", "unknown"],
  "Severity": ["low", "medium", "high"],
  "Fail-closedMode": ["F0", "BLOCKED", "REVIEW_REQUIRED"]
}
```

Padrão de IDs sintéticos:

- caminhão: `TRK-001`
- destino: `DST-COV-01`
- ticket: `TCK-003`
- decisão: `DEC-2026-010`
- request: `REQ-2026-0007`

### 6.2 `DecisionRequest`

#### Schema mínimo

```json
{
  "$id": "schemas/DecisionRequest.schema.json",
  "type": "object",
  "properties": {
    "request_id": {"type": "string"},
    "scenario_id": {"type": "string"},
    "variant": {"type": "string", "enum": ["fifo", "heuristic", "full"]},
    "queue_csv_ref": {"type": "string"},
    "ticket_ref": {"type": "string"},
    "ticket_content_type": {
      "type": "string",
      "enum": ["application/pdf", "image/png", "image/jpeg"]
    },
    "operator_note": {"type": "string", "maxLength": 2000},
    "weather_state": {
      "type": "object",
      "properties": {
        "precipitation": {"type": "string"},
        "severity": {"type": "string"},
        "timestamp": {"type": "string"}
      },
      "required": ["precipitation", "severity"]
    },
    "resource_state": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "resource_id": {"type": "string"},
          "status": {"type": "string"},
          "capacity_pct": {"type": "number"},
          "resource_type": {"type": "string"},
          "exposure": {"type": "string"},
          "allowed_vehicle_types": {
            "type": "array",
            "items": {"type": "string"}
          }
        },
        "required": ["resource_id", "status", "capacity_pct", "exposure"]
      }
    },
    "policy_profile_version": {"type": "string"},
    "run_mode": {"type": "string", "enum": ["interactive", "benchmark"]}
  },
  "required": [
    "request_id",
    "scenario_id",
    "variant",
    "queue_csv_ref",
    "ticket_ref",
    "ticket_content_type",
    "operator_note",
    "weather_state",
    "resource_state",
    "policy_profile_version",
    "run_mode"
  ],
  "additionalProperties": false
}
```

#### Exemplo

```json
{
  "request_id": "REQ-2026-0007",
  "scenario_id": "S02_RAIN_OPEN",
  "variant": "full",
  "queue_csv_ref": "scenarios/cases/S02_RAIN_OPEN/queue.csv",
  "ticket_ref": "scenarios/cases/S02_RAIN_OPEN/ticket_01.pdf",
  "ticket_content_type": "application/pdf",
  "operator_note": "Começou a chover e a moega aberta foi bloqueada.",
  "weather_state": {
    "precipitation": "rain",
    "severity": "medium",
    "timestamp": "2026-04-04T10:15:00Z"
  },
  "resource_state": [
    {
      "resource_id": "DST-OPEN-01",
      "status": "blocked",
      "capacity_pct": 0,
      "resource_type": "hopper",
      "exposure": "open",
      "allowed_vehicle_types": ["bitrem", "rodotrem", "truck"]
    },
    {
      "resource_id": "DST-COV-01",
      "status": "available",
      "capacity_pct": 90,
      "resource_type": "hopper",
      "exposure": "covered",
      "allowed_vehicle_types": ["bitrem", "truck"]
    }
  ],
  "policy_profile_version": "v1-demo",
  "run_mode": "interactive"
}
```

### 6.3 `InterpretedContext`

#### Schema mínimo

```json
{
  "$id": "schemas/InterpretedContext.schema.json",
  "type": "object",
  "properties": {
    "parsed_ticket": {
      "type": "object",
      "properties": {
        "ticket_id": {"type": ["string", "null"]},
        "truck_id": {"type": ["string", "null"]},
        "vehicle_type": {"type": "string"},
        "document_status": {"type": "string"},
        "document_block_flags": {
          "type": "array",
          "items": {"type": "string"}
        },
        "load_condition": {"type": "string"},
        "contract_priority_flag": {"type": "boolean"},
        "destination_constraints": {
          "type": "array",
          "items": {"type": "string"}
        },
        "parse_confidence": {"type": "number"},
        "ambiguities": {
          "type": "array",
          "items": {"type": "string"}
        }
      },
      "required": [
        "vehicle_type",
        "document_status",
        "load_condition",
        "contract_priority_flag",
        "parse_confidence"
      ]
    },
    "exception_assessment": {
      "type": "object",
      "properties": {
        "primary_exception": {"type": "string"},
        "secondary_exceptions": {
          "type": "array",
          "items": {"type": "string"}
        },
        "severity": {"type": "string"},
        "affected_resources": {
          "type": "array",
          "items": {"type": "string"}
        },
        "ambiguities": {
          "type": "array",
          "items": {"type": "string"}
        },
        "needs_human_review": {"type": "boolean"}
      },
      "required": ["primary_exception", "severity", "needs_human_review"]
    },
    "truth_resolution": {
      "type": "object",
      "properties": {
        "authoritative_sources": {
          "type": "array",
          "items": {"type": "string"}
        },
        "material_conflicts": {
          "type": "array",
          "items": {"type": "string"}
        }
      },
      "required": ["authoritative_sources", "material_conflicts"]
    },
    "provenance": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "field": {"type": "string"},
          "source": {
            "type": "string",
            "enum": [
              "queue_snapshot",
              "ticket_document",
              "operator_note",
              "weather_state",
              "resource_state"
            ]
          },
          "confidence": {"type": ["number", "null"]}
        },
        "required": ["field", "source"]
      }
    },
    "needs_human_review": {"type": "boolean"},
    "review_reasons": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "required": [
    "parsed_ticket",
    "exception_assessment",
    "truth_resolution",
    "provenance",
    "needs_human_review",
    "review_reasons"
  ],
  "additionalProperties": false
}
```

#### Exemplo

```json
{
  "parsed_ticket": {
    "ticket_id": "TCK-001",
    "truck_id": "TRK-001",
    "vehicle_type": "bitrem",
    "document_status": "clear",
    "document_block_flags": [],
    "load_condition": "dry",
    "contract_priority_flag": false,
    "destination_constraints": [],
    "parse_confidence": 0.88,
    "ambiguities": []
  },
  "exception_assessment": {
    "primary_exception": "RAIN_OPEN_HOPPER_BLOCK",
    "secondary_exceptions": [],
    "severity": "high",
    "affected_resources": ["DST-OPEN-01"],
    "ambiguities": [],
    "needs_human_review": false
  },
  "truth_resolution": {
    "authoritative_sources": ["queue_snapshot", "weather_state", "resource_state"],
    "material_conflicts": []
  },
  "provenance": [
    {"field": "vehicle_type", "source": "ticket_document", "confidence": 0.88},
    {"field": "primary_exception", "source": "operator_note", "confidence": null},
    {"field": "resource_status", "source": "resource_state", "confidence": null}
  ],
  "needs_human_review": false,
  "review_reasons": []
}
```

### 6.4 Payload de entrada do adaptador Gemma

```json
{
  "$id": "schemas/GemmaInterpretRequest.schema.json",
  "type": "object",
  "properties": {
    "request_id": {"type": "string"},
    "task": {"type": "string", "enum": ["interpret_context", "explain_decision"]},
    "model_preference": {"type": "string"},
    "document_bundle": {"type": "object"},
    "queue_summary": {"type": "object"},
    "operator_note": {"type": "string"},
    "weather_state": {"type": "object"},
    "resource_state": {"type": "array"},
    "response_schema": {"type": "string"},
    "allowed_tools": {
      "type": "array",
      "items": {"type": "string"}
    },
    "thinking_mode": {"type": "boolean"}
  },
  "required": [
    "request_id",
    "task",
    "document_bundle",
    "queue_summary",
    "operator_note",
    "weather_state",
    "resource_state",
    "response_schema",
    "allowed_tools",
    "thinking_mode"
  ],
  "additionalProperties": false
}
```

#### Exemplo

```json
{
  "request_id": "REQ-2026-0007",
  "task": "interpret_context",
  "model_preference": "gemma4-e4b",
  "document_bundle": {
    "document_ref": "scenarios/cases/S02_RAIN_OPEN/ticket_01.pdf",
    "content_type": "application/pdf",
    "sha256": "7f7d1b...",
    "rendered_pages": ["cache/doc_pages/TCK-001_p1.png"],
    "text_extract": "TRK-001 ... carga seca ..."
  },
  "queue_summary": {
    "queue_version": "v1",
    "top_fifo_ids": ["TRK-001", "TRK-002", "TRK-003", "TRK-005"],
    "waiting_count": 6
  },
  "operator_note": "Começou a chover e a moega aberta foi bloqueada.",
  "weather_state": {"precipitation": "rain", "severity": "medium"},
  "resource_state": [
    {"resource_id": "DST-OPEN-01", "status": "blocked", "capacity_pct": 0, "exposure": "open"},
    {"resource_id": "DST-COV-01", "status": "available", "capacity_pct": 90, "exposure": "covered"}
  ],
  "response_schema": "InterpretedContext",
  "allowed_tools": [
    "validate_hard_constraints",
    "rank_candidates",
    "generate_audit_payload"
  ],
  "thinking_mode": false
}
```

### 6.5 Payload de saída do adaptador Gemma

```json
{
  "$id": "schemas/GemmaInterpretResponse.schema.json",
  "type": "object",
  "properties": {
    "status": {"type": "string", "enum": ["ok", "error"]},
    "parsed_ticket": {"type": "object"},
    "exception_assessment": {"type": "object"},
    "ambiguities": {
      "type": "array",
      "items": {"type": "string"}
    },
    "provenance": {
      "type": "array",
      "items": {"type": "object"}
    },
    "requested_tool_call": {
      "type": ["object", "null"],
      "properties": {
        "tool_name": {"type": "string"},
        "arguments": {"type": "object"}
      }
    },
    "needs_human_review": {"type": "boolean"},
    "error_code": {"type": ["string", "null"]}
  },
  "required": [
    "status",
    "parsed_ticket",
    "exception_assessment",
    "ambiguities",
    "provenance",
    "requested_tool_call",
    "needs_human_review",
    "error_code"
  ],
  "additionalProperties": false
}
```

#### Exemplo

```json
{
  "status": "ok",
  "parsed_ticket": {
    "ticket_id": "TCK-001",
    "truck_id": "TRK-001",
    "vehicle_type": "bitrem",
    "document_status": "clear",
    "document_block_flags": [],
    "load_condition": "dry",
    "contract_priority_flag": false,
    "destination_constraints": [],
    "parse_confidence": 0.88,
    "ambiguities": []
  },
  "exception_assessment": {
    "primary_exception": "RAIN_OPEN_HOPPER_BLOCK",
    "secondary_exceptions": [],
    "severity": "high",
    "affected_resources": ["DST-OPEN-01"],
    "ambiguities": [],
    "needs_human_review": false
  },
  "ambiguities": [],
  "provenance": [
    {"field": "vehicle_type", "source": "ticket_document", "confidence": 0.88},
    {"field": "primary_exception", "source": "operator_note", "confidence": null}
  ],
  "requested_tool_call": {
    "tool_name": "validate_hard_constraints",
    "arguments": {
      "candidate_trucks": ["TRK-001", "TRK-002", "TRK-003", "TRK-005"],
      "candidate_destinations": ["DST-OPEN-01", "DST-COV-01"]
    }
  },
  "needs_human_review": false,
  "error_code": null
}
```

### 6.6 Matriz de validação de hard constraints

```json
{
  "$id": "schemas/ValidationMatrix.schema.json",
  "type": "object",
  "properties": {
    "validation_matrix": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "truck_id": {"type": "string"},
          "destination_id": {"type": "string"},
          "eligible": {"type": "boolean"},
          "failed_constraints": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "constraint_id": {"type": "string"},
                "severity": {"type": "string"},
                "source": {"type": "string"},
                "detail": {"type": "string"}
              },
              "required": ["constraint_id", "severity", "source", "detail"]
            }
          }
        },
        "required": ["truck_id", "destination_id", "eligible", "failed_constraints"]
      }
    },
    "global_blocks": {
      "type": "array",
      "items": {"type": "string"}
    },
    "policy_profile_version": {"type": "string"},
    "validated_at": {"type": "string"}
  },
  "required": ["validation_matrix", "global_blocks", "policy_profile_version", "validated_at"],
  "additionalProperties": false
}
```

#### Exemplo

```json
{
  "validation_matrix": [
    {
      "truck_id": "TRK-001",
      "destination_id": "DST-OPEN-01",
      "eligible": false,
      "failed_constraints": [
        {
          "constraint_id": "HC-01",
          "severity": "hard",
          "source": "weather_state",
          "detail": "Destino aberto bloqueado por chuva."
        }
      ]
    },
    {
      "truck_id": "TRK-001",
      "destination_id": "DST-COV-01",
      "eligible": true,
      "failed_constraints": []
    }
  ],
  "global_blocks": [],
  "policy_profile_version": "v1-demo",
  "validated_at": "2026-04-04T10:22:00Z"
}
```

### 6.7 Payload auditável final

```json
{
  "$id": "schemas/AuditRecord.schema.json",
  "type": "object",
  "properties": {
    "decision_id": {"type": "string"},
    "request_id": {"type": "string"},
    "scenario_id": {"type": "string"},
    "variant": {"type": "string"},
    "hard_constraints_checked": {
      "type": "array",
      "items": {"type": "object"}
    },
    "fired_rules": {
      "type": "array",
      "items": {"type": "string"}
    },
    "rejected_candidates": {
      "type": "array",
      "items": {"type": "object"}
    },
    "recommended_pair": {
      "type": ["object", "null"]
    },
    "fifo_break": {"type": "boolean"},
    "provenance": {
      "type": "array",
      "items": {"type": "object"}
    },
    "operator_action": {
      "type": ["object", "null"]
    },
    "latencies_ms": {"type": "object"},
    "source_hashes": {"type": "object"},
    "created_at": {"type": "string"}
  },
  "required": [
    "decision_id",
    "request_id",
    "scenario_id",
    "variant",
    "hard_constraints_checked",
    "fired_rules",
    "rejected_candidates",
    "recommended_pair",
    "fifo_break",
    "provenance",
    "operator_action",
    "latencies_ms",
    "source_hashes",
    "created_at"
  ],
  "additionalProperties": false
}
```

#### Exemplo

```json
{
  "decision_id": "DEC-2026-010",
  "request_id": "REQ-2026-0007",
  "scenario_id": "S02_RAIN_OPEN",
  "variant": "full",
  "hard_constraints_checked": [
    {
      "constraint_id": "HC-01",
      "status": "failed_for_TRK-001_on_DST-OPEN-01",
      "scope": "pair",
      "evidence_ref": "weather_state"
    }
  ],
  "fired_rules": [
    "PR-01_FIFO_DEFAULT",
    "PR-03_REDUCED_CAPACITY_PENALTY"
  ],
  "rejected_candidates": [
    {"truck_id": "TRK-001", "destination_id": "DST-OPEN-01", "reason": "HC-01"},
    {"truck_id": "TRK-002", "destination_id": "DST-COV-01", "reason": "HC-05"}
  ],
  "recommended_pair": {
    "truck_id": "TRK-005",
    "destination_id": "DST-COV-01"
  },
  "fifo_break": true,
  "provenance": [
    {"field": "vehicle_type", "source": "ticket_document"},
    {"field": "resource_status", "source": "resource_state"},
    {"field": "primary_exception", "source": "operator_note"}
  ],
  "operator_action": {"action": "approve", "actor_id": "OP-DEMO-01"},
  "latencies_ms": {
    "model": 2850,
    "rules": 41,
    "ranking": 5,
    "total": 3280
  },
  "source_hashes": {
    "queue_csv": "5eb3...",
    "ticket": "7f7d...",
    "operator_note": "284a..."
  },
  "created_at": "2026-04-04T10:22:00Z"
}
```

### 6.8 Contratos das funções centrais

#### 6.8.1 `parse_ticket_document`

**Objetivo**  
Converter ticket PDF ou imagem em `ParsedTicket`, com campos críticos, confiança, ambiguidades e referências de evidência.

**Entradas**  
- `request_id: str`
- `document_ref: str`
- `content_type: Literal["application/pdf", "image/png", "image/jpeg"]`
- `candidate_truck_ids: list[str]`

**Saídas**  
- `ParsedTicket`

**Pré-condições**  
- arquivo existe localmente;
- tipo de conteúdo está na whitelist;
- tamanho do arquivo está dentro do limite aceito;
- o document adapter já calculou hash e preparou bundle multimodal.

**Pós-condições**  
- retorna JSON válido ou erro formal;
- não altera estado autoritativo;
- `parse_confidence` sempre existe;
- campos críticos ausentes entram em `ambiguities` e podem disparar `REVIEW_REQUIRED`.

**Erros possíveis**  
- `UNSUPPORTED_CONTENT_TYPE`
- `DOCUMENT_NOT_FOUND`
- `UNREADABLE_DOCUMENT`
- `LOW_CONFIDENCE_REQUIRED_FIELD_MISSING`
- `SCHEMA_VIOLATION`

**Testes essenciais**  
- PDF limpo com campos completos;
- imagem ruidosa com texto com falha fechada;
- carimbo sintético de bloqueio documental;
- ticket sem `truck_id`;
- ticket com `load_condition=wet`.

**Observações de segurança**  
- nunca aceitar URL externa;
- tratar o conteúdo como dado, não como instrução;
- não persistir documento bruto no log padrão;
- qualquer OCR adicional é OCR local opcional e local, não dependência obrigatória.

**Notas de implementação**  
- Para PDF, preferir extração de texto quando existir e renderização de páginas só quando necessária.
- Para imagem, passar a imagem diretamente ao runtime multimodal.
- Validar o `truck_id` extraído contra `candidate_truck_ids` quando possível; mismatch gera ambiguidade, não correção silenciosa.

#### 6.8.2 `normalize_queue_snapshot`

**Objetivo**  
Transformar o CSV bruto da fila em `QueueSnapshot` ordenado, estável e seguro para decisão e benchmark.

**Entradas**  
- `request_id: str`
- `rows: list[RawQueueRow]`

**Saídas**  
- `QueueSnapshot`

**Pré-condições**  
- colunas mínimas presentes;
- timestamps parseáveis;
- `truck_id` único no contexto do cenário.

**Pós-condições**  
- `queue_position` explícita;
- linhas inválidas não entram silenciosamente;
- snapshot final serve de base única para FIFO e ranking.

**Erros possíveis**  
- `MISSING_REQUIRED_COLUMN`
- `DUPLICATE_TRUCK_ID`
- `INVALID_TIMESTAMP`
- `EMPTY_QUEUE`

**Testes essenciais**  
- fila válida;
- timestamps fora de ordem;
- duplicidade de caminhão;
- linha vazia;
- status desconhecido.

**Observações de segurança**  
- neutralizar formula injection em eventual reexportação;
- não aceitar colunas que alterem política sem schema;
- toda transformação deve ser determinística.

**Notas de implementação**  
- `wait_minutes` pode ser calculado contra `request.received_at` ou contra o timestamp do cenário; no pack sintético, usar snapshot fixo do cenário.
- Em caso de `EMPTY_QUEUE`, o fluxo termina em `BLOCKED` com razão `EMPTY_QUEUE`.

#### 6.8.3 `classify_exception`

**Objetivo**  
Classificar a exceção operacional dominante com abordagem híbrida: regra simples primeiro, Gemma quando a evidência exigir interpretação contextual.

**Entradas**  
- `request_id: str`
- `parsed_ticket: ParsedTicket | None`
- `operator_note: str`
- `weather_state: WeatherState`
- `resource_state: list[ResourceState]`
- `queue_snapshot: QueueSnapshot`

**Saídas**  
- `ExceptionAssessment`

**Pré-condições**  
- clima e recurso presentes;
- vocabulário de exceções versionado;
- fila minimamente normalizada.

**Pós-condições**  
- sempre retorna label canônica ou `needs_human_review=true`;
- a classificação não despacha nada por si;
- ambiguidades ficam explícitas.

**Erros possíveis**  
- `MISSING_CONTEXT`
- `UNRESOLVED_CONTRADICTION`
- `INVALID_ENUM`
- `LOW_CONFIDENCE_AMBIGUITY`

**Testes essenciais**  
- os 10 cenários obrigatórios;
- conflito entre nota e estado local;
- caso sem exceção;
- múltiplos sinais simultâneos.

**Observações de segurança**  
- a nota do operador é tratada como dado delimitado;
- qualquer prompt injection no texto da nota deve ser neutralizado pelo template;
- a classificação não pode gerar efeitos colaterais.

**Notas de implementação**  
- casos óbvios a partir do estado local, como `resource.status="down"`, podem ser classificados sem chamar o modelo para economizar latência;
- mesmo quando a exceção é óbvia, Gemma continua central via parsing do ticket e/ou explicação final.

#### 6.8.4 `validate_hard_constraints`

**Objetivo**  
Aplicar HC-01..HC-07 em pares caminhão-destino de forma puramente determinística.

**Entradas**  
- `request_id: str`
- `normalized_queue: QueueSnapshot`
- `parsed_ticket: ParsedTicket | None`
- `weather_state: WeatherState`
- `resource_state: list[ResourceState]`
- `candidate_destinations: list[str]`

**Saídas**  
- `ValidationMatrix`

**Pré-condições**  
- IDs válidos e conhecidos;
- estados de clima e recurso presentes;
- destinos candidatos conhecidos.

**Pós-condições**  
- nenhum par fora da matriz pode ser usado no ranking;
- a saída não depende do modelo;
- toda inelegibilidade aponta `constraint_id` e `source`.

**Erros possíveis**  
- `UNKNOWN_DESTINATION`
- `UNKNOWN_TRUCK_ID`
- `MISSING_RESOURCE_STATE`
- `SCHEMA_VIOLATION`

**Testes essenciais**  
- um teste por HC-01..HC-07;
- combinação de bloqueios simultâneos;
- cenário-base sem exceção;
- ausência de destino elegível.

**Observações de segurança**  
- função pura, sem side effects;
- dados ausentes geram erro formal, nunca default silencioso;
- override humano não executa essa função em modo especial: ele passa pela mesma validação.

**Notas de implementação**  
- gerar matriz completa do produto cartesiano `caminhões candidatos x destinos candidatos`;
- em benchmark sintético, esse custo é pequeno e facilita auditabilidade.

#### 6.8.5 `rank_candidates`

**Objetivo**  
Ordenar apenas os pares elegíveis, preservando FIFO quando não houver justificativa técnica publicada para rompê-lo.

**Entradas**  
- `request_id: str`
- `validation_matrix: ValidationMatrix`
- `policy_profile: PolicyProfile`
- `queue_snapshot: QueueSnapshot`
- `exception_assessment: ExceptionAssessment`

**Saídas**  
- `RankedCandidates`

**Pré-condições**  
- só entram pares `eligible=true`;
- `policy_profile` versionado e carregado.

**Pós-condições**  
- o primeiro item é a recomendação determinística;
- empate usa regra estável documentada;
- `fifo_break` fica explícito por candidato.

**Erros possíveis**  
- `NO_ELIGIBLE_CANDIDATE`
- `EMPTY_VALIDATION_MATRIX`
- `INVALID_POLICY_PROFILE`

**Testes essenciais**  
- cenário-base;
- prioridade contratual;
- múltiplos elegíveis equivalentes;
- quebra justificada de FIFO.

**Observações de segurança**  
- a função não pode introduzir candidato fora da matriz;
- pesos e tie-breakers precisam ser publicados de forma genérica;
- score não deve ser usado como “verdade”, apenas como política de ordenação.

**Notas de implementação**  
Tie-break recomendado:

1. maior `score`;
2. menor `queue_position`;
3. menor `arrival_ts`;
4. menor `truck_id` lexicográfico;
5. menor `destination_id` lexicográfico.

#### 6.8.6 `generate_audit_payload`

**Objetivo**  
Montar o payload auditável imutável que torna a decisão reconstruível.

**Entradas**  
- `request_id: str`
- `interpreted_context: InterpretedContext`
- `validation_matrix: list`
- `ranked_decision: DecisionPreview`
- `operator_action: OperatorAction | None`

**Saídas**  
- `AuditRecord`

**Pré-condições**  
- decisão já calculada;
- validação e ranking disponíveis.

**Pós-condições**  
- payload apto a persistência e UI;
- toda quebra de FIFO lista rejeitados anteriores e regra disparada;
- override registra delta `before/after`.

**Erros possíveis**  
- `MISSING_DECISION`
- `MISSING_VALIDATION_TRACE`
- `SCHEMA_VIOLATION`

**Testes essenciais**  
- decisão nominal;
- quebra justificada de FIFO;
- override humano;
- caso bloqueado sem rota válida.

**Observações de segurança**  
- não incluir chain-of-thought;
- não incluir documento cru;
- IDs devem permanecer sintéticos.

**Notas de implementação**  
- o hash do audit payload deve ser calculado no momento da persistência;
- o preview da decisão e a ação humana devem ser armazenados separadamente para preservar rastreabilidade.

#### 6.8.7 `compose_driver_message`

**Objetivo**  
Gerar mensagem curta, operacional, segura e consistente com o estado formal da decisão.

**Entradas**  
- `request_id: str`
- `decision_status: DecisionStatus`
- `recommended_truck: str | None`
- `recommended_destination: str | None`
- `reason_summary: str`
- `max_chars: int`
- `locale: str`

**Saídas**  
- `DriverMessage`

**Pré-condições**  
- decisão final ou preview conhecida;
- `max_chars` e `locale` definidos.

**Pós-condições**  
- mensagem pronta para UI;
- sem vazamento de score, regra interna ou dado sensível.

**Erros possíveis**  
- `MISSING_DECISION_FIELDS`
- `MESSAGE_TOO_LONG`
- `UNSAFE_CONTENT_DETECTED`

**Testes essenciais**  
- mensagem de despacho;
- mensagem de bloqueio;
- mensagem de `REVIEW_REQUIRED`.

**Observações de segurança**  
- preferir templates controlados;
- nunca mencionar regra interna (“HC-01”, score, prioridade contratual sensível) ao motorista;
- nunca inventar motivo ausente do audit payload.

**Notas de implementação**  
Templates mínimos:

- despacho: `Chamar {truck_id} para {destination_id}. {short_reason}.`
- bloqueio: `Aguardar. Sem rota válida no momento. Procurar operador.`
- revisão: `Aguardar conferência operacional. Caso em revisão.`

### 6.9 Política de verdade do sistema

A política de verdade precisa ser explícita e implementada como código.

#### 6.9.1 Hierarquia de verdade

1. **Estado local do sistema** (`queue_snapshot`, `weather_state`, `resource_state`)
2. **Documento parseado** com confiança suficiente
3. **Nota textual do operador**

#### 6.9.2 Por tipo de campo

| Campo | Fonte primária | Fonte secundária | Fonte terciária | Ação em conflito |
|---|---|---|---|---|
| `queue_position`, `status` do caminhão | `queue_snapshot` | nenhuma | nota | prevalece estado local |
| `weather_state` | `weather_state.json` | nota | nenhuma | prevalece estado local; nota vira contexto |
| `resource_state` | `resource_state.json` | nota | nenhuma | prevalece estado local; conflito material pode gerar revisão |
| `document_status` | ticket parseado (`>= 0.75`) | nota | nenhuma | se confiança baixa, revisão |
| `load_condition` | ticket parseado (`>= 0.75`) | nota | nenhuma | se material e incerto, revisão |
| `vehicle_type` | `queue_snapshot` quando presente; senão ticket parseado | nota | nenhuma | mismatch material gera revisão |
| `contract_priority_flag` | ticket parseado | fila, se o pack publicar esse campo | nota | se incerto, não aplicar bônus |

#### 6.9.3 Regra operacional de contradição material

Há contradição material quando o conflito altera elegibilidade, destino ou justificativa de quebra de FIFO. Nestes casos:

- o sistema nunca escolhe “meio-termo” implícito;
- a fonte de maior hierarquia prevalece;
- a contradição é registrada em `material_conflicts`;
- se a contradição tornar a verdade insuficiente, o resultado é `REVIEW_REQUIRED`.

Exemplos:

- o ticket parece `clear`, mas `resource_state` marca o destino necessário como `blocked`: prevalece o estado local; o modelo não pode “reabilitar” o destino;
- a nota diz “choveu”, mas `weather_state` sintético do cenário está `none`: prevalece `weather_state`; a nota vira evidência contextual, não bloqueio;
- o ticket traz `vehicle_type` diferente do CSV e isso muda compatibilidade: `queue_snapshot` prevalece se o campo existir; a divergência é materializada e pode exigir revisão.

### 6.10 Ferramentas expostas ao modelo

#### `validate_hard_constraints`

```json
{
  "tool_name": "validate_hard_constraints",
  "arguments": {
    "candidate_trucks": ["TRK-001", "TRK-005"],
    "candidate_destinations": ["DST-OPEN-01", "DST-COV-01"]
  }
}
```

#### `rank_candidates`

```json
{
  "tool_name": "rank_candidates",
  "arguments": {
    "policy_profile_version": "v1-demo"
  }
}
```

#### `generate_audit_payload`

```json
{
  "tool_name": "generate_audit_payload",
  "arguments": {
    "operator_action": null
  }
}
```

#### `compose_driver_message` (opcional)

```json
{
  "tool_name": "compose_driver_message",
  "arguments": {
    "max_chars": 220,
    "locale": "pt-BR"
  }
}
```

---

## 7. Scenario Pack e benchmark

### 7.1 Objetivo do Scenario Pack

O pack sintético existe para tornar a submissão:

- reproduzível;
- benchmarkável;
- filmável;
- sanitizada.

O pack não tenta simular toda a logística. Ele modela o suficiente para forçar decisões não triviais e provar onde Gemma 4 agrega valor.

### 7.2 Estrutura do pack

```text
scenarios/
├─ manifest.json
├─ schemas/
│  ├─ queue_snapshot.schema.json
│  ├─ weather_state.schema.json
│  ├─ resource_state.schema.json
│  ├─ expected_decision.schema.json
│  └─ operator_action.schema.json
├─ common/
│  ├─ policy_profile.json
│  └─ destinations.json
└─ cases/
   ├─ S01_BASELINE/
   │  ├─ queue.csv
   │  ├─ ticket.pdf
   │  ├─ operator_note.txt
   │  ├─ weather_state.json
   │  ├─ resource_state.json
   │  └─ expected_decision.json
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

### 7.3 Schema mínimo de `expected_decision.json`

```json
{
  "type": "object",
  "properties": {
    "expected_status": {"type": "string"},
    "acceptable_trucks": {
      "type": "array",
      "items": {"type": "string"}
    },
    "acceptable_destinations": {
      "type": "array",
      "items": {"type": "string"}
    },
    "required_constraints": {
      "type": "array",
      "items": {"type": "string"}
    },
    "forbidden_pairs": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "truck_id": {"type": "string"},
          "destination_id": {"type": "string"}
        },
        "required": ["truck_id", "destination_id"]
      }
    },
    "fifo_break_expected": {"type": "boolean"},
    "required_rules": {
      "type": "array",
      "items": {"type": "string"}
    },
    "requires_review": {"type": "boolean"},
    "expected_operator_action": {"type": ["object", "null"]}
  },
  "required": [
    "expected_status",
    "acceptable_trucks",
    "acceptable_destinations",
    "required_constraints",
    "forbidden_pairs",
    "fifo_break_expected",
    "required_rules",
    "requires_review",
    "expected_operator_action"
  ],
  "additionalProperties": false
}
```

### 7.4 Dez cenários obrigatórios

#### S01 — cenário-base sem exceção

**Entrada esperada**  
Fila ordenada, ticket claro, `load_condition=dry`, `document_status=clear`, clima estável, todos os recursos disponíveis.

**Saída esperada**  
`PREVIEW_READY`, preservação de FIFO, primeiro caminhão elegível da fila enviado ao destino nominal.

**Racional de validação**  
Prova que o sistema não inventa complexidade quando a operação está normal. O ranking deve respeitar `PR-01_FIFO_DEFAULT`.

**O que prova na narrativa**  
Que o Yard Copilot não existe para “quebrar fila por padrão”. Ele preserva FIFO em regime nominal e só o rompe quando há razão técnica publicada.

#### S02 — chuva bloqueando moega aberta

**Entrada esperada**  
`weather_state.precipitation="rain"`, `DST-OPEN-01.status="blocked"` e destino coberto alternativo disponível; ticket do primeiro caminhão continua claro.

**Saída esperada**  
Recomendação para destino coberto ou, se não houver alternativa elegível, `BLOCKED`/`REVIEW_REQUIRED`. No exemplo canônico do blueprint, `TRK-005 -> DST-COV-01` é aceitável e produz quebra de FIFO justificada.

**Racional de validação**  
HC-01 precisa tornar qualquer par com destino aberto inelegível. O audit payload deve mostrar rejeição explícita dos pares anteriores com motivo `HC-01`.

**O que prova na narrativa**  
Que a quebra de FIFO decorre de restrição física verificável, não de preferência arbitrária do modelo.

#### S03 — carga úmida

**Entrada esperada**  
Ticket/documento indica `load_condition="wet"` com confiança suficiente; o destino nominal não aceita carga úmida; existe ao menos um destino compatível coberto ou o sistema deve aguardar.

**Saída esperada**  
Rerouting para destino compatível ou `BLOCKED`/`REVIEW_REQUIRED` se a compatibilidade não puder ser estabelecida.

**Racional de validação**  
HC-02 depende de parsing documental útil. O baseline heurístico sem Gemma deve ter mais dificuldade quando a indicação de umidade vier em layout menos trivial.

**O que prova na narrativa**  
Que Gemma agrega valor real no parsing do ticket e que essa diferença afeta a decisão, não só a descrição.

#### S04 — quebra de esteira

**Entrada esperada**  
Um recurso crítico associado a um destino aparece como `status="down"` ou `blocked` em `resource_state`; a nota do operador reforça a ocorrência.

**Saída esperada**  
Nenhum despacho pode usar o recurso afetado; o sistema recomenda rota alternativa elegível ou bloqueia.

**Racional de validação**  
HC-03 precisa invalidar todos os pares dependentes do recurso indisponível. A classificação de exceção deve apontar `CONVEYOR_DOWN` como primária.

**O que prova na narrativa**  
Que o estado local do sistema prevalece e que o modelo não reabilita recurso indisponível.

#### S05 — prioridade contratual

**Entrada esperada**  
Existe ao menos um caminhão posterior com `contract_priority_flag=true`, documento claro e par elegível. Há caminhões anteriores também elegíveis.

**Saída esperada**  
Quebra justificada de FIFO em favor do caminhão prioritário, desde que nenhuma hard constraint seja violada e que a política publicada realmente o coloque na frente.

**Racional de validação**  
A quebra de FIFO aqui não vem de bloqueio físico, mas de política local publicada. O benchmark precisa mostrar isso como decisão justificável, não aleatória.

**O que prova na narrativa**  
Que o sistema consegue explicar ruptura de FIFO por política, sem esconder a fila nem a regra.

#### S06 — bloqueio documental

**Entrada esperada**  
Ticket com `document_status="blocked"` ou `document_block_flags` preenchido, por exemplo com carimbo ou marca sintética de pendência.

**Saída esperada**  
O caminhão torna-se inelegível para despacho automático. O sistema escolhe o próximo par elegível ou responde `BLOCKED` se não houver alternativa.

**Racional de validação**  
HC-04 deve atuar no nível do caminhão, independentemente da disponibilidade de destino.

**O que prova na narrativa**  
Que Gemma 4 ajuda a transformar documento em evidência operacional, mas a decisão final continua sendo de código determinístico.

#### S07 — incompatibilidade de veículo

**Entrada esperada**  
O `vehicle_type` do caminhão não pertence à lista `allowed_vehicle_types` do destino nominal.

**Saída esperada**  
O par incompatível é removido da matriz; o sistema escolhe alternativa compatível ou bloqueia.

**Racional de validação**  
HC-05 precisa ser binária e transparente. O audit payload deve indicar exatamente qual pareamento foi rejeitado e por quê.

**O que prova na narrativa**  
Que a elegibilidade é física e codificada, não opinativa.

#### S08 — capacidade reduzida

**Entrada esperada**  
O destino nominal opera com `capacity_pct` reduzido. Se estiver abaixo do mínimo operacional, o par é inelegível. Se estiver acima do mínimo, mas abaixo do conforto, o destino continua possível com penalidade.

**Saída esperada**  
Reranking para outro destino com maior headroom, ou bloqueio quando a capacidade cair abaixo do mínimo.

**Racional de validação**  
HC-06 precisa diferenciar bloqueio duro de penalidade de política. Esse cenário valida a distinção entre hard constraint e regra de ranking.

**O que prova na narrativa**  
Que o sistema não confunde restrição absoluta com preferência operacional.

#### S09 — override humano

**Entrada esperada**  
O sistema produz um preview válido. Em seguida, o cenário injeta ação humana sintética `override` para um par alternativo ainda elegível, com motivo obrigatório.

**Saída esperada**  
`decision_status="OVERRIDDEN"`, registro do preview original, do novo par, do motivo e do ator sintético.

**Racional de validação**  
HC-07 precisa impedir override sem motivo e override para par inelegível. O benchmark deste cenário avalia governança, não “acerto do modelo”.

**O que prova na narrativa**  
Que o humano permanece no loop e que o sistema registra a mudança de forma auditável.

#### S10 — quebra justificada de FIFO

**Entrada esperada**  
Combinação de restrição operacional e/ou prioridade que torna a recomendação correta inequivocamente não FIFO. Os caminhões anteriores precisam aparecer como avaliados e rejeitados.

**Saída esperada**  
Par não FIFO recomendado com `fifo_break=true`, lista de rejeitados anteriores e regra(s) justificando a promoção do candidato final.

**Racional de validação**  
Esse é o núcleo narrativo da submissão. O benchmark deve exigir trilha suficiente para reconstrução completa.

**O que prova na narrativa**  
Que o sistema não apenas escolhe um caminhão; ele explica por que a fila foi quebrada sem virar caixa-preta.

### 7.5 Cenário canônico para o vídeo

O cenário recomendado para o vídeo principal é **S02_RAIN_OPEN**. Ele tem vantagens narrativas:

- a dor é imediatamente compreensível;
- a relação entre clima, recurso e fila é visual;
- Gemma entra no parsing do ticket e na explicação;
- o rules engine aparece de forma clara;
- a quebra de FIFO é tecnicamente defensável e fácil de filmar.

### 7.6 Benchmark: variantes comparadas

#### Variante 1 — `fifo`

Comportamento:

- escolhe o primeiro caminhão em espera por ordem de chegada;
- usa destino padrão simplificado;
- ignora parsing multimodal e quase toda a semântica contextual.

Função no benchmark: ilustrar por que o problema existe.

#### Variante 2 — `heuristic`

Comportamento:

- usa o mesmo downstream determinístico do sistema completo;
- usa contratos sintéticos textuais para medir a parte determinística sem acionar runtime Gemma;
- usa templates fixos de explicação.

Função no benchmark: isolar o valor do Gemma na interpretação e não na governança.

#### Variante 3 — `full`

Comportamento:

- usa Gemma 4 no parsing multimodal;
- usa Gemma 4 na classificação contextual quando necessário;
- usa tool calling controlado;
- mantém regras e ranking determinísticos;
- usa Gemma 4 para `reason_summary` final a partir do resultado formal.

Função no benchmark: demonstrar valor incremental real.

### 7.7 Métricas comparadas

| Métrica | Definição operacional |
|---|---|
| `constraint_violation_rate` | `decisões finais que violam HC / total de decisões finais` |
| `decision_match_at_1` | `top1` pertence ao conjunto `acceptable_trucks x acceptable_destinations` do cenário |
| `exception_f1` | Macro-BLOCKED da classificação de `primary_exception` |
| `ticket_field_accuracy` | média de acerto dos campos críticos do ticket (`document_status`, `load_condition`, `vehicle_type`, `contract_priority_flag`) |
| `fifo_break_justified_precision` | proporção de quebras de FIFO com trilha técnica suficiente (`rejeitados + regra + par final`) |
| `latency_p50` / `latency_p95` | percentis do tempo total do fluxo |
| `review_or_block_rate` | `casos com BLOCKED ou REVIEW_REQUIRED / total de casos` |
| `audit_completeness` | `payloads auditáveis completos / total de decisões` |

### 7.8 Como calcular cada métrica

```text
constraint_violation_rate
= (# decisões finais cujo par aprovado viola HC-01..HC-07) / (# decisões finais)

decision_match_at_1
= (# cenários em que a recomendação top-1 está no conjunto aceitável) / (# cenários avaliados)

ticket_field_accuracy
= (# campos críticos corretos) / (# campos críticos avaliados)

fifo_break_justified_precision
= (# quebras de FIFO com trilha auditável completa) / (# quebras de FIFO)
```

### 7.9 Protocolo experimental reproduzível

1. validar `manifest.json` e schemas do pack;
2. rodar `fifo` em todos os 10 cenários;
3. rodar `heuristic` em todos os 10 cenários;
4. rodar `full` em todos os 10 cenários;
5. exportar `report.json`, `summary.csv` e gráficos;
6. persistir logs e audit payloads;
7. opcionalmente rodar ablações `--no_multimodal` e `--no_tools`.

### 7.10 O que constitui prova de valor real do Gemma 4

Gemma 4 adiciona valor real se, mantendo a mesma segurança do baseline heurístico, ele melhorar:

- `ticket_field_accuracy`;
- `exception_f1`;
- `decision_match_at_1`;

especialmente em S03, S06 e S10, onde a interpretação documental e contextual é a fonte do ganho.

O valor **não** está provado se:

- a explicação ficar melhor, mas a decisão continuar errada;
- o modelo só reproduzir regras já explícitas no estado local;
- a melhora estiver restrita a narrativa textual sem impacto nas métricas de decisão.

### 7.11 O que precisa aparecer nos relatórios

Arquivos recomendados em `bench/reports/<run_id>/`:

```text
summary.csv
per_scenario.json
metrics.json
latency_distribution.png
metric_comparison_bar.png
exception_confusion_matrix.png
audit_samples/
  S02_full_audit.json
  S10_full_audit.json
```

### 7.12 Ações mínimas para o writeup

O writeup precisa conter, no mínimo:

- tabela comparando as três variantes;
- gráfico por métrica;
- matriz por cenário;
- screenshot do audit payload;
- screenshot da UI;
- nota explícita de limites e fail-closed.

---

## 8. Modos de falha, riscos e defesas

### 8.1 Princípio geral

O sistema deve falhar de forma **controlada, auditável e conservadora**. O erro aceitável é perder automação; o erro inaceitável é emitir despacho aparentemente seguro sem base suficiente.

### 8.2 Edge cases e resposta esperada

| Caso | Detecção | Resposta do sistema | Estado final esperado |
|---|---|---|---|
| Tool call inválida | schema/name/order inválidos | 1 reparo; se falhar, encerrar sem decisão automática | `BLOCKED` ou `REVIEW_REQUIRED` |
| Timeout do Gemma | timeout > limite | falha fechada explicita | BLOCKED ou REVIEW_REQUIRED |
| Documento ilegível | `UNREADABLE_DOCUMENT` | revisão quando campo material depender do documento | `REVIEW_REQUIRED` |
| Baixa confiança no parsing | `parse_confidence < threshold` | aplicar política A-04 | `REVIEW_REQUIRED` se material |
| Conflito entre documento e estado local | `material_conflicts != []` | prevalece fonte superior; se ainda insuficiente, revisão | `BLOCKED` ou `REVIEW_REQUIRED` |
| Fila vazia | `EMPTY_QUEUE` | sem despacho automático | `BLOCKED` |
| Nenhum destino elegível | matriz sem pares elegíveis | bloquear ou revisar conforme suficiência da evidência | `BLOCKED` ou `REVIEW_REQUIRED` |
| Múltiplos candidatos equivalentes | empate de score | tie-break estável | `PREVIEW_READY` |
| Necessidade de revisão humana | reasons explícitas | exibir revisão, não sugestão operacional conclusiva | `REVIEW_REQUIRED` |
| Falha parcial do modelo | parse ou classify falha | encerrar sem substituição automática | `REVIEW_REQUIRED` |
| Override para par inelegível | validação falha | rejeitar override | `REVIEW_REQUIRED` ou manutenção do preview anterior |

### 8.3 Fail-closed detalhado

Objetivo: preservar segurança quando o problema não pode ser automatizado com verdade suficiente.

Invariantes:

- não há modelo substituto;
- não há parser alternativo automático;
- não há retry silencioso que altere lógica decisória;
- não há despacho com campo material indeterminado;
- `BLOCKED` e `REVIEW_REQUIRED` precisam explicar a causa.

#### REVIEW_REQUIRED — revisão obrigatória

Objetivo: impedir que a automação extrapole a verdade disponível.

Condições típicas:

- documento ilegível em campo material;
- conflito sem resolução;
- override ilegal;
- falha de auditoria;
- falta de estado necessário para validação.

### 8.4 Riscos principais e contramedidas

| Risco | Sinal precoce | Contramedida |
|---|---|---|
| Projeto parecer dashboard genérico | juiz não vê papel do Gemma | destacar parsing multimodal, tool calling e benchmark por ablação |
| Escopo expandir | backlog fora do recorte | congelar OOS e ADRs na semana 1 |
| Parsing multimodal fraco | campos críticos saem `unknown` | curar tickets sintéticos e manter fail-closed |
| Latência excessiva | `p95` acima da meta | E4B/E2B, prompts curtos, warmup, thinking off |
| Tool selection errada | muitos `SCHEMA_ERROR` | whitelist curta e state machine explícita |
| Benchmark pouco convincente | variantes próximas demais | fortalecer cenários em que documento/texto afetam decisão |
| Vazamento de IP | artefatos “realistas demais” | synthetic-first, review manual, secret scan |
| Writeup prometer além do código | claims sem prova | matriz de evidências obrigatória |

### 8.5 Defesas de implementação

- schema-first em todas as fronteiras;
- state machine explícita;
- no network calls no caminho feliz;
- fail-closed em decisão automática;
- SQLite + JSONL para inspeção manual;
- separação rígida entre preview e ação humana final;
- testes de falha induzida antes do vídeo.

---

## 9. Segurança, LGPD e repositório público

### 9.1 Estrutura recomendada do repositório público

```text
repo/
├─ README.md
├─ LICENSE
├─ NOTICE
├─ pyproject.toml
├─ requirements.lock
├─ app/
├─ scenarios/
├─ bench/
├─ tests/
├─ docs/
│  ├─ technical_blueprint.md
│  ├─ architecture.md
│  ├─ adr/
│  └─ writeup_assets/
├─ scripts/
│  ├─ bootstrap.sh
│  ├─ prewarm_models.sh
│  ├─ run_demo.sh
│  ├─ run_benchmark.sh
│  ├─ validate_scenarios.sh
│  └─ prepublish_check.sh
└─ .github/
   └─ workflows/
      ├─ test.yml
      └─ lint.yml
```

### 9.2 Scripts obrigatórios

#### `scripts/bootstrap.sh`

Responsabilidades:

- criar ambiente virtual;
- instalar dependências;
- validar schemas;
- orientar obtenção/caching dos pesos do modelo;
- preparar diretórios locais (`cache/`, `bench/reports/`, `var/log/`).

#### `scripts/prewarm_models.sh`

Responsabilidades:

- carregar runtime local;
- executar chamada curta de warmup;
- medir latência inicial;
- registrar backend e modelo usados.

#### `scripts/run_demo.sh`

Exemplo de uso:

```bash
./scripts/run_demo.sh --scenario S02_RAIN_OPEN --variant full
```

Responsabilidades:

- carregar um cenário específico;
- subir a UI ou executar fluxo CLI equivalente;
- abrir a tela pronta para gravação.

#### `scripts/run_benchmark.sh`

Exemplo de uso:

```bash
./scripts/run_benchmark.sh --manifest scenarios/manifest.json
```

Responsabilidades:

- rodar `fifo`, `heuristic` e `full`;
- exportar relatório completo.

#### `scripts/prepublish_check.sh`

Responsabilidades:

- secret scan;
- validação de dados sintéticos;
- verificação de ausência de artefatos reais;
- validação do README e dos comandos.

### 9.3 O que pode ser publicado

| Categoria | Pode publicar? |
|---|---|
| Código-fonte do monólito modular | Sim |
| Schemas JSON e prompts sanitizados | Sim |
| Scenario Pack sintético | Sim |
| Tickets sintéticos e screenshots sintéticos | Sim |
| Benchmarks e relatórios agregados | Sim |
| ADRs, diagramas e blueprint | Sim |

### 9.4 O que não pode ser publicado

| Categoria | Pode publicar? |
|---|---|
| nomes reais de clientes | Não |
| layouts operacionais identificáveis | Não |
| placas, IDs reais, CNPJ, nomes de pessoas | Não |
| logs reais de operação | Não |
| screenshots com dados reais | Não |
| segredos, tokens, endpoints produtivos | Não |
| roadmap amplo do PequiFlux completo | Não |

### 9.5 Política de sanitização

Princípio: **synthetic-first**. O repositório público da hackathon não deve depender de pseudonimização de dado real. Ele deve ser construído para conter somente dado sintético.

Regras práticas:

1. usar IDs sintéticos estáveis;
2. não reutilizar nomes ou códigos internos reais;
3. remover qualquer elemento visual que remeta a cliente, local ou operação específica;
4. deslocar horários e volumes para valores sintéticos;
5. evitar prints de logs privados;
6. revisar manualmente prompts e comentários.

### 9.6 Política de logs

Em modo normal:

- persistir hashes de input, latências, status, fail-closed, códigos de erro e outputs estruturados finais;
- não persistir prompt cru;
- não persistir chain-of-thought;
- não persistir documento bruto.

Em modo debug local privado:

- permitido apenas fora do repositório público;
- nunca commitar.

### 9.7 Tratamento de identificadores

Todos os identificadores visíveis devem seguir esquema sintético e estável.

Exemplos:

- `TRK-001`
- `DST-OPEN-01`
- `DST-COV-01`
- `TCK-003`
- `DEC-2026-010`

Não usar:

- hashes reversíveis de IDs reais;
- placas;
- nomes de motoristas;
- nomes de empresas;
- qualquer label que denuncie origem produtiva.

### 9.8 LGPD por desenho

A forma mais robusta de aderência para esta submissão é simples: **não colocar dado pessoal no artefato público**.

Implicações:

- nenhuma identidade pessoal real precisa aparecer na UI;
- nenhuma mensagem ao motorista precisa conter nome;
- nenhuma nota do operador deve vir de produção;
- o ator humano da demo é sintético.

### 9.9 Limite de exposição do roadmap

O repositório deve falar somente do recorte **Yard Copilot**. Não deve antecipar:

- módulos futuros do PequiFlux;
- integrações planejadas;
- clientes alvo;
- métricas de adoção;
- estratégia comercial.

### 9.10 Checklist pré-publicação

| Item | Gate |
|---|---|
| `gitleaks` / secret scan | `0 findings` |
| dados sintéticos confirmados | 100% |
| README reproduzível | comandos testados |
| screenshots sanitizadas | 100% |
| prompts sem segredo ou IP sensível | validado |
| logs commitados sintéticos | 100% |
| LICENSE e créditos | presentes |
| claims compatíveis com benchmark | validados |

---

## 10. Evidências para submissão

### 10.1 Storyboard do vídeo de 3 minutos

| Tempo | Bloco | O que mostrar | O que precisa ficar claro |
|---|---|---|---|
| 0:00–0:20 | Problema | FIFO falha quando entra chuva/documento/recurso indisponível | dor operacional |
| 0:20–0:40 | Tese | diagrama simples: Gemma interpreta; regras decidem; humano governa | arquitetura em uma frase |
| 0:40–1:20 | Demo principal | carregar CSV, ticket, nota, clima e recurso | input multimodal realista |
| 1:20–1:45 | Centralidade do Gemma | painel curto com parsing e classificação | modelo é central, não cosmético |
| 1:45–2:05 | Determinismo | matriz de hard constraints e ranking | decisão não depende da vontade do modelo |
| 2:05–2:25 | Quebra de FIFO | diff da fila antes/depois + rejeitados | tese central da submissão |
| 2:25–2:40 | Benchmark | tabela simples `fifo vs heuristic vs full` | valor incremental real |
| 2:40–2:55 | Falha e fail-closed | induzir erro/timeout e mostrar BLOCKED/REVIEW_REQUIRED | robustez |
| 2:55–3:00 | Fechamento | repo, relatório, takeaway | reprodutibilidade |

### 10.2 Estrutura recomendada do writeup da Kaggle

1. problema operacional e por que FIFO falha em exceção;
2. recorte congelado e por que ele foi escolhido;
3. arquitetura: Gemma interpreta, regras decidem, humano governa;
4. uso específico do Gemma 4;
5. Scenario Pack, benchmark e variantes;
6. falhas, fail-closed e limites;
7. repositório público e reprodutibilidade;
8. próximos passos estritamente dentro do recorte.

### 10.3 Tabelas, gráficos e screenshots essenciais

| Artefato | Obrigatório? | Papel |
|---|---|---|
| Diagrama de containers | Sim | tornar arquitetura julgável |
| Fluxo e2e | Sim | mostrar cadeia interpretação -> validação -> decisão |
| Screenshot da UI | Sim | provar produto funcional |
| Tabela de benchmark | Sim | provar valor comparativo |
| Screenshot do audit payload | Sim | provar auditabilidade |
| Gráfico de latência | Recomendado | responder crítica de viabilidade local |
| Matriz por cenário | Recomendado | mostrar onde Gemma agrega valor |

### 10.4 Matriz de evidências

| Afirmação | Prova no código | Prova no benchmark | Prova no vídeo | Prova no writeup |
|---|---|---|---|---|
| Gemma 4 é central | `app/gemma/`, prompts, parser multimodal | ganho em `ticket_field_accuracy` e `exception_f1` | painel “Gemma interpreted” | seção “How Gemma 4 was used” |
| Hard constraints são determinísticas | `app/domain/constraints.py` | `constraint_violation_rate=0` no `full` | matriz de constraints | seção de arquitetura |
| Quebra de FIFO é justificável | `app/audit/` + policy profile | `fifo_break_justified_precision=1.0` | diff da fila | seção de resultados |
| Sistema é local-first | scripts + runtime local | benchmark offline após cache | demo sem API externa | seção de reprodutibilidade |
| Fail-closed existe | `app/gemma/fallback.py` | falha induzida coberta | cena de erro e bloqueio | seção de limites |
| Repo é sanitizado | checklist + synthetic pack | n/a | captura do repo | seção de segurança |

### 10.5 Recomendações explícitas para a gravação

- usar **um cenário principal**, não uma colagem apressada de dez;
- mostrar o ticket cru por alguns segundos antes da interpretação;
- mostrar que o modelo não manda no sistema: a tela de constraints deve vir depois do parsing;
- o diff da fila precisa ser legível em 1920x1080;
- a cena de fail-closed deve ser curta e controlada;
- a tabela de benchmark deve caber em um único frame.

---

## 11. ADRs iniciais

### ADR-001 — Monólito modular vs microsserviços

**Status:** Accepted  
**Contexto:** o projeto precisa ser pequeno, reproduzível e rápido de integrar.  
**Decisão:** usar monólito modular em Python.  
**Alternativa rejeitada:** microsserviços com API interna.  
**Consequências positivas:** menos overhead, debug simples, menor custo de integração.  
**Consequências negativas:** menor isolamento operacional.

### ADR-002 — Gemma como camada de interpretação e explicação vs motor decisório total

**Status:** Accepted  
**Contexto:** hard constraints não podem depender de modelo.  
**Decisão:** Gemma interpreta, pede tools permitidas e explica; regras decidem.  
**Alternativa rejeitada:** LLM como motor decisório completo.  
**Consequências positivas:** segurança, auditabilidade, testabilidade.  
**Consequências negativas:** menos autonomia aparente do agente.

### ADR-003 — Rules engine determinístico

**Status:** Accepted  
**Contexto:** elegibilidade, compatibilidade e bloqueios são críticos.  
**Decisão:** HC-01..HC-07 ficam em código versionado.  
**Alternativa rejeitada:** política embutida em prompt.  
**Consequências positivas:** rastreabilidade e benchmark confiável.  
**Consequências negativas:** mais modelagem manual.

### ADR-004 — Entradas múltiplas (CSV + PDF/imagem + nota + estados)

**Status:** Accepted  
**Contexto:** o valor do problema está na heterogeneidade do sinal.  
**Decisão:** suportar múltiplas entradas no fluxo mínimo.  
**Alternativa rejeitada:** texto-only.  
**Consequências positivas:** multimodalidade útil e narrativa forte.  
**Consequências negativas:** mais adaptadores e mais testes.

### ADR-005 — Benchmark contra FIFO

**Status:** Accepted  
**Contexto:** a dor do produto nasce dos limites do FIFO puro.  
**Decisão:** incluir FIFO como baseline obrigatório.  
**Alternativa rejeitada:** benchmark sem baseline.  
**Consequências positivas:** história clara para o juiz.  
**Consequências negativas:** baseline simplista se usado sozinho.

### ADR-006 — Repositório público sanitizado

**Status:** Accepted  
**Contexto:** a competição exige publicidade, mas o produto não pode vazar IP.  
**Decisão:** publicar somente código, prompts, rules e pack sintéticos.  
**Alternativa rejeitada:** repo privado ou semi-realista.  
**Consequências positivas:** segurança e aderência à competição.  
**Consequências negativas:** alguns exemplos ficam menos realistas.

### ADR-007 — UI única rápida de filmar

**Status:** Accepted  
**Contexto:** a submissão precisa de uma superfície única, rápida de construir e estável para vídeo.  
**Decisão:** usar Streamlit como UI padrão (**ASSUNÇÃO A-02**).  
**Alternativa rejeitada:** FastAPI + React ou notebook puro.  
**Consequências positivas:** agilidade e simplicidade.  
**Consequências negativas:** refinamento visual menor.

### ADR-008 — Estratégia local-first

**Status:** Accepted  
**Contexto:** a tese de resiliência e reprodutibilidade depende de execução local.  
**Decisão:** rodar localmente após cache do modelo.  
**Alternativa rejeitada:** cloud-first com API externa.  
**Consequências positivas:** coerência com o recorte.  
**Consequências negativas:** maior sensibilidade a hardware local.

---

## 12. Plano de entrega

### 12.1 Plano em quatro semanas

| Semana | Backlog principal | Definition of Done |
|---|---|---|
| Semana 1 | congelar escopo, schemas, ADRs, policy profile, Scenario Pack v0, wireframe da UI | schemas versionados, 10 cenários definidos, política de verdade fechada, wireframe aprovado |
| Semana 2 | implementar fluxo e2e mínimo, parser multimodal, classificação, rules engine, tool gateway | um cenário roda ponta a ponta por CLI; HC-01..HC-07 implementadas; adapter Gemma retorna schema válido |
| Semana 3 | fechar UI, auditoria, logs, benchmark, override, fail-closed | os 10 cenários rodam em lote; UI exibe preview e trilha; falhas induzidas cobertas |
| Semana 4 | hardening, rerun final, gravação, writeup, sanitização, submissão | benchmark final exportado; vídeo pronto; repo sanitizado; checklist pré-publicação concluído |

### 12.2 Ordem de implementação recomendada

1. contratos de dados;
2. normalização da fila;
3. hard constraints;
4. ranking e decision builder;
5. persistência e audit payload;
6. parser documental com Gemma;
7. classificação híbrida;
8. tool gateway;
9. UI;
10. benchmark;
11. fail-closed;
12. vídeo e writeup.

### 12.3 Caminho crítico

O caminho crítico não é a UI. O caminho crítico é:

`Scenario Pack confiável -> parser/documento útil -> hard constraints sólidas -> benchmark claro -> vídeo simples`

Se esse eixo estiver sólido, a UI pode ser minimalista sem destruir a submissão.

---

## 13. Payload final esperado pelo front-end

### 13.1 Princípio

O front-end deve consumir **um payload único**, suficiente para:

- renderizar a recomendação;
- mostrar os motivos;
- mostrar a quebra ou preservação de FIFO;
- expor a ação humana;
- tornar a centralidade do Gemma visível;
- exibir a trilha de auditoria;
- não depender de lógica adicional para “deduzir” segurança.

### 13.2 Schema mínimo

```json
{
  "$id": "schemas/FrontEndPayload.schema.json",
  "type": "object",
  "properties": {
    "request_id": {"type": "string"},
    "scenario_id": {"type": "string"},
    "variant": {"type": "string"},
    "decision_status": {"type": "string"},
    "recommended_truck": {
      "type": ["object", "null"],
      "properties": {
        "truck_id": {"type": "string"},
        "queue_position_before": {"type": "integer"},
        "queue_position_after": {"type": "integer"}
      }
    },
    "recommended_destination": {
      "type": ["object", "null"],
      "properties": {
        "destination_id": {"type": "string"},
        "destination_type": {"type": "string"}
      }
    },
    "considered_constraints": {
      "type": "array",
      "items": {"type": "object"}
    },
    "reason_summary": {"type": "string"},
    "reason_details": {
      "type": "array",
      "items": {"type": "string"}
    },
    "driver_message": {
      "type": "object",
      "properties": {
        "message": {"type": "string"},
        "template_id": {"type": "string"}
      }
    },
    "operator_actions": {
      "type": "array",
      "items": {"type": "string"}
    },
    "queue_diff": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "truck_id": {"type": "string"},
          "position_before": {"type": "integer"},
          "position_after": {"type": ["integer", "null"]},
          "decision": {"type": "string"},
          "reason": {"type": "string"}
        }
      }
    },
    "gemma_visible_summary": {
      "type": "object",
      "properties": {
        "vehicle_type": {"type": "string"},
        "document_status": {"type": "string"},
        "load_condition": {"type": "string"},
        "primary_exception": {"type": "string"},
        "parse_confidence": {"type": "number"},
        "tools_called": {
          "type": "array",
          "items": {"type": "string"}
        }
      }
    },
    "audit_record": {"type": "object"},
    "latency_ms": {"type": "object"},
    "benchmark_tags": {
      "type": "array",
      "items": {"type": "string"}
    },
    "confidence_notes": {
      "type": "array",
      "items": {"type": "string"}
    }
  },
  "required": [
    "request_id",
    "scenario_id",
    "variant",
    "decision_status",
    "recommended_truck",
    "recommended_destination",
    "considered_constraints",
    "reason_summary",
    "reason_details",
    "driver_message",
    "operator_actions",
    "queue_diff",
    "gemma_visible_summary",
    "audit_record",
    "latency_ms",
    "benchmark_tags",
    "confidence_notes"
  ],
  "additionalProperties": false
}
```

### 13.3 Exemplo completo

```json
{
  "request_id": "REQ-2026-0007",
  "scenario_id": "S02_RAIN_OPEN",
  "variant": "full",
  "decision_status": "PREVIEW_READY",
  "recommended_truck": {
    "truck_id": "TRK-005",
    "queue_position_before": 4,
    "queue_position_after": 1
  },
  "recommended_destination": {
    "destination_id": "DST-COV-01",
    "destination_type": "covered_hopper"
  },
  "considered_constraints": [
    {
      "constraint_id": "HC-01",
      "status": "failed_for_TRK-001_on_DST-OPEN-01",
      "scope": "pair",
      "evidence_ref": "weather_state"
    },
    {
      "constraint_id": "HC-05",
      "status": "failed_for_TRK-002_on_DST-COV-01",
      "scope": "pair",
      "evidence_ref": "resource_state.allowed_vehicle_types"
    }
  ],
  "reason_summary": "A chuva bloqueou a moega aberta. O primeiro par elegível sob as regras atuais é TRK-005 para DST-COV-01.",
  "reason_details": [
    "TRK-001 foi rejeitado para DST-OPEN-01 por HC-01.",
    "TRK-002 não é compatível com DST-COV-01 por HC-05.",
    "TRK-005 mantém elegibilidade e cabe no destino coberto disponível."
  ],
  "driver_message": {
    "message": "Chamar TRK-005 para DST-COV-01. Destino aberto indisponível por chuva.",
    "template_id": "MSG-DISPATCH-001"
  },
  "operator_actions": ["approve", "block", "override"],
  "queue_diff": [
    {
      "truck_id": "TRK-001",
      "position_before": 1,
      "position_after": null,
      "decision": "skipped",
      "reason": "HC-01"
    },
    {
      "truck_id": "TRK-002",
      "position_before": 2,
      "position_after": null,
      "decision": "skipped",
      "reason": "HC-05"
    },
    {
      "truck_id": "TRK-005",
      "position_before": 4,
      "position_after": 1,
      "decision": "recommended",
      "reason": "first_eligible_pair"
    }
  ],
  "gemma_visible_summary": {
    "vehicle_type": "bitrem",
    "document_status": "clear",
    "load_condition": "dry",
    "primary_exception": "RAIN_OPEN_HOPPER_BLOCK",
    "parse_confidence": 0.88,
    "tools_called": [
      "validate_hard_constraints",
      "rank_candidates",
      "generate_audit_payload"
    ]
  },
  "audit_record": {
    "decision_id": "DEC-2026-010",
    "fired_rules": [
      "HC-01",
      "PR-01_FIFO_DEFAULT",
      "PR-03_REDUCED_CAPACITY_PENALTY"
    ],
    "rejected_candidates": [
      {"truck_id": "TRK-001", "destination_id": "DST-OPEN-01", "reason": "HC-01"},
      {"truck_id": "TRK-002", "destination_id": "DST-COV-01", "reason": "HC-05"}
    ],
    "provenance": [
      {"field": "primary_exception", "source": "operator_note"},
      {"field": "vehicle_type", "source": "ticket_document"},
      {"field": "resource_status", "source": "resource_state"}
    ]
  },
  "latency_ms": {
    "model": 2850,
    "rules": 41,
    "ranking": 5,
    "total": 3280
  },
  "benchmark_tags": [
    "S02_RAIN_OPEN",
    "variant:full",
    "fifo_break:true"
  ],
  "confidence_notes": [
    "ticket_parse_confidence=0.88",
    "exception_classification=high_confidence"
  ]
}
```

### 13.4 Semântica operacional do payload final

| Campo | Semântica |
|---|---|
| `decision_status` | preview, bloqueio, revisão, aprovado ou override final |
| `recommended_truck` | caminhão sugerido e sua relação com FIFO |
| `recommended_destination` | destino sugerido e seu tipo |
| `considered_constraints` | regras críticas efetivamente checadas |
| `reason_summary` | resumo curto para operador e vídeo |
| `reason_details` | detalhamento curto das rejeições e promoção do recomendado |
| `driver_message` | mensagem operacional segura |
| `operator_actions` | ações humanas habilitadas naquele estado |
| `queue_diff` | antes/depois da fila, essencial para a narrativa |
| `gemma_visible_summary` | torna a centralidade do modelo visível sem virar chat |
| `audit_record` | trilha formal reconstruível |
| `latency_ms` | prova de viabilidade local |
| `benchmark_tags` | agregação e filtragem experimental |
| `confidence_notes` | observabilidade resumida, sem chain-of-thought |

### 13.5 UI única da demo

#### Acima da dobra

A tela principal deve caber em `1920x1080` e mostrar, sem scroll:

1. **cabeçalho do cenário**: `scenario_id`, variante, politica fail-closed;
2. **preview do ticket**: thumbnail do PDF/imagem ou indicador de documento;
3. **card de recomendação**:
   - caminhão;
   - destino;
   - status da decisão;
   - `reason_summary`;
4. **chips de restrição** com HC disparadas;
5. **barra de ação humana** com `approve`, `block`, `override`;
6. **painel curto “Gemma interpreted”** com campos estruturados e tools chamadas.

#### Abaixo da dobra

1. **diff da fila**: tabela `antes/depois`, com rejeitados e motivo;
2. **audit trail**: painel colapsável com JSON formatado;
3. **benchmark snapshot**: tabela pequena das três variantes para o cenário atual;
4. **diagnóstico**: latência, fail-closed, modelo usado.

#### Como tornar a centralidade do Gemma visível sem poluir

- não usar janela de chat;
- não exibir prompt;
- usar um bloco curto com cinco campos estruturados;
- exibir badges das tools chamadas (`validated`, `ranked`, `audited`);
- mostrar o ticket cru ao lado do resumo estruturado.

#### Approve / Block / Override

- `approve`: um clique, sem motivo obrigatório;
- `block`: exige motivo em campo curto;
- `override`: abre seletor de caminhão/destino entre **pares elegíveis**, mais campo de motivo;
- se o usuário tentar override para par inelegível, a UI deve mostrar erro explícito e registrar tentativa.

---

## 14. Crítica do próprio documento

### 14.1 Pontos ainda frágeis

O blueprint é forte em governança, benchmark e reprodutibilidade, mas continua dependente de três pontos sensíveis:

1. hardware real disponível para a inferência local;
2. qualidade do empacotamento multimodal do ticket;
3. calibração do `policy_profile.json`.

Os pesos de ranking publicados aqui são **ASSUNÇÃO A-05**. Eles servem para tornar o sistema implementável e auditável, não para reivindicar política operacional validada.

### 14.2 Dependências perigosas

As dependências mais perigosas são:

- serialização correta do output estruturado do Gemma;
- estado do runtime local do modelo;
- disciplina em torno do tool gateway;
- qualidade narrativa do benchmark.

Uma arquitetura correta no papel pode falhar na demo por detalhe de schema, timeout ou UI confusa.

### 14.3 Partes que parecem boas no papel, mas podem falhar no vídeo

A cadeia mais vulnerável é:

`documento -> Gemma -> tool call -> validação -> ranking -> UI`

Se qualquer elo ficar opaco, o juiz não verá o valor. O segundo risco é o benchmark: uma tabela correta ainda pode parecer fraca se o vídeo não mostrar visualmente por que o FIFO foi quebrado.

### 14.4 O que simplificar primeiro se o prazo apertar

Em ordem de corte:

1. sofisticação do score;
2. quantidade de painéis secundários da UI;
3. número de ablações opcionais;
4. refinamento da mensagem ao motorista.

O que **não** deve ser simplificado:

- os 10 cenários obrigatórios;
- hard constraints;
- trilha auditável;
- fail-closed;
- comparação contra FIFO e baseline heurístico.

### 14.5 Perguntas ainda abertas

| ID | Pergunta |
|---|---|
| Q-01 | Qual hardware local real estará disponível para benchmark e gravação? |
| Q-02 | O backend local concreto do Gemma será qual, dentro do adaptador? |
| Q-03 | O benchmark principal cobrará `match` exato ou conjunto aceitável por cenário? |
| Q-04 | O cenário principal do vídeo permanecerá S02 ou será S10? |
| Q-05 | Quais módulos do PequiFlux maior precisam ficar totalmente fora do repo público? |

### 14.6 Limite epistemológico do documento

Este blueprint é um projeto técnico executável para uma submissão de hackathon. Ele não substitui:

- validação em campo;
- política operacional homologada;
- estudo de segurança formal em ambiente real;
- engenharia de produção para sistema crítico.

Ele é forte quando se mantém dentro desse limite.

---

## Apêndice A — `policy_profile.json` de referência

Este arquivo deve ser publicado como genérico e explicitamente sintético.

```json
{
  "version": "v1-demo",
  "min_operational_capacity_pct": 20,
  "comfort_capacity_pct": 50,
  "weights": {
    "fifo_position": 40,
    "contract_priority": 30,
    "resource_fit": 15,
    "capacity_headroom": 10,
    "wait_sla_pressure": 5
  },
  "tie_breakers": [
    "higher_score",
    "lower_queue_position",
    "earlier_arrival_ts",
    "lexicographic_truck_id",
    "lexicographic_destination_id"
  ]
}
```

## Apêndice B — Comandos de referência

```bash
# bootstrap local
./scripts/bootstrap.sh

# warmup do modelo
./scripts/prewarm_models.sh

# demo interativa de um cenário
./scripts/run_demo.sh --scenario S02_RAIN_OPEN --variant full

# benchmark completo
./scripts/run_benchmark.sh --manifest scenarios/manifest.json

# validação pré-publicação
./scripts/prepublish_check.sh
```

## Apêndice C — Critério editorial para claims no writeup

Toda afirmação no writeup deve passar por três filtros:

1. **é observável?**
2. **tem artefato correspondente no código, no benchmark ou no vídeo?**
3. **não extrapola o recorte congelado?**

Se a resposta for “não” para qualquer um dos três, a afirmação deve ser removida.
