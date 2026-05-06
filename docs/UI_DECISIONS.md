# UI Decisions

## Objetivo

A interface principal deve parecer produto operacional, não painel de banca. O operador entra para criar uma decisão, preencher ou carregar entradas, analisar com Gemma 4, ler o resultado e registrar a ação humana.

## Decisões Principais

### Fluxo operacional primeiro

A primeira tela segue quatro blocos:

1. Nova decisão: botões `Carregar exemplo` e `Limpar campos`, fila CSV por upload, ticket/documento PDF/PNG/JPG/TXT por upload, nota do operador, clima em formulário simples ou JSON, e recursos em formulário simples ou JSON.
2. Resultado: status, caminhão recomendado, destino recomendado, motivo operacional, documento interpretado, restrições críticas e mensagem ao motorista.
3. Ação do operador: aprovar, bloquear ou sobrescrever com motivo.
4. Auditoria técnica: JSON, matriz de validação, hashes, regras disparadas e latência.

### Demo discreta

A UI mantém apenas dois comandos auxiliares no cabeçalho da entrada operacional: `Carregar exemplo` e `Limpar campos`. O exemplo preenche o pacote com um caso versionado do manifest e permite que avaliadores executem o fluxo como usuários finais. A demo não deve transformar a tela principal em benchmark, modo de banca ou painel comparativo.

### Sem benchmark na tela principal

Benchmark strip, métricas `full`/`heuristic`/`raw_fifo`, texto de banca e comparações entre variantes ficam fora da superfície operacional principal. Esses artefatos continuam em README, docs e `bench/reports/sample/`.

### Fila como objeto central

Os cinco primeiros caminhões aparecem como cartões empilhados. O operador vê quem foi chamado, quem ficou aguardando e quais restrições bloquearam alternativas, sem precisar abrir JSON.

### Auditoria colapsada

A matriz de validação, payload JSON, hashes, regras disparadas e latências continuam disponíveis em `Ver auditoria técnica`. Eles são essenciais para rastreabilidade, mas não competem com a decisão operacional.

### Linguagem operacional

Rótulos como `parse_ticket_document`, `rank_candidates` e `FrontEndPayload` ficam na auditoria técnica. A primeira leitura usa: `Documento interpretado pelo Gemma 4`, `Restrições críticas`, `Fila`, `Mensagem ao motorista` e `Ação do operador`. O cartão principal mostra ticket, caminhão lido, tipo de carga, destino extraído, confiança e campos usados na decisão.

### Prova técnica colapsada

A auditoria técnica explicita a prova de runtime sem benchmark: `Runtime`, `Etapa: parse_ticket_document`, `Tipo do arquivo` e `Status`. Esses sinais ficam dentro de `Ver auditoria técnica`, não na tela principal.

### Screenshot do README

O README embute o screenshot canônico `assets/screenshots/pequiflux-ui.png` e uma galeria curta em `assets/screenshots/pequiflux-ui-0*.png` mostrando entrada, exemplo carregado, resultado e auditoria.

Para gerar evidência visual sem clique manual, a UI aceita `PEQUIFLUX_UI_AUTORUN=1`, que carrega o exemplo e deixa a decisão materializada para captura.
