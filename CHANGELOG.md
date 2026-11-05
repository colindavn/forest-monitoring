# Changelog

## v0.1.1 — 2026-11-05

- **Fix**: `make alerts` printed "0 rows upserted" on an empty warehouse. It now stops with an error when no départements are loaded.
- **Fix**: `dbt build` now fails when the département count is not 96 (the old check passed on an empty table) or when Hansen data is missing for a threshold.
- **Fix**: the GFW forest filter takes the threshold in percent (`>= 30`), not the class code (`>= 5`, rejected with a 500 error).
- **Finding**: GFW DIST-ALERT queries only return alerts from 2025-09-24 onwards. This is about 13 months, the same in every dataset version, so the planned 2023+ backfill is not possible through this API. Confidence comes back as `nominal` / `high` text.

- **Fix**: `make boundaries` failed with `EEException: Request payload size exceeds the limit: 10485760 bytes`. The GEE asset upload sent all 96 polygons (~20 MB) in one request. The upload step is removed: `extract hansen` now sends each département's geometry with its own request, each at most ~1.3 MB. `make boundaries` no longer needs GEE.

## v0.1.0 — 2026-11-03 (M0–M4 code, synthetic data)

Implementation choices that differ from or refine spec v1.1:

- **Raw tables** use generic admin-level names: `raw.admin_areas`, `raw.hansen_forest_extent`, `raw.hansen_loss`, `raw.dist_alerts_day` (SPEC §15.12).
- **Slugs** are computed in dbt (`slugify` macro) instead of seed CSVs.
- **Choropleth palette**: single-hue blue instead of YlOrRd, so the pink/red GFW pixels stay visible.
- **Alerts chart**: plots the 4-week rolling sum ÷ 4, a weekly average on the same scale as the bars. The KPI card still shows the 4-week sum.
- **Hansen in GEE**: one `reduceRegion` per département (not one `reduceRegions` for all), so each request stays under the interactive time limit.
- **Département polygons** are uploaded to GEE as a table export task from client-side geometries, simplified to ~10 m. This needs no GCS bucket.
- **France ±5 % check**: `forestfr extract hansen --reference-ha <GFW figure>` logs the comparison.

## Spec v1.1 — 2026-11-02

[VERIFY] items checked against live services. Differences from spec v1:

- **ADMIN-EXPRESS COG CARTO**: latest edition is 4.0 (2026-01-01). Layer names are now lowercase (`region`, `departement`), and fields are renamed: `code_insee`, `nom_officiel`, `code_insee_de_la_region`. The old names `INSEE_REG`, `INSEE_DEP` and `NOM` no longer exist. The source is now the France-wide FlatGeobuf in WGS84, filtered to metropolitan France.
- **GFW DIST-ALERT API**:
  - Fields are named `umd_glad_dist_alerts__date`, `umd_glad_dist_alerts__confidence` (2/3/4) and `area__ha`.
  - The SQL table name is `results`.
  - The forest filter is available as `umd_tree_cover_density_2000__threshold` (a coded class, not a percentage).
  - Queries require an `x-api-key`.
- **DIST-ALERT tiles**: the confidence parameter is `alert_confidence=low|high`. Their tree-cover filter uses 2010 tree cover density.
- **Hansen GEE asset** `UMD/hansen/global_forest_change_2025_v1_13`: confirmed, still the latest version.
- **Hansen loss tiles**: the URL pattern is confirmed.
- **`umd_tree_cover_loss_from_fires`**: confirmed (v1.13).
- **IGN WMTS**: URL templates added.

Owner decisions (spec §15):
- Thresholds 10/30/50.
- 3 confidence levels.
- Generic admin-level naming.
- Synthetic demo data.
- Warehouse published as a GitHub Release asset.
- MIT licence.
