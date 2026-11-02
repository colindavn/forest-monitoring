from datetime import date
from pathlib import Path

import pytest
from typer.testing import CliRunner

from forestfr.cli import app
from forestfr.load import Warehouse


@pytest.fixture
def wh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Warehouse:
    path = tmp_path / "wh.duckdb"
    monkeypatch.setenv("WAREHOUSE_PATH", str(path))
    return Warehouse(path)


def load_alert(wh: Warehouse, code: str, version: str) -> None:
    row = {
        "country": "FR",
        "code": code,
        "threshold": 30,
        "alert_date": date(2026, 10, 1),
        "confidence_code": 3,
        "area_ha": 1.0,
    }
    wh.upsert("dist_alerts_day", [row], source_version=version)


def test_release_check_fails_when_synthetic_rows_exist(wh: Warehouse) -> None:
    load_alert(wh, "38", "v20261031")
    load_alert(wh, "01", "SYNTHETIC")
    wh.close()

    result = CliRunner().invoke(app, ["check-release"])

    assert result.exit_code == 1
    assert "raw.dist_alerts_day: 1 SYNTHETIC rows" in result.output


def test_release_check_passes_on_real_data(wh: Warehouse) -> None:
    load_alert(wh, "38", "v20261031")
    wh.close()

    result = CliRunner().invoke(app, ["check-release"])

    assert result.exit_code == 0, result.output
