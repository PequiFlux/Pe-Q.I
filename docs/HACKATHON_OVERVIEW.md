# Hackathon Overview

Este documento explica a demo do PequiFlux Yard Copilot para quem abre o
repositorio pela primeira vez. Ele nao e uma fala pronta; e uma leitura guiada do
problema, da solucao e das evidencias da submissao.

## Resumo

PequiFlux Yard Copilot decide qual caminhao chamar e para qual destino enviar
quando o FIFO puro deixa de ser suficiente. A tese tecnica e simples:

> Gemma interprets; deterministic rules decide; the human operator approves.

Gemma 4 interpreta o ticket operacional e, no fluxo completo, tambem atua como
Tool Planner. As regras deterministicas validam restricoes duras, ranqueiam
candidatos e geram uma trilha de auditoria. O operador humano continua no
controle: aprovar, bloquear ou sobrescrever exige justificativa.

## Problema Demonstrado

Em patios logisticos, a primeira posicao da fila nem sempre e a melhor decisao.
Chuva, carga molhada, destinos bloqueados, compatibilidade de recursos e tempo
de espera podem tornar uma decisao FIFO insegura ou ineficiente.

O cenario principal, `S10_FIFO_BREAK_JUSTIFIED`, mostra exatamente esse caso: o
sistema recomenda chamar `TRK-005` para `DST-COV-01`, mesmo que isso quebre a
ordem FIFO. A quebra e justificada por contexto operacional, restricoes
verificaveis e trilha auditavel.

## Como a Solucao Funciona

O fluxo principal separa interpretacao, decisao e governanca:

- Gemma 4 le o ticket e extrai campos operacionais relevantes.
- Gemma 4, no modo `full`, escolhe as tools permitidas para o estado atual do
  fluxo.
- O `ToolGateway` executa apenas tools conhecidas e validas:
  `validate_hard_constraints`, `rank_candidates` e `generate_audit_payload`.
- As regras deterministicas aplicam restricoes duras e calculam a recomendacao.
- A UI mostra resultado, motivo, rejeicoes, impacto na fila, documento
  interpretado e auditoria tecnica.
- Se faltar evidencia material, o sistema fecha em `REVIEW_REQUIRED` ou
  `BLOCKED`; nao ha fallback operacional.

## Como Entender o Video

O video preferido para a banca e
`artifacts/judge-demo/pequiflux-gemma-proof-fluid.webm`. Ele mostra a UI em
ingles, com runtime `Ollama` e modelo Gemma ativo.

Ao assistir, observe estes pontos:

- A tela inicial indica que a demo esta usando Gemma 4 via Ollama, nao modo de
  teste.
- O exemplo versionado carrega um caso sintetico reprodutivel.
- O cartao `Judge proof` confirma runtime, leitura do ticket e tools
  executadas.
- O `Decision moment` mostra a recomendacao operacional.
- A `Decision queue` mostra quem foi chamado, quem ficou aguardando e por que.
- A auditoria tecnica mostra o caminho do Gemma Tool Planner, regras, matriz de
  validacao, hashes, latencias e payload tecnico.

## Claim Correto

Esta submissao deve ser entendida como uma prova de conceito tecnica para a
Gemma 4 Good Hackathon. Ela demonstra uma arquitetura local-first, auditavel e
human-in-the-loop para decisoes operacionais sob restricao.

O repositorio nao reivindica dados reais de campo, validacao industrial,
integracao produtiva ou prontidao para operacao real. O valor da submissao esta
em demonstrar o recorte tecnico de ponta a ponta: interpretacao com Gemma,
decisao deterministica, falha fechada, auditoria e evidencias reproduziveis.

## Evidencias Principais

- UI: `app/ui/streamlit_app.py`
- Papel do Gemma: `docs/gemma.md`
- Video preferido da banca:
  `artifacts/judge-demo/pequiflux-gemma-proof-fluid.webm`
- Prova automatizada curta: `artifacts/judge-demo/pequiflux-gemma-proof.webm`
  via `make judge VIDEO=1`
- Mapa da submissao: `docs/HACKATHON_SUBMISSION.md`
- Limites publicos: `docs/LIMITATIONS.md`
- Benchmark sample publico: `bench/reports/sample/metrics.json`
