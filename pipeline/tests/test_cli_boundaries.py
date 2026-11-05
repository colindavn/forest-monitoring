import json
from pathlib import Path

import geopandas as gpd
import httpx
import pytest
import respx
from typer.testing import CliRunner

from forestfr.boundaries import DEPARTEMENT_URL, REGION_URL
from forestfr.cli import app
from forestfr.load import Warehouse


def fgb_bytes(gdf: gpd.GeoDataFrame, tmp_path: Path, name: str) -> bytes:
    path = tmp_path / f"{name}.fgb"
    gdf.to_file(path, driver="FlatGeobuf")
    return path.read_bytes()


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("WAREHOUSE_PATH", str(tmp_path / "wh.duckdb"))
    monkeypatch.setenv("WEB_GEO_DIR", str(tmp_path / "geo"))
    monkeypatch.setenv("DOWNLOAD_DIR", str(tmp_path / "downloads"))
    monkeypatch.delenv("GEE_PROJECT", raising=False)
    return tmp_path


@respx.mock
def test_extract_boundaries_loads_raw_and_writes_web_geojson(
    env: Path, ign_regions: gpd.GeoDataFrame, ign_departements: gpd.GeoDataFrame
) -> None:
    respx.get(REGION_URL).mock(
        return_value=httpx.Response(200, content=fgb_bytes(ign_regions, env, "r"))
    )
    respx.get(DEPARTEMENT_URL).mock(
        return_value=httpx.Response(200, content=fgb_bytes(ign_departements, env, "d"))
    )

    result = CliRunner().invoke(app, ["extract", "boundaries"])

    assert result.exit_code == 0, result.output
    wh = Warehouse(env / "wh.duckdb")
    assert wh.query("select admin_level, count(*) from raw.admin_areas group by 1 order by 1") == [
        (1, 2),
        (2, 3),
    ]
    departments = json.loads((env / "geo" / "departments.geojson").read_text(encoding="utf-8"))
    regions = json.loads((env / "geo" / "regions.geojson").read_text(encoding="utf-8"))
    assert {f["properties"]["code"] for f in departments["features"]} == {"01", "05", "38"}
    assert {f["properties"]["code"] for f in regions["features"]} == {"84", "93"}
