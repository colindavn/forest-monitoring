"""Tiny hand-made warehouse used by dbt and API tests (expected values computed by hand).

Areas: régions 84 (départements 38, 01) and 94 (département 2A).
Threshold 30 forest: 38 = 1000 ha, 01 = 500 ha, 2A = 200 ha.
Loss (ha):      2001  2002  2003
    38            10    20    30
    01             5     —    15     (2002 missing → zero-filled)
    2A             —     4     —
Alerts: département 38, 4 consecutive weeks from 2025-01-06 (Mondays), 6 ha/week split
nominal 1 / high 2 / highest 3, except the 3rd week (none). Département 2A: ISO week 2 of
2023, 2024, 2025 with 2, 4, 20 ha (high) → 2025 is an anomaly.
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from shapely.geometry import box

from forestfr.config import REPO_ROOT
from forestfr.load import Warehouse

DBT_DIR = REPO_ROOT / "dbt"
FIXTURE_TODAY = "2025-02-28"
ALERT_WEEKS = [date(2025, 1, 6) + timedelta(weeks=i) for i in range(4)]
ANOMALY_HISTORY = {date(2023, 1, 9): 2.0, date(2024, 1, 8): 4.0, ALERT_WEEKS[0]: 20.0}

AREAS = [
    (1, "84", "FR", "Auvergne-Rhône-Alpes"),
    (1, "94", "FR", "Corse"),
    (2, "38", "84", "Isère"),
    (2, "01", "84", "Ain"),
    (2, "2A", "94", "Corse-du-Sud"),
]
EXTENT = {"38": 1000.0, "01": 500.0, "2A": 200.0}
LOSS = [("38", 2001, 10), ("38", 2002, 20), ("38", 2003, 30)]
LOSS += [("01", 2001, 5), ("01", 2003, 15), ("2A", 2002, 4)]


def _alert(code: str, day: date, conf: int, area: float) -> dict[str, Any]:
    return {
        "country": "FR",
        "code": code,
        "threshold": 30,
        "alert_date": day,
        "confidence_code": conf,
        "area_ha": area,
    }


def alert_rows() -> list[dict[str, Any]]:
    rows = []
    for i, monday in enumerate(ALERT_WEEKS):
        if i == 2:
            continue
        wed = monday + timedelta(days=2)
        rows += [_alert("38", monday, 2, 1.0), _alert("38", wed, 3, 2.0), _alert("38", wed, 4, 3.0)]
    rows += [_alert("2A", day, 3, area) for day, area in ANOMALY_HISTORY.items()]
    return rows


def seed(wh: Warehouse, source_version: str = "test") -> None:
    wh.upsert(
        "admin_areas",
        [
            {
                "country": "FR",
                "admin_level": lvl,
                "code": code,
                "parent_code": parent,
                "name": name,
                "area_km2": 100.0,
                "geom_wkb": box(0, 0, 1, 1).wkb,
            }
            for lvl, code, parent, name in AREAS
        ],
        source_version=source_version,
    )
    wh.upsert(
        "hansen_forest_extent",
        [
            {"country": "FR", "code": c, "threshold": 30, "forest_2000_ha": v}
            for c, v in EXTENT.items()
        ],
        source_version=source_version,
    )
    wh.upsert(
        "hansen_loss",
        [
            {"country": "FR", "code": c, "threshold": 30, "year": y, "loss_ha": float(v)}
            for c, y, v in LOSS
        ],
        source_version=source_version,
    )
    wh.upsert("dist_alerts_day", alert_rows(), source_version=source_version)


def run_dbt_build(warehouse: Path, dbt_vars: str | None = None) -> None:
    """Run `dbt build` in a subprocess (so no DuckDB handle stays open in this process)."""
    args = ["build", "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR), "--quiet"]
    if dbt_vars:
        args += ["--vars", dbt_vars]
    env = {**os.environ, "WAREHOUSE_PATH": str(warehouse)}
    code = "import sys; from dbt.cli.main import cli; sys.exit(cli())"
    proc = subprocess.run(
        [sys.executable, "-c", code, *args], env=env, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(f"dbt build failed:\n{proc.stdout}\n{proc.stderr}")


def build_fixture_warehouse(path: Path, source_version: str = "test") -> Path:
    """Seed the raw tables and build all dbt marts into `path`."""
    wh = Warehouse(path)
    seed(wh, source_version)
    wh.close()
    run_dbt_build(
        path, f"{{expected_department_count: 3, thresholds: [30], today: '{FIXTURE_TODAY}'}}"
    )
    return path
