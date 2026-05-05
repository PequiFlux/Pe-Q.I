# DECISIONS

Registrar apenas decisões duráveis. Este arquivo não é changelog.

## Decisões

### 2026-05-05 — UI Streamlit dividida por responsabilidade

Contexto:
`app/ui/streamlit_app.py` concentrava carregamento de cenário, preparação de arquivos temporários, montagem de `DecisionRequest`, execução do orquestrador, renderização visual, ação humana e persistência SQLite.

Decisão:
Manter `streamlit_app.py` como composição da tela e dividir responsabilidades em `scenario_loader.py`, `ui_runner.py`, `components/decision_card.py`, `components/validation_matrix.py`, `components/audit_panel.py` e `styles.py`.

Alternativas rejeitadas:
Continuar adicionando novos blocos no arquivo principal da UI.

Impacto:
Novas telas ou blocos reutilizáveis da UI devem entrar no módulo correspondente, sem duplicar regra de domínio nem instanciar orquestrador fora de `ui_runner.py`.

Arquivos/módulos afetados:
- `app/ui/streamlit_app.py`
- `app/ui/scenario_loader.py`
- `app/ui/ui_runner.py`
- `app/ui/components`
- `app/ui/styles.py`

### 2026-05-05 — Infraestrutura de agente versionada

Contexto:
O repositório já continha implementação Python e documentação de produto/arquitetura, mas não continha os mapas vivos exigidos pelo protocolo global de engenharia.

Decisão:
Manter `docs/CODEMAP.md`, `docs/SURFACE_MAP.md`, `docs/DUPLICATION_GUARD.md` e `docs/SETUP_STATUS.md` como documentação viva para orientar alterações futuras, evitar duplicação e registrar pendências de ferramenta.

Alternativas rejeitadas:
Depender apenas do blueprint técnico e do README para orientar mudanças de código.

Impacto:
Mudanças em módulos, contratos públicos, regras reutilizáveis ou decisões duráveis devem atualizar a documentação afetada no mesmo diff.

Arquivos/módulos afetados:
- `docs/CODEMAP.md`
- `docs/SURFACE_MAP.md`
- `docs/DUPLICATION_GUARD.md`
- `docs/SETUP_STATUS.md`

### 2026-05-05 — Estados terminais sempre auditáveis

Contexto:
Os caminhos `PREVIEW_READY`, `REVIEW_REQUIRED` e `BLOCKED` montavam payload, mensagem, persistência e log em fluxos separados, e caminhos de revisão/bloqueio podiam sair sem registro auditável persistido.

Decisão:
Centralizar a finalização terminal no orquestrador e exigir payload de auditoria também para revisão e bloqueio explícitos.

Alternativas rejeitadas:
Manter auditoria apenas para decisões automáticas prontas para preview.

Impacto:
Novos estados terminais devem passar por `DecisionOrchestrator._finalize_payload`.

Arquivos/módulos afetados:
- `app/orchestration/orchestrator.py`
- `app/audit`
- `app/storage`

### 2026-05-05 — Indicação humana de revisão prevalece sobre classificação automática

Contexto:
Notas operacionais com termos como `conferir` e `revisar` representam pedido explícito de revisão humana, mas podiam ser ignoradas quando o ticket também indicava carga úmida.

Decisão:
Classificar indicação humana de revisão antes de classificações automáticas como `WET_LOAD`.

Alternativas rejeitadas:
Permitir decisão automática quando a nota operacional pede conferência manual.

Impacto:
Cenários com `operator_note` pedindo conferência retornam `REVIEW_REQUIRED` até que a revisão seja resolvida.

Arquivos/módulos afetados:
- `app/services/exception_classifier.py`
- `scenarios/cases/S03_WET_LOAD/expected_decision.json`
