# Demo Script

Roteiro para video de 3 minutos da Gemma 4 Good Hackathon.

Para gerar a prova visual curta sem gravação manual, rode `make judge-demo-video`. Esse alvo executa `make judge-demo`, abre a UI real via Playwright em Docker e salva `artifacts/judge-demo/pequiflux-gemma-proof.webm`. A captura falha se a tela ainda estiver em `modo teste`.

## 0:00-0:20 — Tese

Mostrar a tela inicial de nova decisão.

Fala:
> Pe-Q.I decide qual caminhão chamar quando FIFO puro parece justo, mas fica errado diante de chuva, carga úmida ou documento bloqueado. Gemma interpreta o documento, regras determinísticas decidem, e o operador continua no controle.

## 0:20-0:45 — Carregar exemplo

Antes da gravação, rode `make judge-demo` nesta máquina. Ele zera serviços antigos, sobe a stack real com GPU quando disponível, puxa/preaquece o Gemma, executa o cenário principal e imprime URL, runtime, modelo, healthcheck e status. Para gerar o vídeo curto automaticamente, use `make judge-demo-video`. No bloco `Entrada operacional`, clique em `Carregar e analisar exemplo`. O botão `Carregar exemplo` apenas preenche os campos; `Limpar campos` volta ao estado vazio antes da análise, e `Nova análise` volta ao início depois do resultado.

Fala:
> Para a demo, eu carrego um pacote sintético versionado. Em operação, esses campos viriam do upload da fila CSV, do ticket PDF, imagem ou TXT, da nota do operador, e do clima/recursos em formulário simples ou JSON.

## 0:45-1:10 — Analisar

Se tiver usado apenas `Carregar exemplo`, clique no botão de análise. Para a demo dos juízes, use `make judge-demo`; `make ui` continua útil para subir só a interface, e o botão aparece como `Analisar com Gemma 4`. O caminho `make ui-text` é apenas para teste reproduzível sem modelo.

Fala:
> A execução interpreta o documento, reconcilia a nota do operador com clima e recursos, aplica hard constraints e prepara uma decisão auditável. Se faltar verdade material, o sistema fecha em bloqueio ou revisão, sem fallback operacional.

## 1:10-1:50 — Resultado Operacional

Mostrar status, caminhão recomendado, destino recomendado, motivo operacional, documento interpretado e restrições críticas.

Fala:
> O momento da decisão fica explícito: chamar TRK-005 para DST-COV-01. Logo abaixo, a UI mostra que Gemma 4 está executando via Ollama, quais tools foram executadas, o status da decisão, o caminhão, o destino e o motivo operacional. As restrições bloqueantes aparecem como regras duras, não como sugestão do modelo.

## 1:50-2:20 — Fila e Mensagem

Role pela fila visual e pela mensagem ao motorista.

Fala:
> A fila visual mostra quem foi chamado, quem ficou aguardando e quais restrições explicam o estado de cada caminhão. A mensagem ao motorista transforma a decisão em comunicação operacional curta.

## 2:20-2:45 — Ação Humana

Mostrar aprovar, bloquear ou sobrescrever com motivo obrigatório.

Fala:
> O sistema recomenda; o operador governa. Aprovar, bloquear ou sobrescrever exige motivo, e a persistência registra a ação humana junto da auditoria.

## 2:45-3:00 — Auditoria Técnica

Abrir `Ver auditoria técnica`.

Fala:
> A auditoria técnica fica colapsada: matriz de validação, prova do Gemma Tool Planner, regras disparadas, hashes, latências e JSON completo continuam disponíveis para reconstrução da decisão.
