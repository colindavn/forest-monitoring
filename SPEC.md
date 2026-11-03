# Forest Loss Monitor France — Project Specification

> Audience: Claude Code (implementation agent) and the project owner.
> Status: v1.1 spec, 2 Nov 2026. Former **[VERIFY]** items were checked against live services on 2026-11-02 and are now marked **[VERIFIED 2026-11-02]**; see `CHANGELOG.md` for differences from v1. Owner decisions from the design review are recorded in §15.

---

## 1. Goal

A small web app to visualise **tree cover loss** and **dense time-series disturbance monitoring** for France, with drill-down **France → région → département**.

Users can:
1. See a map of France coloured by forest loss (choropleth) and the underlying 30 m loss pixels.
2. Click a région to see its départements; click a département to see its detail page.
3. See, for any area, the annual loss history (2001 → latest year) and the recent near-real-time disturbance alerts (weekly, from 2023).
4. Compare areas (rankings, % of forest lost, anomalies vs previous years).

### Non-goals (v1)
- No custom ML model training.
- No user accounts, no editing.
- No plot-level EUDR checks.
- Overseas départements (DROM) are out of scope for v1 (see §12).

### Important framing (must appear in the UI)
In France, satellite "tree cover loss" is **not deforestation**: France's forest area is growing. Loss here is mostly **harvesting (coupes rases), fires, storms and bark-beetle dieback**. The UI must say "perte de couvert arboré / perturbations forestières", never "déforestation", and explain this in an "À propos des données" panel.

---

## 2. Decision: API vs. our own pipeline (and where dbt fits)

| Need | Already served ready-to-use by an API? | Decision |
|---|---|---|
| Loss **pixels on the map** (Hansen GFC) | **Yes** — GFW raster tile service | Display directly from tiles. No processing, no storage. |
| Disturbance **alert pixels on the map** (DIST-ALERT) | **Yes** — GFW tile service | Display directly from tiles. |
| Loss **statistics per région / département / year** | **No** — no API returns figures per French région/département with official INSEE boundaries | Compute zonal stats ourselves, store, transform. |
| Alert **statistics per département / week** | **Partly** — GFW Data API can query a raster within a geometry, but one call per polygon, needs an API key, and gives no history/aggregations | Extract per département on a schedule, store, transform. |
| Long history with disturbance cause (1985–2023) | **No API** — European Forest Disturbance Atlas is a Zenodo download | Optional one-off ingest (phase 2). |

**Conclusion: hybrid.**
- Maps: straight from tile APIs.
- Numbers: a small ELT pipeline — Python extracts raw aggregates → DuckDB → **dbt** builds the analytics tables the app reads.

**dbt is justified, but scoped to tabular transformations.** Raster processing (zonal statistics) happens upstream in Python/Google Earth Engine; dbt takes the raw per-département aggregates and produces clean, tested, documented marts (rollups to région/France, rates, rankings, rolling averages, anomalies). This gives the project a readable, testable lineage of "how each number on screen was produced", which is the stated reason for using dbt.

---

## 3. Data sources

### 3.1 Boundaries (reference)
- **IGN ADMIN-EXPRESS COG CARTO** (generalised, official INSEE codes), from the IGN Géoplateforme. **[VERIFIED 2026-11-02]** Edition **4.0 (2026-01-01)**. Source format: France-wide **FlatGeobuf, WGS84 (EPSG:4326)**, one file per layer, no archive:
  - `https://data.geopf.fr/telechargement/download/ADMIN-EXPRESS-COG-CARTO/ADMIN-EXPRESS-COG-CARTO_4-0__FLATGEOBUF_WGS84G_FRA_2026-01-01/region.fgb` (~7.6 MB)
  - `.../departement.fgb` (~12.9 MB)
  - Layers `region` and `departement` (lowercase since 4.0). Fields: `code_insee`, `nom_officiel`, and on `departement` also `code_insee_de_la_region`. The 3.x names `INSEE_REG` / `INSEE_DEP` / `NOM` no longer exist.
  - Files include DROM → filter to metropolitan France (13 régions, 96 départements incl. 2A/2B).
  - Internally the keys are named `insee_reg` (e.g. `"84"`) and `insee_dep` (e.g. `"01"`, `"2A"`). **Always treat codes as strings.**
  - Areas are computed in Lambert-93 (EPSG:2154).
- Two geometry versions:
  - full-resolution (for zonal stats, uploaded to GEE as an asset);
  - simplified (topology-preserving, ~1–2 % of vertices) GeoJSON/TopoJSON for the web map.

### 3.2 Annual tree cover loss — Hansen / UMD Global Forest Change
- 30 m, Landsat-based, years 2001–2025 (2025 released April 2026).
- Google Earth Engine asset: `UMD/hansen/global_forest_change_2025_v1_13` **[VERIFIED 2026-11-02 — latest; no 2026_v1_14 yet]**.
- Bands used: `treecover2000` (0–100 %), `lossyear` (0 = no loss, 1–25 → 2001–2025), `loss`; `datamask` (1 = land) available.
- **Forest definition (configurable, default):** `treecover2000 >= 30` %. Expose the threshold as a pipeline parameter (allowed: 10, 15, 20, 25, 30, 50, 75). **v1 computes 10, 30 and 50**; UI offers a 3-option threshold toggle (default 30).
- Optional companion: **Tree cover loss from fires** (UMD) to split fire vs non-fire loss — GFW dataset `umd_tree_cover_loss_from_fires` **[VERIFIED: exists on GFW Data API, v1.13; tiles available]**. Phase 2.

### 3.3 Near-real-time disturbance — DIST-ALERT (UMD / NASA OPERA)
- 30 m, from Harmonized Landsat-Sentinel-2 (HLS), alerts every 2–4 days, global, record starts 2023.
- Access for stats: **GFW Data API** dataset `umd_glad_dist_alerts` queried with a département geometry (requires a free GFW API key, header `x-api-key`; queries without key → 403). **[VERIFIED 2026-11-02]**
  - Version: `latest` redirects (307) to a weekly version, e.g. `v20261031`. Resolve and store the concrete version.
  - Query: `POST /dataset/umd_glad_dist_alerts/{version}/query/json`, body `{"sql": "...", "geometry": <GeoJSON geometry>}`; table name in SQL is `results`.
  - Fields: date `umd_glad_dist_alerts__date`, confidence `umd_glad_dist_alerts__confidence` (**2 = nominal, 3 = high, 4 = highest**), area `area__ha`, forest filter `umd_tree_cover_density_2000__threshold` (coded class: 1=10, 2=15, 3=20, 4=25, 5=30, 6=50, 7=75 %).
- Fallback access: OPERA `OPERA_L3_DIST-ALERT-HLS_V1` COGs from NASA LP DAAC via `earthaccess` (heavier; only if the GFW API route fails).
- Store **per département × threshold × day × confidence** areas, keeping **3 confidence levels** (`nominal`, `high`, `highest`); weekly rollups are done in dbt.

### 3.4 Forest baseline / context (optional, phase 2)
- **IGN BD Forêt v2** (official French forest map) as an alternative forest mask.
- **European Forest Disturbance Atlas (EFDA) v2.1.1**, Zenodo DOI 10.5281/zenodo.13333034: annual disturbances 1985–2023 with agent (harvest / wind–bark beetle / fire). Gives the "why" behind loss peaks (e.g. 2022 Gironde fires, Grand-Est bark beetle).

### 3.5 Map display layers (no storage)
All tile endpoints below **[VERIFIED 2026-11-02]**: no key, `Access-Control-Allow-Origin: *`, `latest` 307-redirects to the concrete version.
- Hansen loss tiles: `https://tiles.globalforestwatch.org/umd_tree_cover_loss/latest/dynamic/{z}/{x}/{y}.png?start_year=2001&end_year=2025&tree_cover_density_threshold=30` (threshold ∈ 0,10,15,20,25,30,50,75,90).
- DIST-ALERT tiles: `https://tiles.globalforestwatch.org/umd_glad_dist_alerts/latest/dynamic/{z}/{x}/{y}.png?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD&alert_confidence=low|high&tree_cover_density_threshold=30`.
  - The parameter is `alert_confidence` (not `confidence`, which is silently ignored). UI toggle: "toutes" → `low`, "haute confiance" → `high`.
  - Note: the tile tree-cover filter uses **2010** tree cover density, while statistics use **2000** → mention in "À propos".
- Basemaps (IGN Géoplateforme WMTS, no key):
  - Plan IGN v2: `https://data.geopf.fr/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=GEOGRAPHICALGRIDSYSTEMS.PLANIGNV2&STYLE=normal&FORMAT=image/png&TILEMATRIXSET=PM&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}`
  - Orthophotos: same with `LAYER=ORTHOIMAGERY.ORTHOPHOTOS&FORMAT=image/jpeg`.
  - OSM as fallback.

---

## 4. Architecture

```
            ┌──────────────────────── EXTRACT (Python) ───────────────────────┐
 ADMIN-EXPRESS ─► boundaries.py ─► raw.admin_regions / raw.admin_departments    │
 GEE (Hansen)  ─► hansen_zonal.py ─► raw.hansen_loss_dept_year                  │
               ─►                 ─► raw.hansen_forest_extent_dept               │
 GFW Data API  ─► dist_alerts.py ─► raw.dist_alerts_dept_day                    │
 (phase 2) EFDA ─► efda_zonal.py  ─► raw.efda_disturbance_dept_year_agent        │
            └──────────────────────────────┬────────────────────────────────────┘
                                           ▼
                        DuckDB file  data/warehouse.duckdb  (schema raw)
                                           ▼
                     dbt (dbt-duckdb): staging → intermediate → marts
                                           ▼
                     DuckDB schema marts  (+ simplified GeoJSON in data/geo/)
                                           ▼
                FastAPI (read-only)  ──►  React + MapLibre GL front end
                                           ▲
                    GFW raster tiles + IGN basemap loaded directly by the browser
```

### Stack
| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.12 | GEE, geo libs, dbt all Python |
| Raster stats | Google Earth Engine (`earthengine-api`, non-commercial Cloud project) | Hansen is already there; zonal stats over France in minutes, no local raster storage |
| Vector prep | `geopandas`, `shapely`, `mapshaper` (CLI) or `topojson` | Simplification for the web |
| Warehouse | **DuckDB** (+ `spatial` extension) single file | Small data (≈ 96 dépts × 25 years + daily alerts), zero ops |
| Transform | **dbt-core + dbt-duckdb** | Lineage, tests, docs |
| API | FastAPI + `duckdb` (read-only connection) | Thin, fast |
| Front end | React + Vite + TypeScript, **MapLibre GL JS**, **ECharts** (or Recharts) | Free vector map with raster overlays; good time-series charts |
| Orchestration | `Makefile` + GitHub Actions cron | Weekly alerts, yearly Hansen refresh |
| Packaging | `uv` for Python, `pnpm` for front end, Docker Compose for local run |

Data volume estimate: < 50 MB in DuckDB; geometry files < 5 MB.

---

## 5. Repository layout

```
forest-monitoring/
├── README.md
├── CHANGELOG.md
├── LICENSE                      # MIT (code); data licences in §13
├── docs/SETUP_CREDENTIALS.md    # GEE / GFW / GitHub secrets setup
├── SPEC.md                      # this file
├── Makefile
├── docker-compose.yml
├── .env.example                 # GEE_PROJECT, GFW_API_KEY, FOREST_THRESHOLD=30
├── pipeline/                    # Python package: extract & load
│   ├── pyproject.toml
│   ├── forestfr/
│   │   ├── config.py
│   │   ├── boundaries.py        # download ADMIN-EXPRESS, filter metro, simplify, upload to GEE
│   │   ├── hansen_zonal.py      # GEE reduceRegions per dept & year
│   │   ├── dist_alerts.py       # GFW Data API per dept, incremental
│   │   ├── efda_zonal.py        # phase 2
│   │   ├── load.py              # write to DuckDB raw schema (idempotent upserts)
│   │   └── cli.py               # `forestfr extract hansen|alerts|boundaries|all`
│   └── tests/
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml             # duckdb path from env
│   ├── models/
│   │   ├── sources.yml
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   ├── seeds/                   # region_names.csv, dept_names.csv (FR labels, slugs)
│   ├── macros/
│   └── tests/
├── api/
│   ├── app/main.py
│   ├── app/routes/*.py
│   └── tests/
├── web/
│   ├── src/ (components/, pages/, map/, charts/, api/)
│   └── public/geo/              # simplified regions.geojson, departments.geojson
└── data/                        # gitignored: warehouse.duckdb, raw exports
```

---

## 6. Extraction specifications

All extractors are **idempotent** (re-running replaces the same keys) and write a `_loaded_at` timestamp and `_source_version` column.

### 6.1 `boundaries`
1. Download ADMIN-EXPRESS COG CARTO FlatGeobuf (`region.fgb`, `departement.fgb`); keep metropolitan régions (`code_insee` not in `01,02,03,04,06`) and their départements.
2. Source is already EPSG:4326; compute `area_km2` in EPSG:2154.
3. Write `raw.admin_regions(insee_reg, nom, area_km2, geom_wkb)` and `raw.admin_departments(insee_dep, insee_reg, nom, area_km2, geom_wkb)`.
4. Produce simplified `web/public/geo/regions.geojson` and `departments.geojson` with properties `code`, `name`, `parent_code`. Shared borders must stay aligned after simplification (use mapshaper/topojson).
5. Upload full-resolution départements to GEE as `projects/<GEE_PROJECT>/assets/fr_departements`.

### 6.2 `hansen_zonal`
For each département, compute with GEE (`reduceRegions`, `scale=30`, `ee.Reducer.sum()` on pixel area in ha, `tileScale` as needed):
- `forest_2000_ha`: area where `treecover2000 >= threshold`.
- `loss_ha` per `year` 2001–latest: area where `lossyear == year - 2000` **and** `treecover2000 >= threshold`.
Use a grouped reducer on `lossyear` to do all years in one pass. Export to Drive/GCS as CSV or pull via `getInfo` (96 features is small), then load into:
- `raw.hansen_forest_extent_dept(insee_dep, threshold, forest_2000_ha, gfc_version)`
- `raw.hansen_loss_dept_year(insee_dep, threshold, year, loss_ha, gfc_version)`
Run for the default threshold (30). Optionally loop all thresholds.
Validation: France-wide sum should be close to GFW's France dashboard figure for the same threshold (tolerance ±5 %, boundary differences expected). Log the comparison.

### 6.3 `dist_alerts`
- For each département and each threshold (10, 30, 50), query the GFW Data API with the simplified (not web-simplified; ~100 m tolerance) département geometry:
  `SELECT umd_glad_dist_alerts__date, umd_glad_dist_alerts__confidence, SUM(area__ha) FROM results WHERE umd_glad_dist_alerts__date >= '<since>' AND umd_tree_cover_density_2000__threshold >= <class> GROUP BY 1, 2` (class: 10→1, 30→5, 50→6). **[VERIFIED 2026-11-02]**
- Incremental: `since` = max date already loaded minus 30 days (alerts get confirmed/revised); upsert on `(insee_dep, threshold, alert_date, confidence)`.
- First run backfills from 2023-01-01.
- Respect rate limits: sequential calls, retry with exponential backoff, 1 s pause between départements. If a geometry is too large for the API, split by a grid and sum.
- Target table: `raw.dist_alerts_dept_day(insee_dep, threshold, alert_date, confidence_code, area_ha, dataset_version)`; `confidence_code` keeps the raw API value (2/3/4).
- Alerts are restricted to forest pixels (tree cover 2000 ≥ threshold) via the API filter field above.

---

## 7. dbt models

Naming: `stg_*` (1:1 cleaned sources), `int_*` (business logic), `fct_*`/`dim_*`/`mart_*` (what the API reads). Materialise marts as tables.

### 7.1 Staging
| Model | Grain | Notes |
|---|---|---|
| `stg_admin__regions` | région | cast codes to varchar, trim names |
| `stg_admin__departments` | département | + `insee_reg` FK |
| `stg_hansen__forest_extent` | dept × threshold | |
| `stg_hansen__loss` | dept × threshold × year | filter `year between 2001 and latest`, `loss_ha >= 0` |
| `stg_gfw__dist_alerts` | dept × threshold × day × confidence | map confidence code 2/3/4 → `nominal`/`high`/`highest` |

### 7.2 Intermediate
| Model | Logic |
|---|---|
| `int_loss__dept_year` | join loss with forest extent; `loss_pct_of_2000 = loss_ha / forest_2000_ha`; `cum_loss_ha` (window sum by dept ordered by year); zero-fill missing years |
| `int_alerts__dept_week` | ISO week rollup (`date_trunc('week')`), per threshold: `area_ha_nominal`, `area_ha_high`, `area_ha_highest`, `area_ha_high_conf` (= high + highest), `area_ha_all` |

### 7.3 Marts (read by the API)
| Model | Grain | Columns (main) |
|---|---|---|
| `dim_region` | région | `code, name, slug, area_km2, forest_2000_ha` |
| `dim_department` | dept | `code, name, slug, region_code, area_km2, forest_2000_ha` |
| `fct_loss_year` | level × code × year | `level` ∈ {`france`,`region`,`department`}, `code`, `year`, `loss_ha`, `loss_pct_of_2000`, `cum_loss_ha`, `loss_ha_5y_avg`, `yoy_change_pct`. Région and France rows are **sums of département rows** (never recomputed from rasters) so drill-down totals always add up. |
| `fct_alerts_week` | level × code × threshold × week | `area_ha_nominal`, `area_ha_high`, `area_ha_highest`, `area_ha_all`, `area_ha_high_conf`, `area_ha_4w_rolling` |
| `mart_area_kpis` | level × code | latest-year loss, 5-yr average, 2001–latest total, % of 2000 forest lost, trend slope (linear regression on last 10 years), rank within parent level |
| `mart_alert_anomalies` | level × code × week | z-score of weekly alert area vs same ISO week in previous years (only once ≥ 2 years of history), `is_anomaly` (z ≥ 2) |

### 7.4 Tests (dbt)
- `unique` + `not_null` on all keys; `unique_combination_of_columns` on fact grains (dbt_utils).
- `relationships`: department.region_code → dim_region.code.
- `accepted_values`: level, confidence (`nominal`, `high`, `highest`), threshold (10, 30, 50).
- Custom: `loss_ha <= forest_2000_ha` per dept/year; sum of départements = région value in `fct_loss_year`; count of départements = 96; no future dates in alerts.
- Source freshness on `raw.dist_alerts_dept_day` (warn after 10 days, error after 21).

### 7.5 Docs
Every model and column has a description in `schema.yml`; `dbt docs generate` output is published as a static site (link in the app's "À propos" panel). Descriptions must state the forest threshold and that loss ≠ deforestation.

---

## 8. API (FastAPI, read-only)

Base path `/api`. All responses JSON. Codes are strings. Query param `threshold` defaults to 30.

| Method & path | Returns |
|---|---|
| `GET /health` | status, data freshness (latest Hansen year, latest alert date) |
| `GET /areas/france` | France KPIs + list of régions with KPIs |
| `GET /areas/regions/{code}` | région KPIs + its départements with KPIs |
| `GET /areas/departments/{code}` | département KPIs + parent région |
| `GET /loss?level=&code=&from=&to=` | annual series from `fct_loss_year` |
| `GET /alerts?level=&code=&from=&to=&confidence=` | weekly series from `fct_alerts_week` (+ anomaly flags) |
| `GET /choropleth?level=region|department&metric=&year=` | `{code: value}` map for colouring; metrics: `loss_ha`, `loss_pct_of_2000`, `alerts_ha_last_4w`, `trend_slope` |
| `GET /rankings?level=&metric=&year=&parent=&limit=` | sorted list |
| `GET /meta` | data sources, versions, threshold, update dates (for "À propos") |

Validation: 404 for unknown codes; 422 for bad params. CORS limited to the web origin. Cache headers: 1 h.

---

## 9. Front end

### 9.1 Layout
- **Left (≈ 65 %)**: MapLibre map.
- **Right panel**: breadcrumb (France › Région › Département), KPI cards, charts, ranking table.
- **Top bar**: metric selector, year slider (2001–latest), layer toggles, "À propos des données".

### 9.2 Map behaviour
- Initial view: metropolitan France, choropleth by **région** for the selected metric/year.
- Click a région → zoom to it, choropleth switches to its **départements** (others dimmed).
- Click a département → zoom, show département detail in panel.
- Breadcrumb or "back" goes up a level. URL reflects state: `/r/84`, `/d/38?year=2024&metric=loss_pct_of_2000` (shareable).
- Layer toggles:
  - Choropleth (on by default).
  - "Pixels de perte (Hansen)" raster tiles, filtered to the year range selected.
  - "Alertes récentes (DIST-ALERT)" raster tiles, last 90 days by default.
  - Basemap: Plan IGN / Orthophoto IGN.
- Tooltip on hover: name, metric value, rank.
- Colour scales: sequential single-hue **blue** ramp (`#cde2fb → #104281`) with classed breaks (quantiles, 6 classes); legend with units. Blue instead of YlOrRd so the pink/red GFW loss and alert pixels stay visible above the choropleth.

### 9.3 Panel content (for the selected area)
1. KPI cards: forest 2000 (ha), loss latest year (ha and %), total loss since 2001, trend (↑/↓ with slope), alerts last 4 weeks (ha).
2. **Annual loss chart** (bars 2001–latest, with 5-year average line).
3. **Weekly alerts chart** (bars per week since 2023, 3 stacked segments: nominal / high / highest; anomaly weeks highlighted; 4-week rolling line).
4. Ranking table of children (départements of a région, régions of France), sortable, click-through.
5. CSV download of the series shown.

### 9.4 Language & accessibility
- UI in **French**; code, comments and API in English.
- Number formatting `fr-FR` (`12 345,6 ha`).
- Keyboard navigable; colour-blind-safe palettes; charts have table fallbacks.

---

## 10. Operations

### Makefile targets
```
make setup          # uv sync, pnpm install, dbt deps
make boundaries     # extract boundaries (once / yearly)
make hansen         # GEE zonal stats (yearly, after UMD release ~April)
make alerts         # GFW alerts incremental (weekly)
make transform      # dbt build (run + test)
make docs           # dbt docs generate
make api / make web # dev servers
make all            # boundaries hansen alerts transform
```

### Scheduling (GitHub Actions)
- Weekly (Monday 06:00 Europe/Paris): `make alerts transform`, commit/publish the DuckDB file as a release artifact or push to object storage.
- Monthly: check whether a new Hansen version exists in GEE; if yes, open an issue / run `make hansen transform`.
- Secrets: `GEE_SERVICE_ACCOUNT_JSON`, `GEE_PROJECT`, `GFW_API_KEY`.

### Deployment (simple)
- Docker Compose: `api` (FastAPI + DuckDB file mounted read-only) and `web` (static build behind nginx). Any small VM or a free-tier container host works.

---

## 11. Milestones & acceptance criteria

**M0 – Skeleton (day 1–2)**: repo layout, tooling, CI lint/test, `.env.example`.
✅ `make setup` works; CI green.

**M1 – Boundaries + Hansen stats + dbt**
✅ `raw` tables loaded for 96 départements × 2001–latest.
✅ `dbt build` passes all tests; région sums equal département sums.
✅ France total within ±5 % of GFW's published France figure at 30 % threshold (logged).

**M2 – API + map MVP**
✅ Choropleth France → région → département drill-down works with year slider and two metrics.
✅ Annual loss chart and KPI cards for any area.
✅ Hansen raster tiles toggle.

**M3 – Dense time-series monitoring (DIST-ALERT)**
✅ Weekly alerts loaded since 2023 for all départements, incremental refresh works twice in a row without duplicates.
✅ Alerts chart with anomaly highlighting; alerts raster toggle; freshness shown in header.

**M4 – Polish**
✅ "À propos des données" panel (sources, licences, threshold, loss ≠ deforestation, dbt docs link).
✅ CSV export, shareable URLs, French formatting, responsive layout down to tablet width.

**Phase 2 (later)**
- EFDA history 1985–2023 with disturbance **agents** (harvest / wind–bark beetle / fire) → stacked chart.
- Fire vs non-fire split of Hansen loss.
- Own dense time-series run (CCDC in GEE on Landsat + Sentinel-2) for France, compared against DIST-ALERT.
- Monthly NDVI over forest mask per département (Sentinel-2) as a "forest health" curve.
- Overseas départements: Guyane would add tropical products (JRC TMF, RADD, integrated alerts).
- Forest mask alternative: IGN BD Forêt v2.

---

## 12. Open decisions for the owner (defaults in bold)
1. Forest threshold: **30 %** (also offer 10 % / 50 % toggle?).
2. Scope: **metropolitan France only** in v1, or include DROM.
3. Front end: **React + MapLibre** vs a quicker Streamlit prototype.
4. Hosting target (VM, Fly.io, Render, Scaleway…).
5. GEE access: personal non-commercial Cloud project vs service account for CI.

---

## 13. Licences & attribution (display in app)
- Hansen/UMD/Google/USGS/NASA — CC BY 4.0.
- DIST-ALERT — UMD GLAD / NASA OPERA (open).
- Global Forest Watch services — attribution "Global Forest Watch / WRI".
- IGN ADMIN-EXPRESS & basemaps — Licence Ouverte Etalab 2.0.
- EFDA (phase 2) — check Zenodo record licence.

---

## 14. Instructions for Claude Code
- Work milestone by milestone (M0 → M4); stop and summarise at the end of each milestone.
- Before using any **[VERIFY]** item, check it (GEE catalog search, GFW `/datasets` and `/fields` endpoints, tile URL test). If it differs, update this SPEC and note the change in `CHANGELOG.md`.
- Never hard-code secrets; read from `.env`.
- Keep INSEE codes as strings everywhere (`"01"`, `"2A"`).
- Write tests: pytest for extractors (mock GEE/GFW), dbt tests as listed, API tests with a small fixture DuckDB.
- Prefer small, readable modules; type hints; `ruff` + `mypy` for Python, `eslint` + `prettier` for TS.
- Work test-first (red → green), one commit per green cycle with a one-line message, straight to `main`, push at the end of each milestone.

---

## 15. Owner decisions (design review, 2 Nov 2026)
Resolves §12.
1. **Repo**: `forest-monitoring` (name kept to allow extension beyond France), public on GitHub, MIT licence.
2. **Threshold**: compute 10 / 30 / 50 % for both Hansen loss and alerts; default 30; UI toggle.
3. **Scope**: metropolitan France only in v1, but extractors and dbt use **generic admin-level naming** (`country`, `admin_level`, `parent_code`; `country: FR` in config) so other countries / DROM can be added later. API paths and UI stay French-specific (`/regions`, `/departments`).
4. **Front end**: React + Vite + TypeScript + MapLibre GL + ECharts.
5. **Hosting**: deferred. v1 ships Docker Compose (`api` + nginx `web` static build).
6. **Warehouse distribution**: the weekly CI publishes `warehouse.duckdb` as a **GitHub Release asset**; the API container downloads the latest release on start if no local file is mounted.
7. **GEE**: personal non-commercial Cloud project for local yearly `make hansen`; no GEE in CI for v1 (monthly workflow only checks the catalog for a new Hansen version).
8. **Credentials**: none available at build time. CI workflows that need secrets exit cleanly with a notice when the secret is missing. Setup steps are in `docs/SETUP_CREDENTIALS.md`.
9. **Synthetic demo data**: `forestfr demo-data` writes raw tables from real boundaries with fake numbers, `_source_version = 'SYNTHETIC'`. The UI shows a banner when synthetic data is served; release publishing fails if any synthetic row is present. It is also the API test fixture.
10. **Boundaries**: simplified GeoJSON is committed to `web/public/geo/` so the front end works from a fresh clone.
11. **Confidence**: 3 levels kept end to end (`nominal` / `high` / `highest`); `area_ha_high_conf` = high + highest.
12. **Raw table names** (supersede §4/§6 names, follow decision 3). All carry `_source_version` (replaces `gfc_version` / `dataset_version`) and `_loaded_at`:
    - `raw.admin_areas(country, admin_level, code, parent_code, name, area_km2, geom_wkb)`: `admin_level` 1 = région, 2 = département.
    - `raw.hansen_forest_extent(country, code, threshold, forest_2000_ha)`
    - `raw.hansen_loss(country, code, threshold, year, loss_ha)`
    - `raw.dist_alerts_day(country, code, threshold, alert_date, confidence_code, area_ha)`