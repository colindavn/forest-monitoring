from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from forestfr.fixtures import build_fixture_warehouse

WEB_ORIGIN = "http://localhost:5173"


@pytest.fixture(scope="session")
def fixture_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_fixture_warehouse(tmp_path_factory.mktemp("api") / "wh.duckdb")


@pytest.fixture(scope="session")
def client(fixture_db: Path) -> TestClient:
    return TestClient(create_app(fixture_db, web_origin=WEB_ORIGIN))
