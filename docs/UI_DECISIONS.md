# UI Decisions

## Objetivo

A interface principal deve parecer produto operacional, não painel de banca. O operador entra para criar uma decisão, preencher ou carregar entradas, analisar com Gemma 4, ler o resultado e registrar a ação humana.

## Decisões Principais

### Fluxo operacional primeiro

A primeira tela segue quatro blocos:

1. Nova decisão: botões `Carregar exemplo`, `Carregar e analisar exemplo` e `Limpar campos`, fila CSV por upload, ticket/documento PDF/PNG/JPG/TXT por upload, nota do operador, clima em formulário simples ou JSON, e recursos em formulário simples ou JSON.
2. Resultado: status, caminhão recomendado, destino recomendado, motivo operacional, documento interpretado, restrições críticas e mensagem ao motorista.
3. Ação do operador: aprovar, bloquear ou sobrescrever com motivo.
4. Auditoria técnica: JSON, matriz de validação, sequência de tools solicitadas pelo Gemma, hashes, regras disparadas e latência.

### Demo discreta

A UI mantém comandos auxiliares no cabeçalho da entrada operacional: `Carregar exemplo`, `Carregar e analisar exemplo` e `Limpar campos`. O exemplo preenche o pacote com um caso versionado do manifest e permite que avaliadores executem o fluxo como usuários finais. A demo não deve transformar a tela principal em benchmark, modo de banca ou painel comparativo.

Ao carregar exemplo, a UI regenera as keys dos uploaders de fila e ticket para impedir que um arquivo carregado anteriormente continue prevalecendo sobre o fixture preenchido.

### Runtime explícito

O sidebar precisa distinguir execução de teste e execução real. Com `PEQUIFLUX_GEMMA_RUNTIME=text`, a UI informa que é modo teste sem Gemma/Ollama e orienta o uso de TXT ou exemplo. Com `ollama`, informa que Gemma 4 está ativo via Ollama.

O botão de análise também acompanha o runtime: em `ollama`, mostra `Analisar com Gemma 4`; em `text`, mostra `Analisar em modo teste` para não sugerir uso real de Gemma/Ollama.

### Recursos sem JSON obrigatório

O formulário simples de recursos inclui destinos disponíveis, destinos bloqueados e `Destinos compatíveis com carga úmida`. Destinos marcados como compatíveis recebem `supported_load_conditions: ["dry", "wet"]`, evitando que o operador precise abrir JSON para modelar moega compatível com carga úmida.

### Sem benchmark na tela principal

Benchmark strip, métricas `full`/`heuristic`/`raw_fifo`, texto de banca e comparações entre variantes ficam fora da superfície operacional principal. Esses artefatos continuam em README, docs e `bench/reports/sample/`.

### Fila como objeto central

Os cinco primeiros caminhões aparecem como cartões empilhados. O operador vê quem foi chamado, quem ficou aguardando e quais restrições bloquearam alternativas, sem precisar abrir JSON.

### Auditoria colapsada

A matriz de validação, sequência de tools solicitadas pelo Gemma, payload JSON, hashes, regras disparadas e latências continuam disponíveis em `Ver auditoria técnica`. Eles são essenciais para rastreabilidade, mas não competem com a decisão operacional.

### Linguagem operacional

Rótulos como `parse_ticket_document`, `rank_candidates` e `FrontEndPayload` ficam na auditoria técnica. A primeira leitura usa: `Documento interpretado pelo Gemma 4`, `Restrições críticas`, `Fila`, `Mensagem ao motorista` e `Ação do operador`. O cartão principal mostra ticket, caminhão lido, tipo de carga, destino extraído, confiança e campos usados na decisão.

### Prova técnica colapsada

A auditoria técnica explicita a prova de runtime sem benchmark: `Runtime`, `Etapa: parse_ticket_document`, `Tipo do arquivo`, `Status` e a lista `Gemma 4 solicitou` com `validate_hard_constraints`, `rank_candidates` e `generate_audit_payload` quando registradas em `AuditRecord.tool_calls`. Cada tool mostra a sequência auditável de status, o `purpose` retornado pelo Gemma e o estado do workflow. Esses sinais ficam dentro de `Ver auditoria técnica`, não na tela principal.

### Screenshot do README

O README embute o screenshot canônico `assets/screenshots/pequiflux-ui.png` e uma galeria curta em `assets/screenshots/pequiflux-ui-0*.png` mostrando entrada, exemplo carregado, resultado e auditoria.

Para gerar evidência visual sem clique manual, a UI aceita `PEQUIFLUX_UI_AUTORUN=1`, que carrega o exemplo e deixa a decisão materializada para captura.
