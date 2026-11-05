# Credentials setup

The app runs without credentials on **synthetic demo data** (`make demo-data`). Real numbers need two free accounts:

| What | Needed for | Where it goes |
|---|---|---|
| Google Earth Engine Cloud project | `make hansen` (yearly, run locally) | `.env` → `GEE_PROJECT` |
| GFW Data API key | `make alerts` (weekly, locally or in CI) | `.env` → `GFW_API_KEY`, GitHub secret `GFW_API_KEY` |

Copy `.env.example` to `.env` first. `.env` is gitignored, so never commit it.

## 1. Google Earth Engine (Hansen statistics)

1. Create a Google Cloud project at https://console.cloud.google.com/projectcreate (e.g. `forest-monitoring-fr`).
2. Register it for Earth Engine **non-commercial** use at https://code.earthengine.google.com/register. Choose "Unpaid usage" → "No affiliation / personal" or your research or academic category.
3. Enable the Earth Engine API for the project: https://console.cloud.google.com/apis/library/earthengine.googleapis.com
4. Authenticate locally once: `uv run earthengine authenticate`. This opens a browser and stores a token in your user profile.
5. Set `GEE_PROJECT=<your-project-id>` in `.env`.
6. Load the boundaries: `make boundaries`. Nothing is uploaded to GEE: each Hansen request carries its own département polygon, at most ~1.3 MB, well under GEE's 10 MB request limit.
7. Look up France's total tree cover loss 2001–2025 at 30 % on the GFW dashboard (https://www.globalforestwatch.org/dashboards/country/FRA/). Then compute the statistics:
   ```bash
   uv run forestfr extract hansen --reference-ha <GFW figure in ha>
   make transform
   ```
   - This computes 96 départements × 3 thresholds, one `reduceRegion` call each.
   - Expect roughly 15–45 minutes in total.
   - The log line `France total vs GFW at 30 %` must say `OK` (within ±5 %). Small differences are expected because GFW's France includes overseas départements and uses different boundaries. If it is far off, check the overseas share first.
8. Publish the warehouse so the deployed API and the weekly CI job can use it: `make publish`. This needs `gh auth login`. It refuses to publish if any synthetic rows are present.

> **Clearing demo data:** before loading real data, delete `data/warehouse.duckdb` (or run on a fresh clone). Then run `make boundaries hansen alerts transform`. Synthetic and real rows must not be mixed, and `make publish` blocks it.

### Optional: service account for CI (not needed in v1)

v1 runs Hansen locally once a year, so CI has no GEE access. If you later want CI to run `make hansen`:
1. Create a service account in the same project with the role *Earth Engine Resource Writer*.
2. Register it at https://signup.earthengine.google.com/#!/service_accounts.
3. Store its JSON key as the GitHub secret `GEE_SERVICE_ACCOUNT_JSON` and the project id as `GEE_PROJECT`.

## 2. Global Forest Watch Data API key (DIST-ALERT)

1. Create a free GFW account at https://www.globalforestwatch.org/ (sign in → *My GFW*).
2. Get a token and create an API key. See https://data-api.globalforestwatch.org/#tag/Authentication:
   ```bash
   # token
   curl -X POST https://data-api.globalforestwatch.org/auth/token \
     -d "username=<email>&password=<password>"
   # API key (alias, organisation, email, domains = [] for server-side use)
   curl -X POST https://data-api.globalforestwatch.org/auth/apikey \
     -H "Authorization: Bearer <token>" -H "Content-Type: application/json" \
     -d '{"alias":"forest-monitoring","organization":"personal","email":"<email>","domains":[]}'
   ```
3. Put the returned key in `.env` as `GFW_API_KEY=...`.
4. Run the first backfill (from 2023-01-01; 96 départements × 3 thresholds, about 10–20 min): `make alerts transform`.
5. Run `make alerts` a second time to check the incremental refresh: the row count must not grow for days already loaded.

## 3. GitHub Actions secrets

Add the secret at *Settings → Secrets and variables → Actions → New repository secret*:

| Secret | Used by | Required |
|---|---|---|
| `GFW_API_KEY` | `weekly-alerts.yml` | yes, for the weekly refresh |
| `GEE_SERVICE_ACCOUNT_JSON`, `GEE_PROJECT` | (future CI Hansen run) | no |

Without `GFW_API_KEY`, the weekly workflow exits with a notice instead of failing.

The weekly job does the following:
1. Downloads the `warehouse-latest` release asset.
2. Appends the new alerts.
3. Runs `dbt build` and the freshness checks.
4. Re-uploads the asset.

So publish a first warehouse with Hansen data (`make publish`) before enabling it.
