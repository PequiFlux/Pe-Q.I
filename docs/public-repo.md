# Repositório Público e Sanitização

## O que pode ser publicado

- código-fonte do monólito modular
- schemas JSON
- prompts sanitizados
- scenario pack sintético
- benchmarks agregados
- ADRs, diagramas e documentação

## O que não pode ser publicado

- nomes reais de clientes
- layouts identificáveis de operação
- placas, CNPJ, nomes de pessoas e IDs reversíveis
- logs reais
- screenshots com dados reais
- segredos, tokens e endpoints produtivos

## Política de sanitização

Princípio: `synthetic-first`.

Regras:

1. usar IDs sintéticos estáveis, como `TRK-001` e `DST-COV-01`
2. não reutilizar nomes ou códigos internos reais
3. deslocar horários, volumes e exemplos para valores sintéticos
4. revisar manualmente prompts, comentários e screenshots
5. não commitar artefatos de debug privado

## Política de logs

Persistir:

- hashes de entrada
- latências
- status
- códigos de erro
- outputs estruturados finais

Não persistir:

- prompt cru
- chain-of-thought
- documento bruto
- nota real de operador

## Scripts mínimos

- `scripts/bootstrap.sh`: ambiente e dependências
- `scripts/prewarm_models.sh`: warmup e identificação do runtime
- `scripts/run_demo.sh`: fluxo de demo
- `app.cli.run_benchmark`: execução das variantes
- `scripts/prepublish_check.sh`: checagens antes da publicação

## Checklist pré-publicação

- secret scan sem findings
- dados sintéticos confirmados
- README e comandos testados
- prompts e logs revisados
- screenshots sanitizadas
- claims alinhadas ao benchmark
