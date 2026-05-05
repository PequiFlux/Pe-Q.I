# UI Decisions

## Objetivo

A interface foi desenhada para uma banca entender em menos de dois minutos:

1. quem o FIFO chamaria;
2. quem o Pe-Q.I recomenda;
3. por que a quebra de FIFO e legitima;
4. que documento foi interpretado;
5. quais regras bloquearam alternativas;
6. qual decisao ainda cabe ao operador.

## Decisoes Principais

### Judge Mode primeiro

A UI abre com tres casos narrativos em vez de formularios de JSON. Isso reduz densidade tecnica e permite que a banca veja a tese antes dos detalhes.

### Fila como objeto central

Os cinco primeiros caminhoes aparecem como cartoes empilhados. O primeiro da fila recebe estado explicito, como `bloqueado por restricao` ou `mantido aguardando`. O caminhao promovido fica destacado.

### Comparacao FIFO vs Pe-Q.I

A comparacao aparece lado a lado para explicitar o conflito de legitimidade: o sistema nao apenas recomenda outro caminhao, ele mostra por que FIFO puro falharia.

Nos resultados, esse bloco vem antes da fila empilhada para que o screenshot e a banca vejam primeiro o contraste `FIFO chamaria` versus `Pe-Q.I recomenda`.

### Heatmap em vez de tabela

A matriz de validacao tecnica virou heatmap: caminhoes nas linhas, destinos nas colunas, verde para elegivel, vermelho para bloqueado e chips com HC-01, HC-02 etc.

### Linguagem operacional

Rotulos como `parse_ticket_document`, `rank_candidates` e `FrontEndPayload` ficam no painel avancado. A primeira leitura usa: `Documento interpretado`, `Regras conferidas`, `Alternativas bloqueadas`, `Fila recalculada`, `Operador decide`.

### Benchmark visivel

A faixa superior mostra o comparativo `full`, `fifo` e `heuristic` sem abrir notebook. Os detalhes continuam em `bench/reports/sample/`.

### Screenshot do README

O README embute o screenshot canonico `assets/screenshots/pequiflux-ui.png`.

Para gerar evidencia visual sem clique manual, a UI aceita `PEQUIFLUX_UI_AUTORUN=1`, que executa o caso narrativo selecionado e deixa a decisao materializada para captura.
