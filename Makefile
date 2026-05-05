.PHONY: help demo demo-text ui ui-text test bench audit format-check quality prewarm

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
	@echo "  make quality    Run format check, tests and blueprint audit"

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
	docker run --rm pequiflux-yard-copilot:test python -m black --check app/ui app/cli/run_benchmark.py app/services/raw_fifo.py app/services/structured_ticket_parser.py tests/unit/test_raw_fifo.py tests/unit/test_structured_ticket_parser.py tests/unit/test_ui_benchmark_summary.py

quality: format-check test audit

prewarm:
	docker compose --profile gemma-setup run --rm gemma-init
	docker compose --profile gemma-setup run --rm gemma-prewarm
