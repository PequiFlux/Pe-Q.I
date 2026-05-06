# UI Decisions

## Objetivo

A interface principal deve parecer produto operacional, nao painel de banca. O operador entra para criar uma decisao, preencher ou carregar entradas, analisar com Gemma 4, ler o resultado e registrar a acao humana.

## Decisoes Principais

### Fluxo operacional primeiro

A primeira tela segue quatro blocos:

1. Nova decisao: botoes `Carregar exemplo` e `Limpar campos`, fila CSV por upload, ticket/documento PDF/PNG/JPG/TXT por upload, nota do operador, clima em formulario simples ou JSON, e recursos em formulario simples ou JSON.
2. Resultado: status, caminhao recomendado, destino recomendado, motivo operacional, documento interpretado, restricoes criticas e mensagem ao motorista.
3. Acao do operador: aprovar, bloquear ou sobrescrever com motivo.
4. Auditoria tecnica: JSON, matriz de validacao, hashes, regras disparadas e latencia.

### Demo discreta

A UI mantem apenas dois comandos auxiliares antes dos campos: `Carregar exemplo` e `Limpar campos`. O exemplo preenche o pacote com um caso versionado do manifest e permite que avaliadores executem o fluxo como usuarios finais. A demo nao deve transformar a tela principal em benchmark, Judge Mode ou painel comparativo.

### Sem benchmark na tela principal

Benchmark strip, metricas `full`/`heuristic`/`raw_fifo`, texto de banca e comparacao `FIFO chamaria` versus `Pe-Q.I recomenda` ficam fora da superficie operacional principal. Esses artefatos continuam em README, docs e `bench/reports/sample/`.

### Fila como objeto central

Os cinco primeiros caminhoes aparecem como cartoes empilhados. O operador ve quem foi chamado, quem ficou aguardando e quais restricoes bloquearam alternativas, sem precisar abrir JSON.

### Auditoria colapsada

A matriz de validacao, payload JSON, hashes, regras disparadas e latencias continuam disponiveis em `Ver auditoria tecnica`. Eles sao essenciais para rastreabilidade, mas nao competem com a decisao operacional.

### Linguagem operacional

Rotulos como `parse_ticket_document`, `rank_candidates` e `FrontEndPayload` ficam na auditoria tecnica. A primeira leitura usa: `Documento interpretado`, `Restricoes criticas`, `Fila`, `Mensagem ao motorista` e `Acao do operador`.

### Screenshot do README

O README embute o screenshot canonico `assets/screenshots/pequiflux-ui.png` e uma galeria curta em `assets/screenshots/pequiflux-ui-0*.png` mostrando entrada, exemplo carregado, resultado e auditoria.

Para gerar evidencia visual sem clique manual, a UI aceita `PEQUIFLUX_UI_AUTORUN=1`, que carrega o exemplo e deixa a decisao materializada para captura.
