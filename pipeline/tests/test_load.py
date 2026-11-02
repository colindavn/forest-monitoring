from pathlib import Path

import pytest

from forestfr.load import Warehouse


@pytest.fixture
def wh(tmp_path: Path) -> Warehouse:
    return Warehouse(tmp_path / "wh.duckdb")


def loss_row(code: str, year: int, loss_ha: float) -> dict[str, object]:
    return {"country": "FR", "code": code, "threshold": 30, "year": year, "loss_ha": loss_ha}


def test_upsert_twice_replaces_rows_with_same_keys(wh: Warehouse) -> None:
    wh.upsert("hansen_loss", [loss_row("38", 2020, 10.0)], source_version="v1")
    wh.upsert("hansen_loss", [loss_row("38", 2020, 12.5)], source_version="v2")

    rows = wh.query("select code, year, loss_ha, _source_version from raw.hansen_loss")
    assert rows == [("38", 2020, 12.5, "v2")]


def test_upsert_keeps_rows_with_other_keys(wh: Warehouse) -> None:
    wh.upsert("hansen_loss", [loss_row("38", 2020, 10.0)], source_version="v1")
    wh.upsert("hansen_loss", [loss_row("2A", 2020, 3.0)], source_version="v1")

    rows = wh.query("select code from raw.hansen_loss order by code")
    assert rows == [("2A",), ("38",)]


def test_codes_stay_strings(wh: Warehouse) -> None:
    wh.upsert("hansen_loss", [loss_row("01", 2001, 1.0)], source_version="v1")

    assert wh.query("select code from raw.hansen_loss") == [("01",)]


def test_rows_get_a_load_timestamp(wh: Warehouse) -> None:
    wh.upsert("hansen_loss", [loss_row("38", 2020, 10.0)], source_version="v1")

    assert wh.query("select count(*) from raw.hansen_loss where _loaded_at is not null") == [(1,)]


def test_unknown_table_is_rejected(wh: Warehouse) -> None:
    with pytest.raises(KeyError):
        wh.upsert("nope", [], source_version="v1")
