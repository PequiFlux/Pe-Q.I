.PHONY: help demo ui test bench audit quality prewarm

SCENARIO ?= S10_FIFO_BREAK_JUSTIFIED

help:
	@echo "Targets:"
	@echo "  make demo    Run the default scenario demo via Docker Compose"
	@echo "  make ui      Start Streamlit UI on http://localhost:8501"
	@echo "  make test    Build and run the Docker test target"
	@echo "  make bench   Run the full scenario benchmark"
	@echo "  make audit   Run blueprint audit inside Docker"
	@echo "  make quality Run tests and blueprint audit"

demo:
	docker compose run --rm demo python -m app.cli.run_scenario --scenario $(SCENARIO)

ui:
	docker compose --profile ui up ui

test:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test

bench:
	docker compose run --rm benchmark

audit:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test python -m app.cli.blueprint_audit

quality: test audit

prewarm:
	docker compose --profile gemma-setup run --rm gemma-init
	docker compose --profile gemma-setup run --rm gemma-prewarm
