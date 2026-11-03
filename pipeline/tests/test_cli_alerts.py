from pathlib import Path

import pytest
from typer.testing import CliRunner

from forestfr.cli import app


def test_extract_alerts_requires_an_api_key(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("WAREHOUSE_PATH", str(tmp_path / "wh.duckdb"))
    monkeypatch.setenv("GFW_API_KEY", "")

    result = CliRunner().invoke(app, ["extract", "alerts"])

    assert result.exit_code == 1
    assert "GFW_API_KEY" in result.output
