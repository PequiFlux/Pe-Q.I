SHELL := /usr/bin/env bash

# Configuration
RUNTIME ?= text
ACCEL ?= cpu
SCENARIO ?= S10_FIFO_BREAK_JUSTIFIED
SUITE ?= sample
VALIDATE ?= 0
VIDEO ?= 0
VARIANT ?= full

COMPOSE = docker compose
COMPOSE_GPU = docker compose -f compose.yaml -f compose.gpu.yaml
JUDGE_URL ?= http://localhost:8501
JUDGE_CAPTURE_URL ?= http://host.docker.internal:8501/
JUDGE_VIDEO_PATH ?= artifacts/judge-demo/pequiflux-gemma-proof.webm
PLAYWRIGHT_CAPTURE_IMAGE ?= mcr.microsoft.com/playwright:v1.54.1-noble

ifeq ($(ACCEL),gpu)
COMPOSE_RUN = $(COMPOSE_GPU)
else ifeq ($(ACCEL),cpu)
COMPOSE_RUN = $(COMPOSE)
else
$(error Unsupported ACCEL '$(ACCEL)'. Use ACCEL=cpu or ACCEL=gpu)
endif

ifeq ($(RUNTIME),gemma)
CLI_RUNTIME = ollama
else ifeq ($(RUNTIME),ollama)
CLI_RUNTIME = ollama
else ifeq ($(RUNTIME),text)
CLI_RUNTIME = text
else
$(error Unsupported RUNTIME '$(RUNTIME)'. Use RUNTIME=text or RUNTIME=gemma)
endif

ifeq ($(SUITE),sample)
EVAL_MODE = benchmark
EVAL_MANIFEST = scenarios/manifest.json
EVAL_SCENARIO_DIR = scenarios
ifeq ($(VALIDATE),1)
EVAL_OUTPUT ?= /tmp/pequiflux-benchmark-validate
else
EVAL_OUTPUT ?= /tmp/pequiflux-benchmark-sample
endif
else ifeq ($(SUITE),extended)
EVAL_MODE = benchmark
EVAL_MANIFEST = scenarios/manifest.json
EVAL_SCENARIO_DIR = scenarios
EVAL_OUTPUT ?=
else ifeq ($(SUITE),public-test)
EVAL_MODE = clean
EVAL_MANIFEST = scenarios/extended/public_test_frozen/manifest.json
EVAL_SCENARIO_DIR = scenarios/extended/public_test_frozen
EVAL_OUTPUT ?= artifacts/eval/public-test
else ifeq ($(SUITE),public-dev)
EVAL_MODE = clean
EVAL_MANIFEST = scenarios/extended/public_dev/manifest.json
EVAL_SCENARIO_DIR = scenarios/extended/public_dev
EVAL_OUTPUT ?= artifacts/eval/public-dev
else ifeq ($(SUITE),private-holdout)
EVAL_MODE = clean
EVAL_MANIFEST = scenarios/extended/private_holdout/manifest.json
EVAL_SCENARIO_DIR = scenarios/extended/private_holdout
EVAL_OUTPUT ?= artifacts/eval/private-holdout
else ifeq ($(SUITE),public-train)
EVAL_MODE = clean
EVAL_MANIFEST = scenarios/extended/public_train/manifest.json
EVAL_SCENARIO_DIR = scenarios/extended/public_train
EVAL_OUTPUT ?= artifacts/eval/public-train
else
$(error Unsupported SUITE '$(SUITE)'. Use sample, extended, public-test, public-dev, private-holdout, or public-train)
endif

ifeq ($(VALIDATE),1)
EVAL_VALIDATE_FLAG =
else
EVAL_VALIDATE_FLAG = --no-validate
endif

EVAL_OUTPUT_DIR_FLAG = $(if $(strip $(EVAL_OUTPUT)),--output-dir $(EVAL_OUTPUT),)

.PHONY: help doctor setup serve demo eval eval-smoke test lint format check release-check clean clean-artifacts clean-all audit judge ci
.PHONY: _require-docker _eval-benchmark _eval-clean _judge-video-capture
.PHONY: ui ui-text ui-gpu demo-text demo-gpu bench bench-gpu benchmark-smoke benchmark-validate-text quality prepublish judge-demo judge-demo-video demo-ready prewarm prewarm-gpu format-check leakage-guard extended-pack-check kaggle-video kaggle-video-full

help:
	@echo "Public commands:"
	@echo "  make doctor        Verify required host tooling"
	@echo "  make setup         Pull and prewarm the configured Gemma/Ollama model"
	@echo "  make serve         Start the Streamlit UI; use RUNTIME=text|gemma ACCEL=cpu|gpu"
	@echo "  make demo          Run one scenario; use RUNTIME=text|gemma SCENARIO=<id>"
	@echo "  make eval          Run benchmark/eval; use SUITE=<suite> RUNTIME=text|gemma VALIDATE=0|1"
	@echo "  make eval-smoke    Run the cheap text benchmark smoke path"
	@echo "  make test          Build and run the Docker test target"
	@echo "  make lint          Run Black in check mode"
	@echo "  make format        Format Python files with Black"
	@echo "  make check         Run the Docker quality gate"
	@echo "  make release-check Run the pre-publication gate"
	@echo "  make clean         Remove local caches and generated run logs"
	@echo "  make clean-artifacts Remove generated benchmark/eval artifacts"
	@echo "  make clean-all     Run clean and clean-artifacts"
	@echo "  make audit         Run blueprint audit inside Docker"
	@echo "  make judge         Run the judge flow; use VIDEO=1 to capture proof video"
	@echo ""
	@echo "Examples:"
	@echo "  make serve RUNTIME=text"
	@echo "  make serve RUNTIME=gemma ACCEL=gpu"
	@echo "  make demo RUNTIME=gemma ACCEL=gpu SCENARIO=S10_FIFO_BREAK_JUSTIFIED"
	@echo "  make eval SUITE=sample RUNTIME=text VALIDATE=1"
	@echo "  make eval SUITE=public-test RUNTIME=gemma"

_require-docker:
	@command -v docker >/dev/null 2>&1 || { echo "docker is required"; exit 1; }
	@docker compose version >/dev/null 2>&1 || { echo "docker compose is required"; exit 1; }

# Fast local preflight. It checks host tools only; project correctness lives in check/release-check.
doctor: _require-docker
	@command -v curl >/dev/null 2>&1 || { echo "curl is required"; exit 1; }
	@echo "Local tooling OK"

setup: _require-docker
	$(COMPOSE_RUN) --profile gemma-setup run --rm gemma-init
	$(COMPOSE_RUN) --profile gemma-setup run --rm gemma-prewarm

serve: _require-docker
ifeq ($(RUNTIME),text)
	$(COMPOSE) stop ui >/dev/null 2>&1 || true
	$(COMPOSE) --profile ui-text up --build ui-text
else
	$(COMPOSE) stop ui-text >/dev/null 2>&1 || true
	$(COMPOSE_RUN) --profile ui up --build ui
endif

demo: _require-docker
ifeq ($(RUNTIME),text)
	$(COMPOSE) run --rm demo-text python -m app.cli.run_scenario --scenario $(SCENARIO)
else
	$(COMPOSE_RUN) run --rm demo python -m app.cli.run_scenario --scenario $(SCENARIO)
endif

eval: _require-docker
ifeq ($(EVAL_MODE),clean)
	@$(MAKE) _eval-clean
else
	@$(MAKE) _eval-benchmark
endif

eval-smoke:
	@$(MAKE) eval SUITE=sample RUNTIME=text VALIDATE=0 EVAL_OUTPUT=/tmp/pequiflux-benchmark-smoke

_eval-benchmark:
ifeq ($(RUNTIME),text)
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm -e PEQUIFLUX_GEMMA_RUNTIME=text pequiflux-yard-copilot:test python -m app.cli.run_benchmark --manifest $(EVAL_MANIFEST) $(EVAL_OUTPUT_DIR_FLAG) $(EVAL_VALIDATE_FLAG)
else
	$(COMPOSE_RUN) run --rm benchmark python -m app.cli.run_benchmark --manifest $(EVAL_MANIFEST) $(EVAL_OUTPUT_DIR_FLAG) $(EVAL_VALIDATE_FLAG)
endif

_eval-clean:
ifeq ($(RUNTIME),text)
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm -e PEQUIFLUX_GEMMA_RUNTIME=text pequiflux-yard-copilot:test python -m bench.clean_eval --variant $(VARIANT) --runtime text --scenario-dir $(EVAL_SCENARIO_DIR) --manifest $(EVAL_MANIFEST) --output $(EVAL_OUTPUT) --fail-on-leakage
else
	$(COMPOSE_RUN) run --rm benchmark python -m bench.clean_eval --variant $(VARIANT) --runtime $(CLI_RUNTIME) --scenario-dir $(EVAL_SCENARIO_DIR) --manifest $(EVAL_MANIFEST) --output $(EVAL_OUTPUT) --fail-on-leakage
endif

test:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test

lint:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test python -m black --check app bench tests scripts

format:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm -v "$(CURDIR):/app" -w /app pequiflux-yard-copilot:test python -m black app bench tests scripts

audit:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test python -m app.cli.blueprint_audit

leakage-guard:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test pytest -q tests/scenarios/test_no_expected_ticket_leakage.py

extended-pack-check:
	docker build --target test -t pequiflux-yard-copilot:test .
	docker run --rm pequiflux-yard-copilot:test pytest -q tests/scenarios/test_extended_pack_schema.py

check: lint test leakage-guard extended-pack-check audit
	@$(MAKE) eval SUITE=sample RUNTIME=text VALIDATE=1 EVAL_OUTPUT=/tmp/pequiflux-benchmark-validate

release-check:
	./scripts/prepublish_check.sh

ci: check

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache cache tmp test-results
	find var/log -type f -delete 2>/dev/null || true
	find artifacts/latest -type f -name run.log -delete 2>/dev/null || true

clean-artifacts:
	rm -rf artifacts/latest artifacts/eval artifacts/debug*

clean-all: clean clean-artifacts

judge: _require-docker
	@set -e; \
	$(COMPOSE) down --remove-orphans >/dev/null 2>&1 || true; \
	$(COMPOSE_GPU) down --remove-orphans >/dev/null 2>&1 || true; \
	$(COMPOSE) stop ui-text >/dev/null 2>&1 || true
	@$(MAKE) setup ACCEL=$(ACCEL)
	$(COMPOSE_RUN) --profile ui up -d --build ui
	$(COMPOSE_RUN) run --rm demo python -m app.cli.run_scenario --scenario $(SCENARIO)
	@set -e; \
	ui_health='unreachable'; \
	for attempt in $$(seq 1 30); do \
		if curl -fsS $(JUDGE_URL)/_stcore/health >/tmp/pequiflux-ui-health.txt 2>/dev/null; then \
			ui_health="$$(cat /tmp/pequiflux-ui-health.txt)"; \
			break; \
		fi; \
		sleep 2; \
	done; \
	model_status="$$( $(COMPOSE_RUN) exec -T gemma ollama list 2>/dev/null | grep -E "^$${GEMMA_MODEL:-gemma4:e2b}[[:space:]]" || true )"; \
	echo ""; \
	echo "Judge demo ready"; \
	echo "URL: $(JUDGE_URL)"; \
	echo "Runtime: ollama"; \
	echo "Model: $${GEMMA_MODEL:-gemma4:e2b}"; \
	echo "Scenario: $(SCENARIO)"; \
	echo "UI healthcheck: $$ui_health"; \
	echo "Acceleration: $(ACCEL)"; \
	if [ -n "$$model_status" ]; then \
		echo "Model status: cached"; \
	else \
		echo "Model status: not confirmed by ollama list"; \
	fi; \
	echo "Services:"; \
	$(COMPOSE_RUN) ps
	@if [ "$(VIDEO)" = "1" ]; then $(MAKE) _judge-video-capture; fi

_judge-video-capture:
	@mkdir -p $(dir $(JUDGE_VIDEO_PATH))
	docker run --rm --add-host=host.docker.internal:host-gateway -e PEQUIFLUX_UI_URL=$(JUDGE_CAPTURE_URL) -e PEQUIFLUX_JUDGE_VIDEO_PATH=/work/$(JUDGE_VIDEO_PATH) -e PLAYWRIGHT_BROWSERS_PATH=/ms-playwright -e PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 -v "$(CURDIR):/work" -w /work $(PLAYWRIGHT_CAPTURE_IMAGE) bash -lc "mkdir -p /tmp/pequiflux-playwright && cd /tmp/pequiflux-playwright && npm init -y >/dev/null 2>&1 && npm install --silent playwright@1.54.1 >/dev/null 2>&1 && PLAYWRIGHT_MODULE=/tmp/pequiflux-playwright/node_modules/playwright/index.js node /work/scripts/capture_judge_demo_video.mjs"
	@echo "Judge demo video: $(JUDGE_VIDEO_PATH)"

kaggle-video:
	@if [ ! -s artifacts/judge-demo/pequiflux-gemma-proof.webm ]; then \
		$(MAKE) judge VIDEO=1; \
	fi
	python3 video/tools/build_video.py

kaggle-video-full:
	$(MAKE) judge VIDEO=1
	python3 video/tools/build_kaggle_video.py

# Backward-compatible aliases
ui:
	@echo "Deprecated: use 'make serve RUNTIME=gemma'"
	@$(MAKE) serve RUNTIME=gemma

ui-text:
	@echo "Deprecated: use 'make serve RUNTIME=text'"
	@$(MAKE) serve RUNTIME=text

ui-gpu:
	@echo "Deprecated: use 'make serve RUNTIME=gemma ACCEL=gpu'"
	@$(MAKE) serve RUNTIME=gemma ACCEL=gpu

demo-text:
	@echo "Deprecated: use 'make demo RUNTIME=text'"
	@$(MAKE) demo RUNTIME=text SCENARIO=$(SCENARIO)

demo-gpu:
	@echo "Deprecated: use 'make demo RUNTIME=gemma ACCEL=gpu'"
	@$(MAKE) demo RUNTIME=gemma ACCEL=gpu SCENARIO=$(SCENARIO)

bench:
	@echo "Deprecated: use 'make eval RUNTIME=gemma SUITE=extended'"
	@$(MAKE) eval RUNTIME=gemma SUITE=extended

bench-gpu:
	@echo "Deprecated: use 'make eval RUNTIME=gemma ACCEL=gpu SUITE=extended'"
	@$(MAKE) eval RUNTIME=gemma ACCEL=gpu SUITE=extended

benchmark-smoke:
	@echo "Deprecated: use 'make eval-smoke'"
	@$(MAKE) eval-smoke

benchmark-validate-text:
	@echo "Deprecated: use 'make eval SUITE=sample RUNTIME=text VALIDATE=1'"
	@$(MAKE) eval SUITE=sample RUNTIME=text VALIDATE=1 EVAL_OUTPUT=/tmp/pequiflux-benchmark-validate

quality:
	@echo "Deprecated: use 'make check'"
	@$(MAKE) check

prepublish:
	@echo "Deprecated: use 'make release-check'"
	@$(MAKE) release-check

judge-demo:
	@echo "Deprecated: use 'make judge'"
	@$(MAKE) judge SCENARIO=$(SCENARIO)

judge-demo-video:
	@echo "Deprecated: use 'make judge VIDEO=1'"
	@$(MAKE) judge VIDEO=1 SCENARIO=$(SCENARIO)

demo-ready:
	@echo "Deprecated: use 'make judge'"
	@$(MAKE) judge SCENARIO=$(SCENARIO)

prewarm:
	@echo "Deprecated: use 'make setup'"
	@$(MAKE) setup ACCEL=cpu

prewarm-gpu:
	@echo "Deprecated: use 'make setup ACCEL=gpu'"
	@$(MAKE) setup ACCEL=gpu

format-check: lint
