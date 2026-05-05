.PHONY: help demo demo-text ui ui-text test bench audit format-check benchmark-smoke quality prewarm

SCENARIO ?= S10_FIFO_BREAK_JUSTIFIED

help:
	@echo "Targets:"
	@echo "  make demo       Run the full Ollama/Gemma scenario demo via Docker Compose"
	@echo "  make demo-text  Run the reproducible text-runtime scenario demo"
	@echo "  make ui         Start full Ollama/Gemma Streamlit UI on http://localhost:8501"
	@echo "  make ui-text    Start text-runtime Streamlit UI on http://localhost:8501"
	@echo "  make test       Build and run the Docker test target"
	@echo "  make bench      Run the full Ollama/Gemma scenario benchmark"
	@echo "  make audit      Run blueprint audit inside Docker"
	@echo "  make quality    Run the same Black, pytest, audit and text benchmark smoke gates as CI"

demo:
	docker compose run --rm demo python -m app.cli.run_scenario --scenario $(SCENARIO)

demo-text:
	docker compose run --rm demo-text python -m app.cli.run_scenario --scenario $(SCENARIO)

ui:
	docker compose --profile ui up ui

ui-text:
	docker compose --profile ui-text up ui-text

test:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test

bench:
	docker compose run --rm benchmark

audit:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test python -m app.cli.blueprint_audit

format-check:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test python -m black --check app bench tests scripts

benchmark-smoke:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm -e PEQUIFLUX_GEMMA_RUNTIME=text pequiflux-yard-copilot:test python -m app.cli.run_benchmark --manifest scenarios/manifest.json --output-dir /tmp/pequiflux-benchmark --no-validate

quality: format-check test audit benchmark-smoke

prewarm:
	docker compose --profile gemma-setup run --rm gemma-init
	docker compose --profile gemma-setup run --rm gemma-prewarm
