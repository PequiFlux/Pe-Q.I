# Scenarios

Pacote sintetico de casos para demo, benchmark e avaliacao tecnica. Cada caso vive em `scenarios/cases/<SCENARIO>/` e traz fila, ticket, nota do operador, clima, recursos e decisao esperada.

## Como usar

```bash
make demo SCENARIO=S10_FIFO_BREAK_JUSTIFIED
make bench
```

O manifest completo fica em [`manifest.json`](./manifest.json). A estrutura e os criterios de integridade ficam em [`../docs/scenario-pack.md`](../docs/scenario-pack.md).

## Leitura humana dos cenarios

| Cenario | Narrativa para avaliacao |
|---|---|
| `S01_BASELINE` | Operacao nominal; nao ha excecao relevante; o sistema deve preservar FIFO. |
| `S02_RAIN_OPEN` | Chuva bloqueia destino aberto; o sistema deve evitar moega exposta e escolher par coberto compativel. |
| `S03_WET_LOAD` | Ticket chega como imagem; a leitura multimodal identifica carga umida e sustenta a revisao humana correta. |
| `S04_CONVEYOR_DOWN` | Recurso local esta indisponivel; moega/correia em manutencao bloqueia despacho automatico para aquele destino. |
| `S05_CONTRACT_PRIORITY` | Prioridade contratual publicada pode justificar quebra de FIFO quando as hard constraints estao limpas. |
| `S06_DOCUMENT_BLOCK` | Documento ou nota fiscal ambigua/bloqueada torna o caminhao inelegivel para despacho automatico. |
| `S07_VEHICLE_INCOMPAT` | Tipo de veiculo nao e compativel com o destino; a restricao fisica bloqueia a alternativa. |
| `S08_REDUCED_CAPACITY` | Capacidade reduzida ainda acima do minimo nao bloqueia, mas penaliza o destino no ranking. |
| `S09_HUMAN_OVERRIDE` | Operador tenta override; o sistema registra motivo e impede que override burle hard constraints. |
| `S10_FIFO_BREAK_JUSTIFIED` | Chuva bloqueia destino aberto; carga umida exige destino compativel; sistema quebra FIFO com justificativa auditavel. |

## O que olhar no video

- `S10_FIFO_BREAK_JUSTIFIED` e o caso principal para mostrar legitimidade da quebra de FIFO.
- `S03_WET_LOAD` mostra por que um ticket em imagem nao pode ser tratado como cosmetica de demo.
- `S06_DOCUMENT_BLOCK` mostra que falta de verdade operacional vira revisao humana, nao fallback.

## Arquivos por caso

```text
ticket.(txt|pdf|png|jpg|jpeg)
queue.csv
operator_note.txt
weather_state.json
resource_state.json
expected_decision.json
expected_ticket.json  # opcional em casos multimodais
```

Todos os dados sao sinteticos e public-safe.
