# Forest Loss Monitor — France

Web app showing **tree cover loss** (Hansen/UMD, 2001 → latest year) and **near-real-time forest disturbance alerts** (DIST-ALERT, weekly since 2023) for metropolitan France. You can drill down France → région → département.

> In France, satellite tree cover loss is **not deforestation**: forest area is growing. Loss is mostly clear-cut harvesting, fires, storms and bark-beetle dieback.

Full specification: [SPEC.md](SPEC.md). Changes from v1: [CHANGELOG.md](CHANGELOG.md).

## Architecture

1. Python extractors (`pipeline/`, package `forestfr`) load raw aggregates into DuckDB (`data/warehouse.duckdb`).
2. dbt (`dbt/`) builds tested marts from them.
3. A read-only FastAPI (`api/`) serves the marts.
4. The front end is React + MapLibre + ECharts (`web/`).

Map pixels come straight from the Global Forest Watch tile services.

## Quick start

Requires [uv](https://docs.astral.sh/uv/), Node 24 + [pnpm](https://pnpm.io/) and GNU make.

```bash
cp .env.example .env
make setup
make lint test
```

## Licence

Code: MIT (see [LICENSE](LICENSE)). Data licences and attribution: see SPEC §13.
