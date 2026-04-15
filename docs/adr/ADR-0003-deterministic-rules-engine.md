# ADR-0003: Rules Engine Determinístico

## Status

Accepted

## Contexto

A elegibilidade do despacho envolve restrições físicas, documentais e de governança que precisam ser testáveis e reconstruíveis.

## Decisão

Todas as hard constraints e o ranking operam em código puro, com entradas formais, saídas estruturadas e trilha explícita de falhas e regras disparadas.

## Consequências

- decisões ficam reproduzíveis
- ranking nunca enxerga pares não validados
- override humano continua submetido às mesmas regras duras

