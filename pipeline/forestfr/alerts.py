"""DIST-ALERT per département from the GFW Data API → raw.dist_alerts_day (incremental)."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Iterable
from datetime import date, timedelta
from typing import Any

import httpx
from shapely import wkb
from shapely.geometry import box, mapping
from shapely.geometry.base import BaseGeometry

from forestfr.load import Warehouse

log = logging.getLogger(__name__)

API = "https://data-api.globalforestwatch.org"
DATASET = "umd_glad_dist_alerts"
COUNTRY = "FR"
BACKFILL_START = date(2023, 1, 1)
REVISION_WINDOW = timedelta(days=30)  # alerts get confirmed / revised after first detection
QUERY_TOLERANCE_DEG = 0.001  # ~100 m simplification for API geometries
# GFW codes tree cover density 2000 thresholds as classes (SPEC §3.3).
THRESHOLD_CLASS = {10: 1, 15: 2, 20: 3, 25: 4, 30: 5, 50: 6, 75: 7}
CONFIDENCE_CODE = {"nominal": 2, "high": 3, "highest": 4}
RETRY_STATUS = {429, 500, 502, 503, 504}
TOO_LARGE_STATUS = {413}


class GeometryTooLargeError(RuntimeError):
    pass


def build_sql(since: date, threshold: int) -> str:
    return (
        "SELECT umd_glad_dist_alerts__date, umd_glad_dist_alerts__confidence, "
        "SUM(area__ha) AS area__ha FROM results "
        f"WHERE umd_glad_dist_alerts__date >= '{since.isoformat()}' "
        f"AND umd_tree_cover_density_2000__threshold >= {THRESHOLD_CLASS[threshold]} "
        "GROUP BY umd_glad_dist_alerts__date, umd_glad_dist_alerts__confidence"
    )


def confidence_code(value: Any) -> int:
    return CONFIDENCE_CODE[value] if isinstance(value, str) else int(value)


class GfwClient:
    """Minimal GFW Data API client: sequential calls, retries with exponential backoff."""

    def __init__(
        self,
        api_key: str,
        pause_s: float = 1.0,
        backoff_s: float = 2.0,
        max_retries: int = 5,
        timeout_s: float = 120.0,
    ) -> None:
        self._http = httpx.Client(base_url=API, headers={"x-api-key": api_key}, timeout=timeout_s)
        self.pause_s = pause_s
        self.backoff_s = backoff_s
        self.max_retries = max_retries

    def latest_version(self) -> str:
        resp = self._http.get(f"/dataset/{DATASET}/latest", follow_redirects=False)
        if resp.status_code in (301, 302, 307, 308):
            return resp.headers["location"].rstrip("/").rsplit("/", 1)[-1]
        resp.raise_for_status()
        return str(resp.json()["data"]["version"])

    def query(self, version: str, sql: str, geometry: dict[str, Any]) -> list[dict[str, Any]]:
        url = f"/dataset/{DATASET}/{version}/query/json"
        for attempt in range(self.max_retries + 1):
            resp = self._http.post(url, json={"sql": sql, "geometry": geometry})
            if resp.status_code in TOO_LARGE_STATUS:
                raise GeometryTooLargeError(resp.text)
            if resp.status_code in RETRY_STATUS and attempt < self.max_retries:
                time.sleep(self.backoff_s * 2**attempt)
                continue
            resp.raise_for_status()
            data: list[dict[str, Any]] = resp.json()["data"]
            return data
        raise RuntimeError("unreachable")

    def pause(self) -> None:
        time.sleep(self.pause_s)


def grid_cells(geom: BaseGeometry, n: int = 2) -> list[BaseGeometry]:
    """Split a geometry into an n x n grid of non-empty parts."""
    minx, miny, maxx, maxy = geom.bounds
    dx, dy = (maxx - minx) / n, (maxy - miny) / n
    boxes = [
        box(minx + i * dx, miny + j * dy, minx + (i + 1) * dx, miny + (j + 1) * dy)
        for i in range(n)
        for j in range(n)
    ]
    cells = [geom.intersection(b) for b in boxes]
    return [c for c in cells if not c.is_empty]


def query_area(
    client: GfwClient, version: str, sql: str, geom: BaseGeometry, depth: int = 0
) -> dict[tuple[date, int], float]:
    """Alert area by (date, confidence code); splits the geometry if the API rejects it."""
    try:
        rows = client.query(version, sql, mapping(geom))
    except GeometryTooLargeError:
        if depth >= 3:
            raise
        log.info("Geometry too large, splitting into a 2x2 grid (depth %d)", depth + 1)
        totals: dict[tuple[date, int], float] = defaultdict(float)
        for cell in grid_cells(geom):
            for key, area in query_area(client, version, sql, cell, depth + 1).items():
                totals[key] += area
        return totals
    out: dict[tuple[date, int], float] = defaultdict(float)
    for r in rows:
        day = date.fromisoformat(str(r["umd_glad_dist_alerts__date"])[:10])
        out[(day, confidence_code(r["umd_glad_dist_alerts__confidence"]))] += float(r["area__ha"])
    return out


def since_for(wh: Warehouse, threshold: int) -> date:
    latest = wh.query(
        "select max(alert_date) from raw.dist_alerts_day "
        "where country = ? and threshold = ? and _source_version <> 'SYNTHETIC'",
        [COUNTRY, threshold],
    )[0][0]
    return max(BACKFILL_START, latest - REVISION_WINDOW) if latest else BACKFILL_START


def run_alerts(
    wh: Warehouse, client: GfwClient, thresholds: Iterable[int], today: date | None = None
) -> int:
    """Incremental extract for every département and threshold. Returns rows loaded."""
    today = today or date.today()
    version = client.latest_version()
    departments = wh.query(
        "select code, geom_wkb from raw.admin_areas where country = ? and admin_level = 2 "
        "order by code",
        [COUNTRY],
    )
    total = 0
    for threshold in thresholds:
        since = since_for(wh, threshold)
        sql = build_sql(since, threshold)
        log.info("DIST-ALERT %s threshold %s since %s", version, threshold, since)
        for code, geom_wkb in departments:
            geom = wkb.loads(bytes(geom_wkb)).simplify(QUERY_TOLERANCE_DEG)
            areas = query_area(client, version, sql, geom)
            rows = [
                {
                    "country": COUNTRY,
                    "code": code,
                    "threshold": threshold,
                    "alert_date": day,
                    "confidence_code": conf,
                    "area_ha": area,
                }
                for (day, conf), area in sorted(areas.items())
                if day <= today
            ]
            total += wh.upsert("dist_alerts_day", rows, source_version=version)
            client.pause()
    return total
