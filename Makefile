.PHONY: help demo demo-gpu demo-text ui ui-gpu ui-text test bench bench-gpu audit format-check leakage-guard extended-pack-check benchmark-smoke benchmark-validate-text quality prewarm prewarm-gpu

SCENARIO ?= S10_FIFO_BREAK_JUSTIFIED
COMPOSE_GPU = docker compose -f compose.yaml -f compose.gpu.yaml

help:
	@echo "Targets:"
	@echo "  make demo       Run the full Ollama/Gemma scenario demo via Docker Compose"
	@echo "  make demo-gpu   Run the full Ollama/Gemma scenario demo with GPU access"
	@echo "  make demo-text  Run the reproducible text-runtime scenario demo"
	@echo "  make ui         Start full Ollama/Gemma Streamlit UI on http://localhost:8501"
	@echo "  make ui-gpu     Start full Ollama/Gemma Streamlit UI with GPU access"
	@echo "  make ui-text    Start text-runtime Streamlit UI on http://localhost:8501"
	@echo "  make test       Build and run the Docker test target"
	@echo "  make bench      Run the full Ollama/Gemma scenario benchmark"
	@echo "  make bench-gpu  Run the full Ollama/Gemma scenario benchmark with GPU access"
	@echo "  make audit      Run blueprint audit inside Docker"
	@echo "  make leakage-guard  Run expected_ticket clean-eval leakage guard tests"
	@echo "  make extended-pack-check  Validate B1 extended split manifests"
	@echo "  make quality    Run Black, pytest, audit and validated text benchmark gates as CI"

demo:
	docker compose run --rm demo python -m app.cli.run_scenario --scenario $(SCENARIO)

demo-gpu:
	$(COMPOSE_GPU) run --rm demo python -m app.cli.run_scenario --scenario $(SCENARIO)

demo-text:
	docker compose run --rm demo-text python -m app.cli.run_scenario --scenario $(SCENARIO)

ui:
	docker compose --profile ui up ui

ui-gpu:
	$(COMPOSE_GPU) --profile ui up ui

ui-text:
	docker compose --profile ui-text up ui-text

test:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test

bench:
	docker compose run --rm benchmark

bench-gpu:
	$(COMPOSE_GPU) run --rm benchmark

audit:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test python -m app.cli.blueprint_audit

format-check:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test python -m black --check app bench tests scripts

leakage-guard:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test pytest -q tests/scenarios/test_no_expected_ticket_leakage.py

extended-pack-check:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test pytest -q tests/scenarios/test_extended_pack_schema.py

benchmark-smoke:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm -e PEQUIFLUX_GEMMA_RUNTIME=text pequiflux-yard-copilot:test python -m app.cli.run_benchmark --manifest scenarios/manifest.json --output-dir /tmp/pequiflux-benchmark --no-validate

benchmark-validate-text:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm -e PEQUIFLUX_GEMMA_RUNTIME=text pequiflux-yard-copilot:test python -m app.cli.run_benchmark --manifest scenarios/manifest.json --output-dir /tmp/pequiflux-benchmark-validate

quality: format-check test leakage-guard extended-pack-check audit benchmark-validate-text

prewarm:
	docker compose --profile gemma-setup run --rm gemma-init
	docker compose --profile gemma-setup run --rm gemma-prewarm

prewarm-gpu:
	$(COMPOSE_GPU) --profile gemma-setup run --rm gemma-init
	$(COMPOSE_GPU) --profile gemma-setup run --rm gemma-prewarm
