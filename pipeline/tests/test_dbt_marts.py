"""dbt build on a tiny hand-made warehouse; expected values computed by hand.

Areas: régions 84 (départements 38, 01) and 94 (département 2A).
Threshold 30 forest: 38 = 1000 ha, 01 = 500 ha, 2A = 200 ha.
Loss (ha):      2001  2002  2003
    38            10    20    30
    01             5     —    15     (2002 missing → zero-filled)
    2A             —     4     —
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import duckdb
import pytest
from dbt.cli.main import dbtRunner
from shapely.geometry import box

from forestfr.load import Warehouse

DBT_DIR = Path(__file__).resolve().parents[2] / "dbt"


def seed(wh: Warehouse) -> None:
    areas = [
        (1, "84", "FR", "Auvergne-Rhône-Alpes"),
        (1, "94", "FR", "Corse"),
        (2, "38", "84", "Isère"),
        (2, "01", "84", "Ain"),
        (2, "2A", "94", "Corse-du-Sud"),
    ]
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
            for lvl, code, parent, name in areas
        ],
        source_version="test",
    )
    extent = {"38": 1000.0, "01": 500.0, "2A": 200.0}
    wh.upsert(
        "hansen_forest_extent",
        [
            {"country": "FR", "code": c, "threshold": 30, "forest_2000_ha": v}
            for c, v in extent.items()
        ],
        source_version="test",
    )
    loss = [("38", 2001, 10), ("38", 2002, 20), ("38", 2003, 30)]
    loss += [("01", 2001, 5), ("01", 2003, 15), ("2A", 2002, 4)]
    wh.upsert(
        "hansen_loss",
        [
            {"country": "FR", "code": c, "threshold": 30, "year": y, "loss_ha": float(v)}
            for c, y, v in loss
        ],
        source_version="test",
    )
    wh.upsert("dist_alerts_day", alert_rows(), source_version="test")


ALERT_WEEKS = [date(2025, 1, 6) + timedelta(weeks=i) for i in range(4)]  # Mondays


def alert_rows() -> list[dict[str, Any]]:
    """Département 38: on Monday + Wednesday of 4 consecutive weeks.

    Monday: nominal 1 ha; Wednesday: high 2 ha + highest 3 ha → 6 ha per week,
    except week 3 (index 2) which has no alerts.
    """
    rows = []
    for i, monday in enumerate(ALERT_WEEKS):
        if i == 2:
            continue
        wed = monday + timedelta(days=2)
        for day, conf, area in ((monday, 2, 1.0), (wed, 3, 2.0), (wed, 4, 3.0)):
            rows.append(
                {
                    "country": "FR",
                    "code": "38",
                    "threshold": 30,
                    "alert_date": day,
                    "confidence_code": conf,
                    "area_ha": area,
                }
            )
    return rows


@pytest.fixture(scope="module")
def marts(tmp_path_factory: pytest.TempPathFactory) -> Iterator[duckdb.DuckDBPyConnection]:
    path = tmp_path_factory.mktemp("dbt") / "wh.duckdb"
    wh = Warehouse(path)
    seed(wh)
    wh.close()

    os.environ["WAREHOUSE_PATH"] = str(path)
    result = dbtRunner().invoke(
        [
            "build",
            "--project-dir",
            str(DBT_DIR),
            "--profiles-dir",
            str(DBT_DIR),
            "--vars",
            "{expected_department_count: 3, today: '2025-02-28'}",
            "--quiet",
        ]
    )
    assert result.success, result.exception
    con = duckdb.connect(str(path))  # dbt-duckdb keeps a read-write handle open in-process
    yield con
    con.close()


def rows(con: duckdb.DuckDBPyConnection, sql: str) -> list[tuple[Any, ...]]:
    return con.execute(sql).fetchall()


def test_department_loss_is_zero_filled_and_cumulated(marts: duckdb.DuckDBPyConnection) -> None:
    assert rows(
        marts,
        "select year, loss_ha, cum_loss_ha from marts.fct_loss_year "
        "where level = 'department' and code = '01' and threshold = 30 order by year",
    ) == [(2001, 5.0, 5.0), (2002, 0.0, 5.0), (2003, 15.0, 20.0)]


def test_region_and_france_rows_are_sums_of_departments(
    marts: duckdb.DuckDBPyConnection,
) -> None:
    assert rows(
        marts,
        "select level, code, year, loss_ha from marts.fct_loss_year "
        "where level in ('region', 'france') and threshold = 30 order by level desc, code, year",
    ) == [
        ("region", "84", 2001, 15.0),
        ("region", "84", 2002, 20.0),
        ("region", "84", 2003, 45.0),
        ("region", "94", 2001, 0.0),
        ("region", "94", 2002, 4.0),
        ("region", "94", 2003, 0.0),
        ("france", "FR", 2001, 15.0),
        ("france", "FR", 2002, 24.0),
        ("france", "FR", 2003, 45.0),
    ]


def test_loss_rates_and_rolling_metrics(marts: duckdb.DuckDBPyConnection) -> None:
    (pct, yoy, avg5) = rows(
        marts,
        "select loss_pct_of_2000, yoy_change_pct, loss_ha_5y_avg from marts.fct_loss_year "
        "where level = 'region' and code = '84' and threshold = 30 and year = 2003",
    )[0]
    assert pct == pytest.approx(45 / 1500)
    assert yoy == pytest.approx((45 - 20) / 20)
    assert avg5 == pytest.approx((15 + 20 + 45) / 3)
