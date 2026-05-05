# CODEMAP

Mapa vivo do repositório PequiFlux Yard Copilot.

## Módulos principais

| Módulo | Caminho | Responsabilidade | Dependências principais | Observações |
|---|---|---|---|---|
| UI | `app/ui` | Interface Streamlit em Judge Mode para demonstrar cenários narrativos e a legitimidade da quebra de FIFO antes dos detalhes técnicos | `app/orchestration`, `app/adapters`, `bench/reports` | Primeira dobra abre com faixa de benchmark `fifo`/`heuristic`/`full` do scenario pack, lendo relatório quando disponível ou snapshot explícito quando o container exclui `bench/reports`; depois mostra três casos executáveis, comparação FIFO puro vs Pe-Q.I, fila empilhada dos 5 primeiros caminhões, documento interpretado, regra aplicada e ação do operador; validação técnica usa heatmap de `AuditRecord`; CSV/JSON ficam no Modo técnico |
| CLI | `app/cli` | Entrypoints para cenário, benchmark, prewarm e auditoria de blueprint | `app/orchestration`, `bench`, `scenarios` | Deve continuar executável via Docker |
| Orquestração | `app/orchestration` | Fluxo de decisão, resolução de verdade e máquina de estados | `app/domain`, `app/services`, `app/audit` | Coordena camadas sem substituir regras determinísticas |
| Domínio | `app/domain` | Modelos, enums, constraints, ranking e política determinística | `scenarios/common` | Regras hard-constraint vivem aqui |
| Serviços | `app/services` | Builders, parsers, governança operacional, classificação de exceções e mensagens | `app/domain`, `app/gemma` | Adaptam dados para decisão sem fallback silencioso |
| Gemma | `app/gemma` | Runtime, adapter, schemas, prompts e gateway da camada LLM | `app/domain`, runtime externo | Interpretação deve falhar fechado quando inválida |
| Adapters | `app/adapters` | Leitura de CSV, estados, notas e documentos | `app/domain`, arquivos de cenário | Entrada de dados sintéticos e públicos |
| Storage | `app/storage` | SQLite, migrations e log JSONL | `app/audit`, `app/domain` | Persistência local e auditável |
| Audit | `app/audit` | Payloads e serviço de auditoria | `app/domain`, `app/orchestration` | Preserva rastreabilidade de decisões |
| Benchmarks | `bench` | Runner e métricas do pacote de cenários | `scenarios`, `app/cli` | Evidência para regressão e comparação |
| Evidências | `assets/screenshots`, `bench/reports/sample`, `docs/DEMO_SCRIPT.md`, `docs/HACKATHON_SUBMISSION.md`, `docs/LIMITATIONS.md`, `docs/UI_DECISIONS.md` | Artefatos de avaliação para GitHub/hackathon | `app/ui`, `bench`, `docs` | Mantém demo, benchmark, limites e decisões de UI encontráveis em até dois minutos |
| Scenarios | `scenarios` | Fixtures sintéticas, manifest, schemas JSON e README narrativo por cenário | `tests/scenarios`, `bench` | Fonte de casos de validação; `scenarios/README.md` deve explicar os casos em linguagem humana para vídeo e avaliação |
| Tests | `tests` | Testes unitários e de cenário | `app`, `bench`, `scenarios` | Cobrem constraints, auditoria, runtime e E2E |

## Fluxos importantes

- Cenário CLI/UI: adapters carregam fixtures, orquestração resolve contexto, domínio aplica constraints/ranking quando há verdade suficiente, serviços constroem decisão, auditoria registra resultado terminal.
- Benchmark: `bench/runner.py` executa casos de `scenarios/manifest.json` e compara decisões esperadas.
- LLM: `app/gemma` interpreta contexto; saída ausente ou inválida deve gerar erro/revisão explícita, nunca fallback de decisão.

## Áreas sensíveis

- Não duplicar regras de `app/domain/constraints.py`, `app/domain/ranking.py` ou `app/domain/policy.py`.
- Não introduzir fallback model, fallback heuristic, retry silencioso ou modo degradado.
- Não commitar dados reais, credenciais ou identificadores operacionais fora dos placeholders sintéticos.
- Não tratar `.code-review-graph/` como código-fonte.
