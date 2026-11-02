.PHONY: setup lint test boundaries hansen alerts demo-data transform docs api web all check-release

DBT_FLAGS = --project-dir dbt --profiles-dir dbt

setup:
	uv sync
	cd web && pnpm install
	uv run dbt deps $(DBT_FLAGS)

lint:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	cd web && pnpm lint && pnpm typecheck

test:
	uv run pytest
	cd web && pnpm test

boundaries:
	uv run forestfr extract boundaries

hansen:
	uv run forestfr extract hansen

alerts:
	uv run forestfr extract alerts

demo-data:
	uv run forestfr demo-data

transform:
	uv run dbt build $(DBT_FLAGS)

docs:
	uv run dbt docs generate $(DBT_FLAGS)

check-release:
	uv run forestfr check-release

api:
	uv run uvicorn app.main:app --app-dir api --reload --port 8000

web:
	cd web && pnpm dev

all: boundaries hansen alerts transform
