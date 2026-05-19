# SETUP STATUS

Atualizado em: 2026-05-09

## Ferramentas

| Ferramenta | Status | Observação |
|---|---|---|
| Serena | parcial | `serena project health-check` já gerou `.serena/project.yml`, mas a etapa de configuração global continua fora do escopo do repositório |
| Graphify | ok | Ferramenta presente no ambiente anterior de setup; sem impacto nos gates obrigatórios da hackathon |
| code-review-graph | ok | Ferramenta presente no ambiente anterior de setup; sem impacto nos gates obrigatórios da hackathon |
| Docker | ok | `docker build --target test -t pequiflux-yard-copilot:test .` passou em 2026-05-09 |
| Test image | ok | `docker run --rm pequiflux-yard-copilot:test` passou com `142 passed` em 2026-05-09 |
| Blueprint audit | ok | `docker run --rm pequiflux-yard-copilot:test python -m app.cli.blueprint_audit` passou com 8 checks em 2026-05-09 |
| Benchmark textual validado | ok | `docker run --rm -e PEQUIFLUX_GEMMA_RUNTIME=text pequiflux-yard-copilot:test python -m app.cli.run_benchmark --manifest scenarios/manifest.json --output-dir /tmp/pequiflux-benchmark-validate` passou com 20/20 cenários em 2026-05-09 |
| Demo textual | ok | `docker compose run --rm demo-text python -m app.cli.run_scenario --scenario S10_FIFO_BREAK_JUSTIFIED` passou em 2026-05-09 |
| UI textual | ok | `docker compose --profile ui-text up -d ui-text` + `curl http://127.0.0.1:8501/_stcore/health` retornou `ok` em 2026-05-09 após limpeza prévia com `docker compose down --remove-orphans` |
| Bootstrap | ok | `bash scripts/bootstrap.sh` passou em 2026-05-09 |
| Gemma service | ok | `docker compose --profile gemma-setup up -d gemma` deixou o serviço `gemma` saudável em 2026-05-09 |
| Gemma init | ok | `docker compose --profile gemma-setup run --rm gemma-init` concluiu o pull de `gemma4:e2b` em 2026-05-09 |
| Demo Gemma/Ollama | ok | `docker compose run --rm demo python -m app.cli.run_scenario --scenario S10_FIFO_BREAK_JUSTIFIED` passou em 2026-05-09 |
| UI Gemma/Ollama | ok | `docker compose --profile ui up -d ui` + `curl http://127.0.0.1:8501/_stcore/health` retornou `ok` em 2026-05-09 em stack limpa |
| Black | ok | Declarado em `requirements-dev.txt`/`pyproject.toml`; o gate oficial roda via Docker pelo `scripts/check-quality.sh` |
| SonarScanner | parcial | Continua opcional e fora do gate mínimo; exige `SONAR_TOKEN` no ambiente |

## Pendências

- `.codex/`, `.agents/` e `.serena/` existem como diretórios no workspace atual; a observação antiga sobre `.codex` como arquivo não se aplica mais.
- Manter `SONAR_TOKEN` fora do repositório; gerar/exportar no ambiente antes de usar Sonar como gate adicional.
- O gate mínimo de prontidão hoje é: build da imagem de teste, suíte Docker, blueprint audit e benchmark textual validado.
- A superfície principal continua coerente com esse fluxo: `make demo RUNTIME=text`, `make serve RUNTIME=text`, `make test`, `make eval SUITE=extended RUNTIME=gemma`, `make audit`, `make leakage-guard`, `make extended-pack-check` e `make check`.
- Quando houver GPU NVIDIA disponível no Docker, use `ACCEL=gpu`, por exemplo `make demo RUNTIME=gemma ACCEL=gpu`, `make serve RUNTIME=gemma ACCEL=gpu`, `make eval RUNTIME=gemma ACCEL=gpu SUITE=extended` e `make setup ACCEL=gpu`.
- O modo Gemma/Ollama agora é CPU-first por padrão em `compose.yaml`; use `compose.gpu.yaml` somente quando quiser aceleração NVIDIA.
- O default de `GEMMA_MODEL` foi reduzido para `gemma4:e2b` para facilitar warmup local; `gemma4:e4b` continua opção explícita para demos em hardware mais forte.
- O caminho completo com Gemma/Ollama já foi validado em Docker nesta data, incluindo `gemma`, `gemma-init`, `demo` e `ui`.
