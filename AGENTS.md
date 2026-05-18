# Repository Guidelines

## Project Structure & Module Organization

This repository is currently blueprint-first. The main artifact is [`technical_blueprint.md`](./technical_blueprint.md), which defines scope, assumptions, constraints, and the target architecture for the PequiFlux Yard Copilot. The local `.code-review-graph/` directory is generated tooling state and should not contain source code.

When implementation starts, keep the blueprint mirrored under `docs/technical_blueprint.md` and organize runtime code under:

- `app/` for Streamlit UI and entrypoints
- `domain/` for deterministic rules and decision logic
- `adapters/` for LLM/runtime, SQLite, and file ingestion
- `tests/` for unit and scenario tests
- `scenarios/` for synthetic benchmark fixtures

## Build, Test, and Development Commands

Run project commands through Docker/Compose by default. Do not create or rely on a local `.venv` for normal development, tests, demos, benchmark, or UI execution.

- `docker build -t pequiflux-yard-copilot:local .` builds the default local demo image
- `docker run --rm pequiflux-yard-copilot:local` runs the default CLI demo scenario
- `docker build --target test -t pequiflux-yard-copilot:test .` builds the test image
- `docker run --rm pequiflux-yard-copilot:test` runs the full test suite
- `docker compose run --rm benchmark` runs the scenario benchmark and writes reports
- `docker compose --profile ui up ui` launches the Streamlit UI on port `8501`

Local Python commands are allowed only for quick inspection or emergency debugging when Docker itself is unavailable. If a local environment file or virtualenv is created during debugging, remove it before handing off the repository.

## Reliability Rule

Do not implement fallbacks in this system. There must be no fallback model, fallback heuristic, degraded mode, silent retry path that changes decision logic, or automatic substitution of missing dependencies. If a required input, service, or model output is unavailable or invalid, fail closed with an explicit error or review state; do not continue with reduced behavior.

## Coding Style & Naming Conventions

Use 4-space indentation and type-annotated Python 3.11 code. Prefer small, deterministic functions in `snake_case`; classes and Pydantic models should use `PascalCase`; constants should use `UPPER_SNAKE_CASE`. Name rule identifiers exactly as published in the blueprint, for example `HC_01_OPEN_DESTINATION_BLOCKED_BY_RAIN`. Format with `black` and sort imports with `isort` once those tools are added.

## Testing Guidelines

Use `pytest` for all tests. Place fast unit tests in `tests/unit/test_<module>.py` and end-to-end scenario checks in `tests/scenarios/test_<scenario>.py`. Every hard constraint should have at least one deterministic test, and failure-path tests must confirm the system stops or returns an explicit review/error state instead of using a fallback. New behavior should ship with tests before UI polish.

## Commit & Pull Request Guidelines

This workspace does not currently include Git history, so no local commit convention can be inferred. Adopt Conventional Commits such as `feat: add FIFO ranking stub` or `docs: refine scenario assumptions`. Pull requests should include a short problem statement, impacted blueprint sections, test evidence, and screenshots only for UI changes.

## Security & Configuration Tips

Keep the repository synthetic and public-safe. Do not commit real customer data, credentials, or operator identifiers. Use placeholder IDs such as `OP-DEMO-01`, and keep all thresholds, weights, and scenarios aligned with the sanitized assumptions in the blueprint.

Environment files must not live in the repository root. Delete `.env`, `.env.*`, and local virtualenv directories such as `.venv/` from the repository home before finishing work. Configuration for reproducible project execution should be represented through Docker, Compose, documented placeholders, or explicit runtime inputs, never committed secrets.
