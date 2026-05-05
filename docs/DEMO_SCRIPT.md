# Demo Script

Roteiro para video de 3 minutos da Gemma 4 Good Hackathon.

## 0:00-0:20 — Tese

Mostrar a tela inicial com a faixa de benchmark.

Fala:
> Pe-Q.I decide qual caminhao chamar quando FIFO puro parece justo, mas fica errado diante de chuva, carga umida ou documento bloqueado. Gemma interpreta o documento, regras deterministicas decidem, e o operador continua no controle.

## 0:20-0:55 — Judge Mode

Clique em `Chuva bloqueando moega aberta` e depois em `Executar caso`.

Fala:
> A banca nao precisa editar JSON. A UI abre com tres casos narrativos. Aqui, o primeiro da fila iria para moega aberta, mas a chuva e a compatibilidade bloqueiam essa alternativa.

## 0:55-1:35 — Fila Como Objeto Central

Role para `Fila em decisao`.

Fala:
> O primeiro caminhao fica marcado como bloqueado por restricao. O caminhao que subiu aparece destacado, com a nova posicao. Isso evita a percepcao de favorecimento ou fura-fila.

## 1:35-2:10 — FIFO vs Pe-Q.I

Mostrar a comparacao `FIFO chamaria` versus `Pe-Q.I recomenda`.

Fala:
> FIFO chamaria TRK-001. Pe-Q.I recomenda TRK-005 para DST-COV-01. A diferenca e verificavel: documento interpretado, regra aplicada e decisao humana disponivel.

## 2:10-2:40 — Evidencia e Auditoria

Abrir `Ver evidencias tecnicas e auditoria`.

Fala:
> A matriz vira um heatmap: caminhoes nas linhas, destinos nas colunas, verde para elegivel e vermelho para bloqueado. Os chips mostram HC-01, HC-05 e outras restricoes.

## 2:40-3:00 — Benchmark e Fechamento

Voltar para a faixa superior.

Fala:
> O scenario pack sintetico compara full, heuristic, fifo seguro e FIFO bruto. O sistema completo roda 10 de 10 cenarios e zero violacoes de regra; o FIFO bruto fica fora do alvo em cenarios documentais e de politica operacional. O projeto e reproduzivel por Docker e deixa evidencias no repositorio.
