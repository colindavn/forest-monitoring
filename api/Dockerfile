# Build context: repository root (uv workspace).
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY pipeline/pyproject.toml pipeline/pyproject.toml
COPY api/pyproject.toml api/pyproject.toml
COPY pipeline/forestfr pipeline/forestfr
COPY api/app api/app
RUN uv sync --frozen --no-dev --package forestfr-api

RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
COPY api/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENV WAREHOUSE_PATH=/data/warehouse.duckdb \
    WAREHOUSE_URL=https://github.com/colindavn/forest-monitoring/releases/download/warehouse-latest/warehouse.duckdb \
    WEB_ORIGIN=http://localhost:8080
EXPOSE 8000
ENTRYPOINT ["/entrypoint.sh"]
