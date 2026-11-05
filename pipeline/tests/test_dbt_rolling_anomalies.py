"""Anomalies with a short history (< 2 years): baseline = the previous 12 weeks.

One département, alerts every Monday from 2025-09-29: 12 weeks alternating 1 ha / 3 ha
(mean 2, sample std sqrt(12/11)), then 10 ha in week 13 → z = 8 / sqrt(12/11).
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path

import duckdb
import pytest
from shapely.geometry import box

from forestfr.fixtures import run_dbt_build
from forestfr.load import Warehouse

MONDAYS = [date(2025, 9, 29) + timedelta(weeks=i) for i in range(13)]
AREAS = [1.0, 3.0] * 6 + [10.0]


def seed(path: Path) -> None:
    wh = Warehouse(path)
    for level, code, parent, name in ((1, "84", "FR", "ARA"), (2, "38", "84", "Isère")):
        wh.upsert(
            "admin_areas",
            [
                {
                    "country": "FR",
                    "admin_level": level,
                    "code": code,
                    "parent_code": parent,
                    "name": name,
                    "area_km2": 1.0,
                    "geom_wkb": box(0, 0, 1, 1).wkb,
                }
            ],
            source_version="test",
        )
    base = {"country": "FR", "code": "38", "threshold": 30}
    wh.upsert("hansen_forest_extent", [{**base, "forest_2000_ha": 100.0}], source_version="test")
    wh.upsert("hansen_loss", [{**base, "year": 2001, "loss_ha": 1.0}], source_version="test")
    wh.upsert(
        "dist_alerts_day",
        [
            {**base, "alert_date": d, "confidence_code": 3, "area_ha": a}
            for d, a in zip(MONDAYS, AREAS, strict=True)
        ],
        source_version="test",
    )
    wh.close()


@pytest.fixture(scope="module")
def marts(tmp_path_factory: pytest.TempPathFactory) -> Iterator[duckdb.DuckDBPyConnection]:
    path = tmp_path_factory.mktemp("rolling") / "wh.duckdb"
    seed(path)
    run_dbt_build(path, "{expected_department_count: 1, thresholds: [30], today: '2026-01-31'}")
    con = duckdb.connect(str(path), read_only=True)
    yield con
    con.close()


def anomaly(con: duckdb.DuckDBPyConnection, week: date) -> tuple[object, ...]:
    return con.execute(
        "select baseline_method, z_score, is_anomaly from marts.mart_alert_anomalies "
        "where level = 'department' and code = '38' and threshold = 30 and week_start = ?",
        [week],
    ).fetchall()[0]


def test_week_after_12_weeks_of_history_uses_rolling_baseline(
    marts: duckdb.DuckDBPyConnection,
) -> None:
    method, z, is_anomaly = anomaly(marts, MONDAYS[12])

    assert method == "rolling_12w"
    assert z == pytest.approx(8 / (12 / 11) ** 0.5)
    assert is_anomaly is True


def test_no_score_before_12_weeks_of_history(marts: duckdb.DuckDBPyConnection) -> None:
    assert anomaly(marts, MONDAYS[11]) == (None, None, False)
