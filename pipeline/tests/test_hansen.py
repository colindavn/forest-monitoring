from pathlib import Path
from typing import Any

import pytest

from forestfr.hansen import parse_zonal_stats, run_hansen
from forestfr.load import Warehouse


def fc(*features: dict[str, Any]) -> dict[str, Any]:
    """Shape of `ee.FeatureCollection.getInfo()` output."""
    return {"type": "FeatureCollection", "features": [{"properties": p} for p in features]}


ISERE = {
    "code": "38",
    "forest_2000_ha": 350_000.0,
    "groups": [
        {"lossyear": 0, "sum": 349_000.0},  # 0 = no loss → ignored
        {"lossyear": 1, "sum": 120.5},
        {"lossyear": 22, "sum": 900.0},
    ],
}
CORSE_SUD = {"code": "2A", "forest_2000_ha": 200_000.0, "groups": []}


def test_parse_extracts_forest_extent_per_area() -> None:
    extent, _ = parse_zonal_stats(fc(ISERE, CORSE_SUD), threshold=30)

    assert extent == [
        {"country": "FR", "code": "38", "threshold": 30, "forest_2000_ha": 350_000.0},
        {"country": "FR", "code": "2A", "threshold": 30, "forest_2000_ha": 200_000.0},
    ]


def test_parse_maps_lossyear_codes_to_calendar_years() -> None:
    _, loss = parse_zonal_stats(fc(ISERE), threshold=30)

    assert [(r["code"], r["year"], r["loss_ha"]) for r in loss] == [
        ("38", 2001, 120.5),
        ("38", 2022, 900.0),
    ]


class FakeSource:
    version = "UMD/hansen/global_forest_change_2025_v1_13"

    def __init__(self) -> None:
        self.calls: list[int] = []

    def zonal_stats(self, threshold: int) -> dict[str, Any]:
        self.calls.append(threshold)
        scale = {10: 1.2, 30: 1.0, 50: 0.7}[threshold]
        return fc({**ISERE, "forest_2000_ha": 350_000.0 * scale})


def test_run_hansen_loads_every_threshold(tmp_path: Path) -> None:
    wh = Warehouse(tmp_path / "wh.duckdb")
    source = FakeSource()

    run_hansen(wh, source, thresholds=(10, 30, 50))

    assert source.calls == [10, 30, 50]
    assert wh.query(
        "select threshold, forest_2000_ha from raw.hansen_forest_extent order by threshold"
    ) == [(10, pytest.approx(420_000.0)), (30, 350_000.0), (50, pytest.approx(245_000.0))]
    assert wh.query("select count(*), max(_source_version) from raw.hansen_loss") == [
        (6, "UMD/hansen/global_forest_change_2025_v1_13")
    ]
