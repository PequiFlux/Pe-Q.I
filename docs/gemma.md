# Gemma 4

## Papel no sistema

Gemma é a camada de interpretação e explicação, não o árbitro final da decisão operacional.

Faz:

- interpretar ticket PDF/imagem e produzir `ParsedTicket`
- ajudar na classificação de exceções ambíguas
- solicitar tools permitidas sob schema e ordem controlados
- sintetizar `reason_summary` a partir da decisão formal

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
- integração com tool calling contido

## Runtime Docker

O Compose sobe um serviço local `gemma` com Ollama e injeta o runtime na aplicação:

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

## Tool Calling

Whitelist atual:

- `validate_hard_constraints`
- `rank_candidates`
- `generate_audit_payload`

Regras:

- validar nome e argumentos antes de executar
- validar ordem pela máquina de estados
- validar IDs contra estado local
- registrar tentativas em log estruturado

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
