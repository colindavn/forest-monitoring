from datetime import date
from pathlib import Path

import pytest
from shapely.geometry import box
from typer.testing import CliRunner

from forestfr.cli import app
from forestfr.load import Warehouse


@pytest.fixture
def wh_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "wh.duckdb"
    monkeypatch.setenv("WAREHOUSE_PATH", str(path))
    return path


def seed_areas(path: Path) -> None:
    wh = Warehouse(path)
    rows = [
        ("84", 1, "FR", "Auvergne-Rhône-Alpes"),
        ("38", 2, "84", "Isère"),
        ("2A", 2, "94", "Corse-du-Sud"),
        ("94", 1, "FR", "Corse"),
    ]
    wh.upsert(
        "admin_areas",
        [
            {
                "country": "FR",
                "admin_level": level,
                "code": code,
                "parent_code": parent,
                "name": name,
                "area_km2": 8000.0,
                "geom_wkb": box(4, 45, 5, 46).wkb,
            }
            for code, level, parent, name in rows
        ],
        source_version="test",
    )
    wh.close()


def run_demo(until: str = "2026-10-31") -> None:
    result = CliRunner().invoke(app, ["demo-data", "--until", until])
    assert result.exit_code == 0, result.output


def test_demo_data_needs_boundaries_first(wh_path: Path) -> None:
    result = CliRunner().invoke(app, ["demo-data"])

    assert result.exit_code == 1
    assert "extract boundaries" in result.output


def test_every_department_gets_extent_and_loss_for_every_threshold(wh_path: Path) -> None:
    seed_areas(wh_path)
    run_demo()

    wh = Warehouse(wh_path)
    assert wh.query(
        "select code, count(*) from raw.hansen_forest_extent group by 1 order by 1"
    ) == [("2A", 3), ("38", 3)]
    assert wh.query(
        "select code, threshold, min(year), max(year), count(*) from raw.hansen_loss "
        "group by 1, 2 order by 1, 2"
    ) == [
        ("2A", 10, 2001, 2025, 25),
        ("2A", 30, 2001, 2025, 25),
        ("2A", 50, 2001, 2025, 25),
        ("38", 10, 2001, 2025, 25),
        ("38", 30, 2001, 2025, 25),
        ("38", 50, 2001, 2025, 25),
    ]


def test_values_are_physically_consistent(wh_path: Path) -> None:
    seed_areas(wh_path)
    run_demo()

    wh = Warehouse(wh_path)
    # Forest at a lower threshold always contains forest at a higher threshold.
    assert wh.query(
        "select count(*) from raw.hansen_forest_extent a join raw.hansen_forest_extent b "
        "using (code) where a.threshold < b.threshold and a.forest_2000_ha < b.forest_2000_ha"
    ) == [(0,)]
    # Cumulative loss never exceeds the forest extent.
    assert wh.query(
        "select count(*) from (select code, threshold, sum(loss_ha) as total "
        "from raw.hansen_loss group by 1, 2) l join raw.hansen_forest_extent e "
        "using (code, threshold) where l.total > e.forest_2000_ha or l.total <= 0"
    ) == [(0,)]


def test_alerts_cover_2023_to_until_with_three_confidence_levels(wh_path: Path) -> None:
    seed_areas(wh_path)
    run_demo(until="2026-10-31")

    wh = Warehouse(wh_path)
    first, last, confidences = wh.query(
        "select min(alert_date), max(alert_date), list(distinct confidence_code order by 1) "
        "from raw.dist_alerts_day"
    )[0]
    assert first >= date(2023, 1, 1)
    assert date(2026, 10, 1) <= last <= date(2026, 10, 31)
    assert confidences == [2, 3, 4]


def test_all_rows_are_flagged_synthetic(wh_path: Path) -> None:
    seed_areas(wh_path)
    run_demo()

    wh = Warehouse(wh_path)
    for table in ("hansen_forest_extent", "hansen_loss", "dist_alerts_day"):
        assert wh.query(f"select distinct _source_version from raw.{table}") == [("SYNTHETIC",)]
