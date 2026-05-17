.PHONY: help clean demo demo-gpu demo-text ui ui-gpu ui-text demo-ready judge-demo judge-demo-video test bench bench-gpu audit format-check leakage-guard extended-pack-check benchmark-smoke benchmark-validate-text quality prepublish prewarm prewarm-gpu

SCENARIO ?= S10_FIFO_BREAK_JUSTIFIED
COMPOSE_GPU = docker compose -f compose.yaml -f compose.gpu.yaml
JUDGE_URL ?= http://localhost:8501
JUDGE_CAPTURE_URL ?= http://host.docker.internal:8501/
JUDGE_VIDEO_PATH ?= artifacts/judge-demo/pequiflux-gemma-proof.webm
PLAYWRIGHT_CAPTURE_IMAGE ?= mcr.microsoft.com/playwright:v1.54.1-noble

help:
	@echo "Targets:"
	@echo "  make demo       Run the full Ollama/Gemma scenario demo via Docker Compose"
	@echo "  make demo-gpu   Run the full Ollama/Gemma scenario demo with GPU access"
	@echo "  make demo-text  Run the reproducible text-runtime scenario demo"
	@echo "  make ui         Start full Ollama/Gemma Streamlit UI in background; auto-uses GPU when available"
	@echo "  make ui-gpu     Start full Ollama/Gemma Streamlit UI with GPU access"
	@echo "  make ui-text    Start text-runtime Streamlit UI on http://localhost:8501"
	@echo "  make judge-demo Run the canonical judge ritual: reset, pull/prewarm, start UI, run S10, print status"
	@echo "  make judge-demo-video Run judge-demo and save a short proof video with runtime Ollama"
	@echo "  make demo-ready Alias for make judge-demo"
	@echo "  make clean      Remove local caches and generated run logs"
	@echo "  make test       Build and run the Docker test target"
	@echo "  make bench      Run the full Ollama/Gemma scenario benchmark"
	@echo "  make bench-gpu  Run the full Ollama/Gemma scenario benchmark with GPU access"
	@echo "  make audit      Run blueprint audit inside Docker"
	@echo "  make leakage-guard  Run expected_ticket clean-eval leakage guard tests"
	@echo "  make extended-pack-check  Validate B1 extended split manifests"
	@echo "  make quality    Run Black, pytest, audit and validated text benchmark gates as CI"
	@echo "  make prepublish Run the Docker pre-publication gate"

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache cache var/log/*
	find artifacts/latest -type f -name run.log -delete

demo:
	docker compose run --rm demo python -m app.cli.run_scenario --scenario $(SCENARIO)

demo-gpu:
	$(COMPOSE_GPU) run --rm demo python -m app.cli.run_scenario --scenario $(SCENARIO)

demo-text:
	docker compose run --rm demo-text python -m app.cli.run_scenario --scenario $(SCENARIO)

ui:
	docker compose stop ui-text
	@if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then \
		echo "NVIDIA GPU detected; starting Gemma/Ollama UI with compose.gpu.yaml"; \
		$(COMPOSE_GPU) --profile ui up -d --build ui; \
		$(COMPOSE_GPU) ps; \
	else \
		echo "No NVIDIA GPU detected; starting Gemma/Ollama UI with CPU Compose"; \
		docker compose --profile ui up -d --build ui; \
		docker compose ps; \
	fi

ui-gpu:
	docker compose stop ui-text
	$(COMPOSE_GPU) --profile ui up -d --build ui
	$(COMPOSE_GPU) ps

ui-text:
	docker compose --profile ui-text up --build ui-text

judge-demo:
	@set -e; \
	docker compose down --remove-orphans >/dev/null 2>&1 || true; \
	$(COMPOSE_GPU) down --remove-orphans >/dev/null 2>&1 || true; \
	docker compose stop ui-text >/dev/null 2>&1 || true; \
	if command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; then \
		compose_cmd='$(COMPOSE_GPU)'; \
		stack_label='gpu'; \
		echo "NVIDIA GPU detected; running judge demo with compose.gpu.yaml"; \
	else \
		compose_cmd='docker compose'; \
		stack_label='cpu'; \
		echo "No NVIDIA GPU detected; running judge demo with CPU Compose"; \
	fi; \
	echo "Pulling and prewarming model $${GEMMA_MODEL:-gemma4:e2b}"; \
	eval "$$compose_cmd --profile gemma-setup run --rm gemma-init"; \
	eval "$$compose_cmd --profile gemma-setup run --rm gemma-prewarm"; \
	echo "Starting UI stack"; \
	eval "$$compose_cmd --profile ui up -d --build ui"; \
	echo "Running live scenario $(SCENARIO)"; \
	eval "$$compose_cmd run --rm demo python -m app.cli.run_scenario --scenario $(SCENARIO)"; \
	ui_health='unreachable'; \
	for attempt in $$(seq 1 30); do \
		if curl -fsS $(JUDGE_URL)/_stcore/health >/tmp/pequiflux-ui-health.txt 2>/dev/null; then \
			ui_health="$$(cat /tmp/pequiflux-ui-health.txt)"; \
			break; \
		fi; \
		sleep 2; \
	done; \
	model_status="$$(eval "$$compose_cmd exec -T gemma ollama list" 2>/dev/null | grep -E "^$${GEMMA_MODEL:-gemma4:e2b}[[:space:]]" || true)"; \
	echo ""; \
	echo "Judge demo ready"; \
	echo "URL: $(JUDGE_URL)"; \
	echo "Runtime: ollama"; \
	echo "Model: $${GEMMA_MODEL:-gemma4:e2b}"; \
	echo "Scenario: $(SCENARIO)"; \
	echo "UI healthcheck: $$ui_health"; \
	echo "Stack: $$stack_label"; \
	if [ -n "$$model_status" ]; then \
		echo "Model status: cached"; \
	else \
		echo "Model status: not confirmed by ollama list"; \
	fi; \
	echo "Services:"; \
	eval "$$compose_cmd ps"

demo-ready: judge-demo

judge-demo-video:
	@$(MAKE) judge-demo
	@mkdir -p $(dir $(JUDGE_VIDEO_PATH))
	docker run --rm --add-host=host.docker.internal:host-gateway -e PEQUIFLUX_UI_URL=$(JUDGE_CAPTURE_URL) -e PEQUIFLUX_JUDGE_VIDEO_PATH=/work/$(JUDGE_VIDEO_PATH) -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright -e PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 -v "$(CURDIR):/work" -w /work $(PLAYWRIGHT_CAPTURE_IMAGE) bash -lc "mkdir -p /tmp/pequiflux-playwright && cd /tmp/pequiflux-playwright && npm init -y >/dev/null 2>&1 && npm install --silent playwright@1.54.1 >/dev/null 2>&1 && PLAYWRIGHT_MODULE=/tmp/pequiflux-playwright/node_modules/playwright/index.js node /work/scripts/capture_judge_demo_video.mjs"
	@echo "Judge demo video: $(JUDGE_VIDEO_PATH)"

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

prepublish:
	./scripts/prepublish_check.sh

prewarm:
	docker compose --profile gemma-setup run --rm gemma-init
	docker compose --profile gemma-setup run --rm gemma-prewarm

prewarm-gpu:
	$(COMPOSE_GPU) --profile gemma-setup run --rm gemma-init
	$(COMPOSE_GPU) --profile gemma-setup run --rm gemma-prewarm
