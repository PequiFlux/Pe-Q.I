# Política Decisória

## Hard Constraints

As regras duras vivem em código, não em prompt, principalmente em [`app/domain/constraints.py`](../app/domain/constraints.py).

| ID | Regra |
|---|---|
| `HC-01` | destino aberto não recebe carga quando há precipitação |
| `HC-02` | carga úmida só segue para destino compatível |
| `HC-03` | recurso `down` ou `blocked` não recebe despacho |
| `HC-04` | bloqueio documental impede despacho automático |
| `HC-05` | veículo precisa ser compatível com o destino |
| `HC-06` | capacidade abaixo do mínimo operacional torna o destino inelegível |
| `HC-07` | override humano não pode burlar hard constraints |

## Regras de Política

As regras abaixo ordenam somente pares já elegíveis:

| ID | Regra |
|---|---|
| `PR-01` | FIFO é o padrão |
| `PR-02` | prioridade contratual pode justificar quebra de FIFO |
| `PR-03` | capacidade reduzida penaliza ranking |
| `PR-04` | espera excessiva pode adicionar pressão de SLA |
| `PR-05` | ausência de par válido gera `BLOCKED`, não improvisação |
| `PR-06` | destino alinhado à exceção ativa recebe bônus auditável |

## Verdade do Sistema

Hierarquia de verdade:

1. estado local validado: fila, clima e recursos
2. documento parseado com confiança suficiente
3. nota textual do operador

Conflitos materiais nunca são resolvidos implicitamente. Se o conflito afeta elegibilidade, destino ou justificativa, ele precisa aparecer em `material_conflicts` e pode levar a `REVIEW_REQUIRED`.

## `BLOCKED` vs `REVIEW_REQUIRED`

- `BLOCKED`: há evidência suficiente para concluir que não existe despacho automático seguro ou permitido.
- `REVIEW_REQUIRED`: falta verdade suficiente para automatizar com segurança.

## Regra de Operação

- o sistema é fail-closed;
- não existem fallbacks operacionais;
- dado ausente ou inconsistente não pode virar default silencioso;
- override exige motivo e continua passando pela mesma validação.
