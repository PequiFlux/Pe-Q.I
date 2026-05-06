# Demo Script

Roteiro para video de 3 minutos da Gemma 4 Good Hackathon.

## 0:00-0:20 — Tese

Mostrar a tela inicial de nova decisao.

Fala:
> Pe-Q.I decide qual caminhao chamar quando FIFO puro parece justo, mas fica errado diante de chuva, carga umida ou documento bloqueado. Gemma interpreta o documento, regras deterministicas decidem, e o operador continua no controle.

## 0:20-0:45 — Carregar Exemplo

Clique em `Carregar exemplo`. O botao `Limpar campos` fica ao lado para voltar ao estado vazio.

Fala:
> Para a demo, eu carrego um pacote sintetico versionado. Em operacao, esses campos viriam do upload da fila CSV, do ticket PDF, imagem ou TXT, da nota do operador, e do clima/recursos em formulario simples ou JSON.

## 0:45-1:10 — Analisar

Clique em `Analisar com Gemma 4`.

Fala:
> A execucao interpreta o documento, reconcilia a nota do operador com clima e recursos, aplica hard constraints e prepara uma decisao auditavel. Se faltar verdade material, o sistema fecha em bloqueio ou revisao, sem fallback operacional.

## 1:10-1:50 — Resultado Operacional

Mostrar status, caminhao recomendado, destino recomendado, motivo operacional, documento interpretado e restricoes criticas.

Fala:
> O operador ve o status da decisao, o caminhao recomendado, o destino, o motivo operacional e os campos extraidos do documento. As restricoes bloqueantes aparecem como regras duras, nao como sugestao do modelo.

## 1:50-2:20 — Fila e Mensagem

Role pela fila visual e pela mensagem ao motorista.

Fala:
> A fila visual mostra quem foi chamado, quem ficou aguardando e quais restricoes explicam o estado de cada caminhao. A mensagem ao motorista transforma a decisao em comunicacao operacional curta.

## 2:20-2:45 — Acao Humana

Mostrar aprovar, bloquear ou sobrescrever com motivo obrigatorio.

Fala:
> O sistema recomenda; o operador governa. Aprovar, bloquear ou sobrescrever exige motivo, e a persistencia registra a acao humana junto da auditoria.

## 2:45-3:00 — Auditoria Tecnica

Abrir `Ver auditoria tecnica`.

Fala:
> A auditoria tecnica fica colapsada: matriz de validacao, regras disparadas, hashes, latencias e JSON completo continuam disponiveis para reconstrucao da decisao.
