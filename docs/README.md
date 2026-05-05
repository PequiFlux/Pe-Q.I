# Documentação Oficial

Esta pasta converte o `technical_blueprint.md` em documentação operacional, modular e curta para implementação no repositório.

## Como ler

- [`product.md`](./product.md): tese, problema, escopo e critérios de sucesso
- [`decision-policy.md`](./decision-policy.md): constraints, política de ranking, verdade do sistema e semântica de decisão
- [`architecture.md`](./architecture.md): módulos, fluxo, máquina de estados, persistência e observabilidade
- [`gemma.md`](./gemma.md): papel do Gemma, prompting contract-first e tool calling contido
- [`contracts.md`](./contracts.md): payloads e contratos centrais de função
- [`scenario-pack.md`](./scenario-pack.md): cenários obrigatórios, benchmark e relatórios
- [`public-repo.md`](./public-repo.md): sanitização, publicação e checklist de repositório público
- [`DEMO_SCRIPT.md`](./DEMO_SCRIPT.md): roteiro de demo/vídeo de 3 minutos para banca
- [`HACKATHON_SUBMISSION.md`](./HACKATHON_SUBMISSION.md): critérios da hackathon mapeados para evidências versionadas
- [`LIMITATIONS.md`](./LIMITATIONS.md): limites explícitos do protótipo e claims não permitidos
- [`UI_DECISIONS.md`](./UI_DECISIONS.md): decisões de interface para operador, FIFO e auditoria
- [`technical_blueprint.md`](./technical_blueprint.md): referência extensa original

## Regra de precedência

O blueprint continua sendo a referência ampla, mas os documentos modulares desta pasta são a referência de implementação do repositório.

Quando houver conflito entre o blueprint e a política atual do repositório, prevalecem estes documentos modulares. Em particular:

- o sistema opera em modo fail-closed;
- não há fallback operacional;
- ausência de verdade suficiente resulta em `REVIEW_REQUIRED` ou `BLOCKED`, nunca degradação silenciosa.
