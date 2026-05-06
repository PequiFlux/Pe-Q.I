# Gemma 4

## Papel no sistema

Gemma é a camada de interpretação documental e apoio a classificação ambígua, não o árbitro final da decisão operacional.

Faz:

- interpretar ticket PDF/imagem e produzir `ParsedTicket`
- ajudar na classificação de exceções ambíguas
- expor ambiguidade explicitamente quando a verdade não é suficiente

`reason_summary` é gerado de forma determinística a partir da decisão formal; Gemma interpreta documentos e ajuda em classificação ambígua.

O `ToolGateway` está implementado e é usado no fluxo `full` para executar tools determinísticas sob whitelist, ordem de estados, validação de IDs locais e log estruturado. No fluxo atual, o orquestrador passa uma única tool permitida para cada estado; Gemma solicita essa tool permitida sob contrato, sem escolher livremente entre comandos.

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

O caminho mínimo (`make demo-text`, `make ui-text` ou `docker run --rm pequiflux-yard-copilot:local`) usa `PEQUIFLUX_GEMMA_RUNTIME=text` e não sobe Ollama. Esse modo existe para reprodutibilidade básica em máquinas sem GPU/modelo local.

O Compose completo sobe um serviço local `gemma` com Ollama e injeta o runtime na aplicação:

- `PEQUIFLUX_GEMMA_RUNTIME=ollama`
- `GEMMA_BASE_URL=http://gemma:11434`
- `GEMMA_MODEL=gemma4:latest` por padrão
- `OLLAMA_IMAGE=ollama/ollama:latest` por padrão, para runtime com suporte a GPU quando Docker/NVIDIA estiver disponível

O modelo precisa estar cacheado no volume `gemma-models` antes da demo real:

```bash
GEMMA_MODEL=gemma4:latest docker compose --profile gemma-setup run --rm gemma-init
```

Se o runtime não responder ou o modelo não existir, o sistema falha fechado e retorna erro/revisão em vez de trocar automaticamente para parser heurístico.

## Prompting e saída

- prompting contract-first
- enums curtos e estáveis
- preferir `unknown` e `needs_human_review` a inventar fatos
- nenhuma decisão final sem validação externa
- nenhuma instrução derivada da nota do operador é executada diretamente

## ToolGateway

Whitelist atual:

- `validate_hard_constraints`
- `rank_candidates`
- `generate_audit_payload`

Regras:

- validar nome e argumentos antes de executar
- validar ordem pela máquina de estados
- validar IDs contra estado local
- registrar tentativas em log estruturado

No fluxo `full`, o orquestrador passa constraints, ranking e auditoria pelo `ToolGateway`. Em cada etapa, Gemma solicita a tool permitida para o estado atual sob whitelist; ele não decide livremente qual tool executar. Gemma interpreta documentos e apoia classificação ambígua, mas não decide hard constraints. A mensagem ao motorista é composta por serviço determinístico local.

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
