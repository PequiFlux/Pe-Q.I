# Scenarios

Pacote sintetico de casos para demo, benchmark e avaliacao tecnica. O pack principal vive em `scenarios/cases/<SCENARIO>/`, tem 20 casos e fica congelado como vitrine pública. Próximos casos experimentais, de stress ou de falha devem ir para [`extended/`](./extended/).

## Como usar

```bash
make demo SCENARIO=S10_FIFO_BREAK_JUSTIFIED
make bench
```

O manifest completo fica em [`manifest.json`](./manifest.json). A estrutura e os criterios de integridade ficam em [`../docs/scenario-pack.md`](../docs/scenario-pack.md).
O manifest principal deve permanecer alinhado aos 20 casos da vitrine; manifests estendidos, se necessários, devem ficar sob `extended/`.

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
| `S11_IMAGE_ROTATED_WET_LOAD` | Ticket em imagem rotacionada mantém a evidência de carga úmida dependente de parsing multimodal. |
| `S12_PDF_SCANNED_DOCUMENT_BLOCK` | PDF escaneado sem texto extraível exige leitura multimodal para identificar bloqueio documental. |
| `S13_TRUCK_ID_NOT_IN_QUEUE` | Ticket aponta caminhão ausente da fila; a fila local prevalece e a decisão exige revisão. |
| `S14_NOTE_RAIN_WEATHER_NONE_CONFLICT` | Nota menciona chuva, mas o estado local diz tempo seco; conflito material exige revisão. |
| `S15_UNKNOWN_DESTINATION_IN_TICKET` | Ticket e FIFO bruto apontam destino inexistente no estado de recursos; `resource_state` prevalece e bloqueia automação. |
| `S16_ALL_DESTINATIONS_BLOCKED` | Todos os destinos estão inelegíveis; o sistema falha fechado em `BLOCKED`. |
| `S17_OVERRIDE_INELIGIBLE_PAIR` | Override para par inelegível é rejeitado pela validação de hard constraints. |
| `S18_OVERRIDE_ELIGIBLE_NON_TOP_PAIR` | Override para par elegível não-top é permitido quando há motivo explícito e auditável. |
| `S19_TIE_BREAK_EQUAL_SCORE` | Destinos com score empatado usam desempate determinístico lexicográfico. |
| `S20_LARGE_QUEUE_100_TRUCKS` | Fila sintética com 100 caminhões valida estabilidade do ranking e do benchmark. |

## O que olhar no video

- `S10_FIFO_BREAK_JUSTIFIED` e o caso principal para mostrar legitimidade da quebra de FIFO.
- `S03_WET_LOAD`, `S11_IMAGE_ROTATED_WET_LOAD` e `S12_PDF_SCANNED_DOCUMENT_BLOCK` mostram por que parsing multimodal nao e cosmetica de demo.
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
