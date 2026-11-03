# Forest Loss Monitor — France

Web app showing **tree cover loss** (Hansen/UMD, 2001 → 2025) and **near-real-time forest disturbance alerts** (DIST-ALERT, weekly since 2023) for metropolitan France. You can drill down France → région → département.

> In France, satellite tree cover loss is **not deforestation**: forest area is growing. Loss is mostly clear-cut harvesting, fires, storms and bark-beetle dieback.

- Specification: [SPEC.md](SPEC.md)
- Changes since spec v1: [CHANGELOG.md](CHANGELOG.md)
- Credentials (GEE, GFW): [docs/SETUP_CREDENTIALS.md](docs/SETUP_CREDENTIALS.md)

## Architecture

```
IGN ADMIN-EXPRESS ─┐
GEE (Hansen)      ─┼─► forestfr extractors ─► DuckDB raw ─► dbt marts ─► FastAPI ─► React + MapLibre + ECharts
GFW Data API      ─┘                                                        ▲
                                     GFW raster tiles + IGN basemaps (browser) ┘
```

| Folder | What |
|---|---|
| `pipeline/` | `forestfr` package: extract & load (boundaries, Hansen via GEE, DIST-ALERT via GFW), synthetic demo data |
| `dbt/` | staging → intermediate → marts, with tests and docs; région/France rows are sums of départements |
| `api/` | read-only FastAPI over the marts (`/api/...`, SPEC §8) |
| `web/` | React + Vite + TypeScript front end, French UI |

## Quick start (no credentials, synthetic data)

Requires [uv](https://docs.astral.sh/uv/), Node 24 + [pnpm](https://pnpm.io/) and GNU make.

```bash
cp .env.example .env
make setup
make boundaries     # real IGN boundaries (no key needed)
make demo-data      # SYNTHETIC Hansen + alert numbers (banner shown in the UI)
make transform      # dbt build (models + tests)
make api            # http://localhost:8000/api/health
make web            # http://localhost:5173
```

## Real data

See [docs/SETUP_CREDENTIALS.md](docs/SETUP_CREDENTIALS.md). Then run:

```bash
make boundaries hansen alerts transform   # yearly Hansen, weekly alerts
make publish                              # upload warehouse.duckdb as a GitHub release asset
```

## Docker

```bash
docker compose up --build    # http://localhost:8080
```

- The API serves `./data/warehouse.duckdb`. Without a mounted file, it downloads the latest `warehouse-latest` release asset.
- nginx serves the static build and proxies `/api`.

## Development

```bash
make lint test    # ruff, mypy, eslint, prettier, tsc; pytest (incl. dbt build on a fixture), vitest
make docs         # dbt docs → dbt/target (served at /dbt-docs/ in Docker)
```

## Licence

- Code: MIT (see [LICENSE](LICENSE)).
- Data:
  - Hansen/UMD/Google/USGS/NASA: CC BY 4.0
  - DIST-ALERT: UMD GLAD / NASA OPERA via Global Forest Watch / WRI
  - IGN ADMIN-EXPRESS and basemaps: Licence Ouverte Etalab 2.0
