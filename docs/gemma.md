# Gemma 4

## Papel no sistema

Gemma é a camada de interpretação documental e apoio a classificação ambígua, não o árbitro final da decisão operacional.

Faz:

- interpretar ticket PDF/imagem e produzir `ParsedTicket`
- ajudar na classificação de exceções ambíguas
- expor ambiguidade explicitamente quando a verdade não é suficiente

`reason_summary` é gerado de forma determinística a partir da decisão formal; Gemma interpreta documentos e ajuda em classificação ambígua.

O `ToolGateway` está implementado e é usado no fluxo `full` para executar tools determinísticas sob whitelist, ordem de estados, validação de IDs locais e log estruturado. No fluxo atual, Gemma atua como Tool Planner: recebe todas as tools legalmente disponíveis para o `FlowState` atual, escolhe a próxima tool válida e fornece `purpose`.

Não faz:

- decidir hard constraints
- alterar fila, recurso ou qualquer estado autoritativo
- executar comandos arbitrários
- aprovar override humano

## Contrato do runtime

O runtime fica isolado em [`app/gemma/adapter.py`](../app/gemma/adapter.py). O restante da aplicação depende de um adaptador schema-bound, não de um backend específico.

Requisitos:

- multimodal local após setup/cache
- saída estruturada validável
- erros categorizáveis
- integração com `ToolGateway` no fluxo `full`

## Runtime Docker

O caminho mínimo (`make demo RUNTIME=text`, `make serve RUNTIME=text` ou `docker run --rm pequiflux-yard-copilot:local`) usa `PEQUIFLUX_GEMMA_RUNTIME=text` e não sobe Ollama. Esse modo existe para reprodutibilidade básica em máquinas sem GPU/modelo local.

O Compose completo sobe um serviço local `gemma` com Ollama e injeta o runtime na aplicação:

- `PEQUIFLUX_GEMMA_RUNTIME=ollama`
- `GEMMA_BASE_URL=http://gemma:11434`
- `GEMMA_MODEL=gemma4:e2b` por padrão para reduzir peso de setup; `gemma4:e4b` continua recomendado quando o hardware suportar
- `OLLAMA_IMAGE=ollama/ollama:latest` por padrão, para runtime com suporte a GPU quando Docker/NVIDIA estiver disponível

O modelo precisa estar cacheado no volume `gemma-models` antes da demo real:

```bash
GEMMA_MODEL=gemma4:e2b docker compose --profile gemma-setup run --rm gemma-init
```

Se o runtime não responder ou o modelo não existir, o sistema falha fechado e retorna erro/revisão em vez de trocar automaticamente para parser heurístico.

## Prompting e saída

- prompting contract-first
- enums curtos e estáveis
- preferir `unknown` e `needs_human_review` a inventar fatos
- nenhuma decisão final sem validação externa
- nenhuma instrução derivada da nota do operador é executada diretamente

## Gemma Tool Planner e ToolGateway

Whitelist atual:

- `validate_hard_constraints`
- `rank_candidates`
- `generate_audit_payload`

Regras:

- o planner recebe somente tools legalmente disponíveis para o estado atual;
- o loop de tools é limitado a 4 steps por decisão;
- validar nome e argumentos antes de executar
- validar ordem pela máquina de estados
- validar IDs contra estado local
- registrar tentativas em log estruturado

No fluxo `full`, o orquestrador passa constraints, ranking e auditoria pelo `ToolGateway`. Gemma escolhe a próxima tool entre as opções permitidas pelo `FlowState`; o gateway ainda valida whitelist, schema, estado e IDs locais antes da execução. Gemma interpreta documentos e apoia classificação ambígua, mas não decide hard constraints, não altera estado autoritativo e não executa comandos livres. A mensagem ao motorista é composta por serviço determinístico local.

## Sem fallback

O blueprint original tinha seções de fallback. A política oficial do repositório substitui isso por fail-closed:

- runtime indisponível não ativa modo heurístico automático;
- erro persistente de tool call não degrada o fluxo;
- falta de verdade suficiente resulta em `REVIEW_REQUIRED` ou `BLOCKED`.

## O que a UI pode mostrar

- `vehicle_type`
- `document_status`
- `load_condition`
- `primary_exception`
- `parse_confidence`
- `needs_human_review`
- status das tools chamadas

Não mostrar:

- prompt cru
- tokens
- chain-of-thought
- mensagens internas longas
