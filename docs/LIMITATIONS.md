# Limitations

Este repositorio e uma prova de conceito tecnica para hackathon. Ele nao deve ser apresentado como sistema produtivo.

## Fora de Escopo

- Nao ha dados reais de campo.
- Não há integração real com ERP, TMS, balança, gate, OCR produtivo ou WhatsApp produtivo.
- Não há operação multiunidade, telemetria em tempo real ou otimização global de pátio.
- Não há garantia de latência produtiva fora do ambiente demonstrado.
- Não há autorização automática para despacho sem operador humano.

## Dados e Cenários

Todos os cenários em `scenarios/cases/` são sintéticos e sanitizados. IDs como `TRK-001`, `DST-COV-01` e `OP-DEMO-01` são placeholders.

## Modelo e Runtime

Gemma é usado como camada de interpretação de documento e explicação controlada. A decisão operacional fica em regras determinísticas versionadas. Se o runtime de modelo faltar ou retornar saída inválida, o sistema falha fechado.

## O Que Pode Ser Reivindicado

- Working proof-of-concept local-first.
- Benchmark sintetico reproduzivel.
- Auditoria de decisões e hard constraints.
- Demonstração de valor sobre FIFO puro em cenários de exceção.

## O Que Nao Pode Ser Reivindicado

- Validação em campo.
- Pronto para producao.
- Substituicao do operador.
- Integração operacional completa.
- Precisao real em ambiente industrial.
