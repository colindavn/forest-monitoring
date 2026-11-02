"""dbt build on the hand-made fixture warehouse (see `forestfr.fixtures` for the data)."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Any

import duckdb
import pytest

from forestfr.fixtures import ALERT_WEEKS, build_fixture_warehouse


@pytest.fixture(scope="module")
def marts(tmp_path_factory: pytest.TempPathFactory) -> Iterator[duckdb.DuckDBPyConnection]:
    path = build_fixture_warehouse(tmp_path_factory.mktemp("dbt") / "wh.duckdb")
    con = duckdb.connect(str(path), read_only=True)
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


def test_weekly_alerts_split_by_confidence_with_rolling_sum(
    marts: duckdb.DuckDBPyConnection,
) -> None:
    assert rows(
        marts,
        "select week_start, area_ha_nominal, area_ha_high, area_ha_highest, area_ha_high_conf, "
        "area_ha_all, area_ha_4w_rolling from marts.fct_alerts_week "
        "where level = 'department' and code = '38' and threshold = 30 "
        "and week_start >= '2025-01-06' order by week_start",
    ) == [
        (ALERT_WEEKS[0], 1.0, 2.0, 3.0, 5.0, 6.0, 6.0),
        (ALERT_WEEKS[1], 1.0, 2.0, 3.0, 5.0, 6.0, 12.0),
        (ALERT_WEEKS[2], 0.0, 0.0, 0.0, 0.0, 0.0, 12.0),  # week without alerts is zero-filled
        (ALERT_WEEKS[3], 1.0, 2.0, 3.0, 5.0, 6.0, 18.0),
    ]


def test_weekly_alerts_roll_up_to_region_and_france(marts: duckdb.DuckDBPyConnection) -> None:
    assert rows(
        marts,
        "select level, code, sum(area_ha_all) from marts.fct_alerts_week "
        "where threshold = 30 group by 1, 2 order by 1, 2",
    ) == [
        ("department", "01", 0.0),
        ("department", "2A", 26.0),
        ("department", "38", 18.0),
        ("france", "FR", 44.0),
        ("region", "84", 18.0),
        ("region", "94", 26.0),
    ]


def test_alert_anomaly_vs_same_iso_week_of_previous_years(
    marts: duckdb.DuckDBPyConnection,
) -> None:
    result = rows(
        marts,
        "select week_start, history_years, z_score, is_anomaly from marts.mart_alert_anomalies "
        "where level = 'department' and code = '2A' and threshold = 30 "
        "and week_start in ('2023-01-09', '2024-01-08', '2025-01-06') order by week_start",
    )
    assert result[0] == (date(2023, 1, 9), 0, None, False)
    assert result[1] == (date(2024, 1, 8), 1, None, False)  # needs >= 2 years of history
    week, years, z, anomaly = result[2]
    assert (week, years, anomaly) == (ALERT_WEEKS[0], 2, True)
    assert z == pytest.approx(17 / 2**0.5)


def test_dimensions_have_slugs_and_default_threshold_forest(
    marts: duckdb.DuckDBPyConnection,
) -> None:
    assert rows(
        marts, "select code, name, slug, forest_2000_ha from marts.dim_region order by code"
    ) == [
        ("84", "Auvergne-Rhône-Alpes", "auvergne-rhone-alpes", 1500.0),
        ("94", "Corse", "corse", 200.0),
    ]
    assert rows(
        marts,
        "select code, slug, region_code, forest_2000_ha from marts.dim_department "
        "where code = '2A'",
    ) == [("2A", "corse-du-sud", "94", 200.0)]


def test_area_kpis(marts: duckdb.DuckDBPyConnection) -> None:
    cols = (
        "level, code, name, latest_year, loss_latest_ha, loss_5y_avg_ha, loss_total_ha, "
        "trend_slope_ha_per_year, alerts_last_4w_ha, rank_in_parent"
    )
    kpis = rows(
        marts,
        f"select {cols} from marts.mart_area_kpis where threshold = 30 order by level, code",
    )
    assert [tuple(pytest.approx(v) if isinstance(v, float) else v for v in r) for r in kpis] == [
        ("department", "01", "Ain", 2003, 15.0, 20 / 3, 20.0, 5.0, 0.0, 2),
        ("department", "2A", "Corse-du-Sud", 2003, 0.0, 4 / 3, 4.0, 0.0, 20.0, 1),
        ("department", "38", "Isère", 2003, 30.0, 20.0, 60.0, 10.0, 18.0, 1),
        ("france", "FR", "France", 2003, 45.0, 28.0, 84.0, 15.0, 38.0, None),
        ("region", "84", "Auvergne-Rhône-Alpes", 2003, 45.0, 80 / 3, 80.0, 15.0, 18.0, 1),
        ("region", "94", "Corse", 2003, 0.0, 4 / 3, 4.0, 0.0, 20.0, 2),
    ]


def test_kpi_loss_percentages(marts: duckdb.DuckDBPyConnection) -> None:
    (latest_pct, total_pct) = rows(
        marts,
        "select loss_latest_pct, loss_total_pct from marts.mart_area_kpis "
        "where level = 'department' and code = '38' and threshold = 30",
    )[0]
    assert latest_pct == pytest.approx(30 / 1000)
    assert total_pct == pytest.approx(60 / 1000)


def test_loss_rates_and_rolling_metrics(marts: duckdb.DuckDBPyConnection) -> None:
    (pct, yoy, avg5) = rows(
        marts,
        "select loss_pct_of_2000, yoy_change_pct, loss_ha_5y_avg from marts.fct_loss_year "
        "where level = 'region' and code = '84' and threshold = 30 and year = 2003",
    )[0]
    assert pct == pytest.approx(45 / 1500)
    assert yoy == pytest.approx((45 - 20) / 20)
    assert avg5 == pytest.approx((15 + 20 + 45) / 3)
