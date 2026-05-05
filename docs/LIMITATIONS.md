# Limitations

Este repositorio e uma prova de conceito tecnica para hackathon. Ele nao deve ser apresentado como sistema produtivo.

## Fora de Escopo

- Nao ha dados reais de campo.
- Nao ha integracao real com ERP, TMS, balanca, gate, OCR produtivo ou WhatsApp produtivo.
- Nao ha operacao multiunidade, telemetria em tempo real ou otimizacao global de patio.
- Nao ha garantia de latencia produtiva fora do ambiente demonstrado.
- Nao ha autorizacao automatica para despacho sem operador humano.

## Dados e Cenarios

Todos os cenarios em `scenarios/cases/` sao sinteticos e sanitizados. IDs como `TRK-001`, `DST-COV-01` e `OP-DEMO-01` sao placeholders.

## Modelo e Runtime

Gemma e usado como camada de interpretacao de documento e explicacao controlada. A decisao operacional fica em regras deterministicas versionadas. Se o runtime de modelo faltar ou retornar saida invalida, o sistema falha fechado.

## O Que Pode Ser Reivindicado

- Working proof-of-concept local-first.
- Benchmark sintetico reproduzivel.
- Auditoria de decisoes e hard constraints.
- Demonstracao de valor sobre FIFO puro em cenarios de excecao.

## O Que Nao Pode Ser Reivindicado

- Validacao em campo.
- Pronto para producao.
- Substituicao do operador.
- Integracao operacional completa.
- Precisao real em ambiente industrial.
