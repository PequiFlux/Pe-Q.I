# Produto

## Tese

O PequiFlux Yard Copilot é um copiloto local-first e auditável para decidir qual caminhão chamar e para qual destino enviar quando o FIFO puro deixa de ser suficiente.

## Problema

O sistema existe para resolver exceções operacionais sem transferir a autoridade decisória para o modelo. A decisão precisa ser:

- tecnicamente defensável;
- auditável;
- rápida para o operador;
- bloqueável ou sobrescrevível por humano.

## Escopo incluído

- ingestão de `queue.csv`, ticket PDF/imagem, nota operacional e estados locais
- parsing multimodal com Gemma para contexto documental
- validação determinística de hard constraints
- ranking explicável
- payload auditável
- UI única filmável
- benchmark com `raw_fifo`, `fifo_safe`, `heuristic` e `full`

## Fora de escopo

- ERP, balança, telemetria, WhatsApp e integrações produtivas
- otimização global de pátio
- dados reais de cliente
- fine-tuning do modelo
- validação em campo
- escopo completo do PequiFlux

## Critérios de sucesso

- `constraint_violation_rate = 0`
- melhora sobre o baseline heurístico em `ticket_field_accuracy`, `exception_f1` e `decision_match_at_1`
- trilha completa para toda quebra de FIFO e todo override
- execução local e reproduzível do pack sintético

## Definição de pronto

- os 10 cenários obrigatórios executam em lote
- o benchmark exporta comparação entre variantes
- a UI mostra recomendação, restrições e ação humana acima da dobra
- o repositório permanece 100% sintético e publicável
