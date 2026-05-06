# Docker

This repository ships a local-first container setup for the hackathon demo path.

## Build

```bash
docker build -t pequiflux-yard-copilot:local .
```

The image uses Python 3.11 slim, installs dependencies from `requirements-all.txt`, runs as a non-root user, and keeps runtime state under:

- `cache/`
- `bench/reports/`
- `var/log/`
- `var/db/`

## Run Demo CLI

```bash
docker run --rm pequiflux-yard-copilot:local
docker compose run --rm demo-text
SCENARIO=S02_RAIN_OPEN docker compose run --rm demo-text
```

These commands use `PEQUIFLUX_GEMMA_RUNTIME=text` and do not require GPU, Ollama, or a `gemma` service.

With Gemma/Ollama:

```bash
docker compose run --rm demo
SCENARIO=S02_RAIN_OPEN docker compose run --rm demo
```

## Run Tests

```bash
docker build --target test -t pequiflux-yard-copilot:test .
docker run --rm pequiflux-yard-copilot:test
```

With Compose:

```bash
docker compose --profile ci run --rm test
```

## Run Benchmark

```bash
docker compose run --rm benchmark
```

Reports are written to `bench/reports/extended/` by default. The public frozen sample remains in `bench/reports/sample/`, and the CLI refuses that directory as `--output-dir`. Use `bench/reports/extended-sample/<run_id>` or `/tmp` for temporary sample-like reports.

## Run UI

```bash
docker compose --profile ui-text up ui-text
```

Then open `http://localhost:8501`.

With Gemma/Ollama:

```bash
docker compose --profile ui up ui
```

Then open `http://localhost:8501`.

## Runtime Note

The standalone Docker image defaults to `PEQUIFLUX_GEMMA_RUNTIME=text` so the quickstart works without model setup.

The full UI Compose path starts a local Ollama service named `gemma`, runs `gemma-init` to pull `${GEMMA_MODEL:-gemma4:latest}`, and configures the app with:

- `PEQUIFLUX_GEMMA_RUNTIME=ollama`
- `GEMMA_BASE_URL=http://gemma:11434`
- `GEMMA_MODEL=${GEMMA_MODEL:-gemma4:latest}`
- `OLLAMA_IMAGE=${OLLAMA_IMAGE:-ollama/ollama:latest}`

The `gemma` service declares `gpus: all`; use `demo-text`/`ui-text` on machines without a compatible Docker GPU setup. To use another Ollama image, set `OLLAMA_IMAGE` explicitly.

`make ui` uses that full path, so loading the UI also starts Ollama/Gemma and pulls the configured Gemma 4 tag when it is not already cached. To prewarm the model separately:

```bash
GEMMA_MODEL=gemma4:latest docker compose --profile gemma-setup run --rm gemma-init
```

Use the exact model tag available in your Ollama registry/cache. Tests intentionally set `PEQUIFLUX_GEMMA_RUNTIME=text` so CI remains deterministic and does not require model weights.
