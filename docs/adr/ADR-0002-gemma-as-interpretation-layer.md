# ADR-0002: Gemma como camada de interpretação

## Status

Accepted

## Contexto

O sistema precisa de interpretação documental e contextual sem delegar ao modelo a elegibilidade final ou a mutação do estado.

## Decisão

Gemma fica restrito a parsing, classificação contextual quando necessário, tool intents sob contrato e explicação final a partir de decisão formal.

## Consequências

- regras duras continuam auditáveis em código
- o modelo permanece útil sem se tornar árbitro operacional
- falha do runtime não autoriza improvisação automática

