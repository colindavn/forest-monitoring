import json
from datetime import date
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from shapely.geometry import box

from forestfr.alerts import API, DATASET, GfwClient, NoDepartmentsError, run_alerts
from forestfr.load import Warehouse

VERSION = "v20261031"
QUERY_URL = f"{API}/dataset/{DATASET}/{VERSION}/query/json"


@pytest.fixture
def wh(tmp_path: Path) -> Warehouse:
    wh = Warehouse(tmp_path / "wh.duckdb")
    wh.upsert(
        "admin_areas",
        [
            {
                "country": "FR",
                "admin_level": 2,
                "code": code,
                "parent_code": "84",
                "name": name,
                "area_km2": 1.0,
                "geom_wkb": box(4, 45, 5, 46).wkb,
            }
            for code, name in (("38", "Isère"), ("01", "Ain"))
        ],
        source_version="test",
    )
    return wh


def api_rows(*rows: tuple[str, int | str, float]) -> dict[str, Any]:
    """Shape of the live API response; confidence comes back as "nominal" / "high"."""
    return {
        "status": "success",
        "data": [
            {
                "umd_glad_dist_alerts__date": d,
                "umd_glad_dist_alerts__confidence": c,
                "area__ha": a,
            }
            for d, c, a in rows
        ],
    }


def mock_version() -> None:
    respx.get(f"{API}/dataset/{DATASET}/latest").mock(
        return_value=httpx.Response(307, headers={"location": f"/dataset/{DATASET}/{VERSION}"})
    )


def client() -> GfwClient:
    return GfwClient(api_key="secret", pause_s=0, backoff_s=0)


@respx.mock
def test_first_run_backfills_from_2023_with_forest_filter(wh: Warehouse) -> None:
    mock_version()
    route = respx.post(QUERY_URL).mock(
        return_value=httpx.Response(200, json=api_rows(("2026-10-01", "high", 1.5)))
    )

    run_alerts(wh, client(), thresholds=(30,), today=date(2026, 11, 2))

    first = route.calls[0].request
    body = json.loads(first.content)
    assert first.headers["x-api-key"] == "secret"
    assert "umd_glad_dist_alerts__date >= '2023-01-01'" in body["sql"]
    # The API takes the threshold in percent (it rejects the class code 5 with a 500).
    assert "umd_tree_cover_density_2000__threshold >= 30" in body["sql"]
    assert body["geometry"]["type"] in {"Polygon", "MultiPolygon"}
    assert route.call_count == 2  # one per département
    assert wh.query(
        "select code, threshold, alert_date, confidence_code, area_ha, _source_version "
        "from raw.dist_alerts_day order by code"
    ) == [
        ("01", 30, date(2026, 10, 1), 3, 1.5, VERSION),
        ("38", 30, date(2026, 10, 1), 3, 1.5, VERSION),
    ]


@respx.mock
def test_incremental_run_starts_30_days_before_latest_and_does_not_duplicate(
    wh: Warehouse,
) -> None:
    mock_version()
    route = respx.post(QUERY_URL).mock(
        return_value=httpx.Response(
            200, json=api_rows(("2026-10-01", 3, 1.5), ("2026-10-02", 2, 1))
        )
    )

    run_alerts(wh, client(), thresholds=(30,), today=date(2026, 11, 2))
    run_alerts(wh, client(), thresholds=(30,), today=date(2026, 11, 2))

    second_sql = json.loads(route.calls[-1].request.content)["sql"]
    assert "umd_glad_dist_alerts__date >= '2026-09-02'" in second_sql  # 2026-10-02 - 30 days
    assert wh.query("select count(*) from raw.dist_alerts_day") == [(4,)]


@respx.mock
def test_refuses_to_run_without_departments(tmp_path: Path) -> None:
    mock_version()
    empty = Warehouse(tmp_path / "empty.duckdb")

    with pytest.raises(NoDepartmentsError, match="extract boundaries"):
        run_alerts(empty, client(), thresholds=(30,), today=date(2026, 11, 2))


@respx.mock
def test_retries_rate_limited_requests(wh: Warehouse) -> None:
    mock_version()
    route = respx.post(QUERY_URL).mock(
        side_effect=[
            httpx.Response(429),
            httpx.Response(503),
            httpx.Response(200, json=api_rows(("2026-10-01", 4, 2.0))),
            httpx.Response(200, json=api_rows()),
        ]
    )

    run_alerts(wh, client(), thresholds=(30,), today=date(2026, 11, 2))

    assert route.call_count == 4
    assert wh.query("select confidence_code, area_ha from raw.dist_alerts_day") == [(4, 2.0)]


@respx.mock
def test_splits_geometry_on_a_grid_when_too_large(wh: Warehouse) -> None:
    mock_version()
    responses = [httpx.Response(413)] + [
        httpx.Response(200, json=api_rows(("2026-10-01", 3, 1.0))) for _ in range(4)
    ]
    responses += [httpx.Response(200, json=api_rows())]
    respx.post(QUERY_URL).mock(side_effect=responses)

    run_alerts(wh, client(), thresholds=(30,), today=date(2026, 11, 2))

    # 4 grid cells x 1 ha, summed for the same day and confidence.
    assert wh.query("select code, area_ha from raw.dist_alerts_day") == [("01", 4.0)]
