# SETUP STATUS

Atualizado em: 2026-05-05

## Ferramentas

| Ferramenta | Status | Observação |
|---|---|---|
| Serena | parcial | CLI encontrada em `/home/marcusvinicius/.local/bin/serena`; `serena project health-check` gerou `.serena/project.yml`, mas falhou ao tentar gravar `/home/marcusvinicius/.serena/serena_config.yml` fora do sandbox |
| Graphify | ok | CLI encontrada em `/home/marcusvinicius/.local/bin/graphify` |
| code-review-graph | ok | CLI encontrada em `/home/marcusvinicius/.local/bin/code-review-graph`; build executado com 87 arquivos, 470 nodes e 2784 edges |
| SonarScanner | parcial | CLI encontrada em `/home/marcusvinicius/.local/bin/sonar-scanner`; SonarQube local disponível em `http://127.0.0.1:9000`; não executado nesta rodada porque `SONAR_TOKEN` não foi fornecido |

## Pendências

- O bootstrap global `/home/marcusvinicius/bin/init-agent-repo` falhou porque `.codex` existe como arquivo vazio e bloqueia a criação do diretório `.codex/`.
- Não removi nem renomeei `.codex` para evitar apagar estado local não solicitado.
- Manter `SONAR_TOKEN` fora do repositório; gerar/exportar no ambiente antes de usar Sonar como gate durável.
- `docker build --target test -t pequiflux-yard-copilot:test .` passou em 2026-05-05.
- `docker run --rm pequiflux-yard-copilot:test` passou com 49 testes em 2026-05-05.
- `docker run --rm pequiflux-yard-copilot:test python -m app.cli.blueprint_audit` passou com 7 checks em 2026-05-05.
- `make -n demo`, `make -n ui`, `make -n test`, `make -n bench` e `make -n audit` validaram os atalhos em 2026-05-05.
