# Repository Hygiene

This repository should keep source code, documentation, frozen public evidence, synthetic scenarios, and reproducible configuration under version control. Local machine state and generated benchmark outputs must stay outside Git.

## Keep versioned

- Source code under `app/`, `bench/`, `scripts/`, and `tests/`.
- Reproducible scenario inputs under `scenarios/`.
- Frozen public benchmark evidence under `bench/reports/sample/`.
- Stable demo assets under `assets/` and `docs/writeup_assets/`.
- Docker, Compose, CI, and project configuration files.

## Do not version

- Local agent state, including `.codex/`, `.serena/`, `.cursor/`, `.claude/`, `.gemini/`, `.qwen/`, `.continue/`, `.roo/`, `.code-review-graph/`, and root-level agent instruction drafts such as `AGENTS.md` or `GOAL.md`.
- Secrets and local configuration files such as `.env` and `.env.*`.
- Python caches and local environments such as `.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, and `.mypy_cache/`.
- Runtime folders such as `cache/`, `tmp/`, `logs/`, `var/`, and `test-results/`.
- Generated benchmark/evaluation outputs under `artifacts/latest/`, `artifacts/eval/`, and `artifacts/debug*/`.

## Command policy

Use the Makefile as the public command surface:

```bash
make doctor          # verify host tooling
make clean           # remove local caches and logs
make clean-artifacts # remove generated benchmark/eval outputs
make clean-all       # run clean + clean-artifacts
make quality         # run the Docker quality gate
make ci              # alias for quality
make prepublish      # run the pre-publication gate
```

Prefer adding new project tasks to `Makefile` instead of leaving ad hoc commands in local notes. Commands that depend on local-only agent tooling must remain outside the repository.

## Artifact policy

`artifacts/latest/` is intentionally ignored. It is a mutable output location for the most recent run, not a stable evidence source. If an evaluation result must become part of the public record, move it to a named immutable location and document the command, runtime, seed, and commit used to produce it.
