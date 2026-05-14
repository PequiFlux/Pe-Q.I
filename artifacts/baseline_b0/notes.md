# Baseline B0 Notes

Date: 2026-05-12

## Scope

This baseline records the current B0 public scenario pack before starting the clean B1 evaluation work described in `goal.md`.

It is a contract and consistency baseline, not final hackathon evidence for multimodal generalization.

## Real Entry Points

Repository commands are Docker-first:

- `make test`: builds the `test` Docker target and runs `pytest -q`.
- `make audit`: builds the `test` Docker target and runs `python -m app.cli.blueprint_audit`.
- `make benchmark-validate-text`: runs `python -m app.cli.run_benchmark --manifest scenarios/manifest.json --output-dir /tmp/pequiflux-benchmark-validate`.
- `make bench`: runs the full Ollama/Gemma benchmark through Compose.
- `make ui-text`: starts the Streamlit UI with `PEQUIFLUX_GEMMA_RUNTIME=text`.

The benchmark entrypoint is:

```bash
python -m app.cli.run_benchmark --manifest scenarios/manifest.json --output-dir <output-dir>
```

The blueprint audit entrypoint is:

```bash
python -m app.cli.blueprint_audit
```

## Baseline Command

Generated with:

```bash
docker run --rm --user 0:0 \
  -e PEQUIFLUX_GEMMA_RUNTIME=text \
  -v /home/marcusvinicius/Repositorios/PequiFlux/Pe-Q.I/artifacts:/app/artifacts:Z \
  pequiflux-yard-copilot:test \
  python -m app.cli.run_benchmark \
    --manifest scenarios/manifest.json \
    --output-dir artifacts/baseline_b0
```

The `:Z` volume label was required so the container could write to the mounted `artifacts/` directory.

## Generated Artifacts

- `metrics.json`
- `summary.csv`
- `per_scenario.json`

## B0 Metrics

| Variant | decision_match_at_1 | exception_f1 | ticket_field_accuracy | constraint_violation_rate | audit_completeness | tool_call_success_rate |
|---|---:|---:|---:|---:|---:|---:|
| `raw_fifo` | 0.25 | 0.000 | 0.000 | 0.35 | 0.00 | 0.00 |
| `fifo_safe` | 0.75 | 0.735 | 0.000 | 0.00 | 1.00 | 0.00 |
| `heuristic` | 0.85 | 0.678 | 0.850 | 0.00 | 0.85 | 0.00 |
| `full` | 1.00 | 1.000 | 0.969 | 0.00 | 1.00 | 0.95 |

`full` passed 20/20 scenarios with runtime `text`.

## Checks Already Observed In This Workspace

- Docker test image build: passed.
- `docker run --rm pequiflux-yard-copilot:test`: `127 passed`.
- `docker run --rm pequiflux-yard-copilot:test python -m app.cli.blueprint_audit`: passed 8/8 checks.
- `python -m black --check app/ui/streamlit_app.py`: passed for the current UI change.

Local `pytest` was not available outside Docker (`No module named pytest`), so checks used the repository's Docker path.

## Limitations

- This B0 run uses `PEQUIFLUX_GEMMA_RUNTIME=text`; latency values are fixture latency and do not represent Gemma/Ollama performance.
- Current multimodal CI behavior can rely on sidecar fixtures such as `expected_ticket.json`; this is acceptable for B0 contract validation but is explicitly disallowed for clean B1 evaluation splits.
- `tool_call_success_rate = 0.95` for `full`, below the `goal.md` future gate of `0.98`.
- This baseline does not include `bench.clean_eval`, statistical tests, B1 splits, dashboards, notebooks, or clean multimodal holdouts.
