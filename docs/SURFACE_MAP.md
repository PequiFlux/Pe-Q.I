# SURFACE MAP

Mapa da superfície pública/exportada do PequiFlux Yard Copilot.

## Superfície atual

| Símbolo | Tipo | Arquivo | Responsabilidade | Entradas | Saídas | Observações |
|---|---|---|---|---|---|---|
| `app.cli.run_scenario` | CLI module | `app/cli/run_scenario.py` | Executa um cenário sintético | Caminho/ID de cenário | Decisão e payload de execução | Entrada padrão para demo local |
| `app.cli.run_benchmark` | CLI module | `app/cli/run_benchmark.py` | Executa benchmark de cenários | Manifest e fixtures | Métricas/relatório | Usado por Docker/Compose |
| `app.cli.prewarm_gemma` | CLI module | `app/cli/prewarm_gemma.py` | Preaquece runtime Gemma/Ollama | Configuração de runtime | Status de prewarm | Não deve substituir runtime ausente |
| `app.cli.blueprint_audit` | CLI module | `app/cli/blueprint_audit.py` | Audita alinhamento com blueprint | Blueprint/docs | Relatório de auditoria | Apoia checks públicos |
| `app.ui.streamlit_app` | UI module | `app/ui/streamlit_app.py` | Interface Streamlit | Inputs de cenário | Payloads visuais com pacote operacional, ticket, recomendação e auditoria | Deve chamar orquestração, não duplicar domínio |
| `app.orchestration.orchestrator` | module | `app/orchestration/orchestrator.py` | Coordena fluxo de decisão e finalização auditável | Contexto interpretado, estados, política | Decisão final/review/error com payload auditável | Núcleo de execução; estados terminais usam finalização comum |
| `app.orchestration.truth_resolver` | module | `app/orchestration/truth_resolver.py` | Resolve divergências entre fontes | Ticket, nota, estados | Contexto reconciliado | Falhas devem ser explícitas |
| `app.orchestration.state_machine` | module | `app/orchestration/state_machine.py` | Controla estados terminais e transições | Estado atual, evento | Novo estado/erro | Coberto por testes unitários |
| `app.domain.constraints` | module | `app/domain/constraints.py` | Aplica hard constraints | Decisão candidata, contexto | Bloqueios/revisões | Não duplicar em serviços/UI |
| `app.domain.ranking` | module | `app/domain/ranking.py` | Ordena e pontua fila | Fila, política, contexto | Ranking | Reutilizar antes de criar scoring paralelo |
| `app.domain.policy` | module | `app/domain/policy.py` | Carrega/aplica perfil de política | Policy profile | Política validada | Alinha scenarios/common |
| `app.services.decision_builder` | module | `app/services/decision_builder.py` | Monta decisão e payload de saída | Resultado de domínio/orquestração | Front-end/audit payload | Reutilizado por todos os estados terminais |
| `app.gemma.adapter` | module | `app/gemma/adapter.py` | Adapta runtime LLM para contrato do sistema | Prompt/contexto | Contexto interpretado ou erro | Sem fallback silencioso |
| `app.gemma.runtime_factory` | module | `app/gemma/runtime_factory.py` | Constrói runtime configurado | Configuração | Runtime | Deve falhar se dependência obrigatória faltar |
| `app.adapters.document_adapter` | module | `app/adapters/document_adapter.py` | Ingestão de documento/ticket | Arquivo sintético | Dados extraídos | Testes cobrem caminhos de documento |
| `app.storage.sqlite_store` | module | `app/storage/sqlite_store.py` | Persistência SQLite local | Payloads auditáveis | Registros persistidos | Usar migrations versionadas |
| `bench.runner` | module | `bench/runner.py` | Executa suíte de cenários | Manifest/fixtures | Resultados agregados | Usado por Compose benchmark |
| `bench.metrics` | module | `bench/metrics.py` | Calcula métricas de benchmark | Resultados de casos | Métricas | Evitar métrica paralela sem decisão |
| `scripts/check-quality.sh` | script | `scripts/check-quality.sh` | Executa testes, auditoria de blueprint e Sonar opcional | `--sonar`, `SONAR_HOST_URL`, `SONAR_TOKEN` | Status de checks | Usa pytest/python locais quando existem; senão usa Docker |

## Regras

- Atualizar este mapa quando método público/exportado, service, adapter, schema, DTO, endpoint, hook, componente ou contrato mudar.
- Registrar entradas, saídas e efeitos relevantes quando o contrato não for óbvio.
