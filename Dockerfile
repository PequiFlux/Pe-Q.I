# syntax=docker/dockerfile:1.7

ARG PYTHON_VERSION=3.11
ARG PYTHON_BASE_IMAGE=python:${PYTHON_VERSION}-slim

FROM ${PYTHON_BASE_IMAGE} AS wheels

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY requirements*.txt ./
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip wheel && \
    python -m pip wheel --wheel-dir /wheels -r requirements-all.txt

FROM ${PYTHON_BASE_IMAGE} AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    PEQUIFLUX_IN_CONTAINER=1

WORKDIR /app

RUN groupadd --system pequiflux && \
    useradd --system --gid pequiflux --home-dir /app --shell /usr/sbin/nologin pequiflux && \
    mkdir -p /app/cache /app/bench/reports /app/var/log /app/var/db && \
    chown -R pequiflux:pequiflux /app

COPY --from=wheels /wheels /wheels
COPY requirements-all.txt requirements-dev.txt requirements-ui.txt requirements.txt ./
RUN python -m pip install --no-index --find-links=/wheels -r requirements-all.txt && \
    rm -rf /wheels

COPY --chown=pequiflux:pequiflux app app
COPY --chown=pequiflux:pequiflux assets assets
COPY --chown=pequiflux:pequiflux bench bench
COPY --chown=pequiflux:pequiflux data data
COPY --chown=pequiflux:pequiflux docs docs
COPY --chown=pequiflux:pequiflux notebooks notebooks
COPY --chown=pequiflux:pequiflux scenarios scenarios
COPY --chown=pequiflux:pequiflux scripts scripts
COPY --chown=pequiflux:pequiflux tests tests
COPY --chown=pequiflux:pequiflux .github/workflows .github/workflows
COPY --chown=pequiflux:pequiflux pyproject.toml technical_blueprint.md README.md README.en.md Makefile LICENSE Dockerfile compose.yaml ./

USER pequiflux

EXPOSE 8501

ENV PEQUIFLUX_GEMMA_RUNTIME=text

CMD ["python", "-m", "app.cli.run_scenario", "--scenario", "S10_FIFO_BREAK_JUSTIFIED"]

FROM runtime AS test
CMD ["pytest", "-q"]

FROM runtime AS ui
CMD ["python", "-m", "streamlit", "run", "app/ui/streamlit_app.py"]

FROM runtime AS default
