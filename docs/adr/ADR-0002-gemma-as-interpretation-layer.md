# ADR-0002: Gemma como camada de interpretação

## Status

Accepted

## Contexto

O sistema precisa de interpretação documental e contextual sem delegar ao modelo a elegibilidade final ou a mutação do estado.

## Decisão

Gemma fica restrito a parsing e classificação contextual quando necessário. O fluxo `full` usa `ToolGateway` para executar tools permitidas sob contrato; `reason_summary` é gerado de forma determinística a partir da decisão formal.

## Consequências

- regras duras continuam auditáveis em código
- o modelo permanece útil sem se tornar árbitro operacional
- falha do runtime não autoriza improvisação automática
