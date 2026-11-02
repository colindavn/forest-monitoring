from fastapi.testclient import TestClient


def test_loss_series_for_a_region(client: TestClient) -> None:
    body = client.get("/api/loss?level=region&code=84").json()

    assert (body["level"], body["code"], body["threshold"]) == ("region", "84", 30)
    assert [(p["year"], p["loss_ha"], p["cum_loss_ha"]) for p in body["series"]] == [
        (2001, 15.0, 15.0),
        (2002, 20.0, 35.0),
        (2003, 45.0, 80.0),
    ]


def test_loss_series_year_range(client: TestClient) -> None:
    body = client.get("/api/loss?level=department&code=38&from=2002&to=2002").json()

    assert [p["year"] for p in body["series"]] == [2002]


def test_series_validation(client: TestClient) -> None:
    assert client.get("/api/loss?level=commune&code=38").status_code == 422
    assert client.get("/api/loss?level=department&code=99").status_code == 404
    assert client.get("/api/alerts?level=department&code=38&confidence=low").status_code == 422


def test_alert_series_with_anomaly_flags(client: TestClient) -> None:
    body = client.get("/api/alerts?level=department&code=2A&from=2025-01-01").json()

    first = body["series"][0]
    assert first["week_start"] == "2025-01-06"
    assert (first["area_ha_high"], first["area_ha_all"], first["is_anomaly"]) == (20.0, 20.0, True)
    assert [p["week_start"] for p in body["series"]] == [
        "2025-01-06",
        "2025-01-13",
        "2025-01-20",
        "2025-01-27",
    ]


def test_alert_series_confidence_selects_area(client: TestClient) -> None:
    week = "from=2025-01-06&to=2025-01-06"
    all_conf = client.get(f"/api/alerts?level=department&code=38&{week}").json()
    high = client.get(f"/api/alerts?level=department&code=38&{week}&confidence=high").json()

    assert all_conf["series"][0]["area_ha"] == 6.0  # nominal 1 + high 2 + highest 3
    assert high["series"][0]["area_ha"] == 5.0  # high + highest
