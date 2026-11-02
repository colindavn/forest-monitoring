import pytest
from fastapi.testclient import TestClient


def test_choropleth_loss_by_department_for_a_year(client: TestClient) -> None:
    body = client.get("/api/choropleth?level=department&metric=loss_ha&year=2002").json()

    assert body == {
        "level": "department",
        "metric": "loss_ha",
        "year": 2002,
        "threshold": 30,
        "values": {"01": 0.0, "2A": 4.0, "38": 20.0},
    }


def test_choropleth_defaults_to_latest_year(client: TestClient) -> None:
    body = client.get("/api/choropleth?level=region&metric=loss_pct_of_2000").json()

    assert body["year"] == 2003
    assert body["values"] == {"84": pytest.approx(45 / 1500), "94": 0.0}


def test_choropleth_kpi_metrics(client: TestClient) -> None:
    alerts = client.get("/api/choropleth?level=region&metric=alerts_ha_last_4w").json()
    trend = client.get("/api/choropleth?level=region&metric=trend_slope").json()

    assert alerts["values"] == {"84": 18.0, "94": 20.0}
    assert trend["values"] == {"84": pytest.approx(15.0), "94": pytest.approx(0.0)}


def test_choropleth_validation(client: TestClient) -> None:
    assert client.get("/api/choropleth?level=france&metric=loss_ha").status_code == 422
    assert client.get("/api/choropleth?level=region&metric=volume").status_code == 422


def test_rankings_within_parent(client: TestClient) -> None:
    body = client.get("/api/rankings?level=department&metric=loss_ha&parent=84").json()

    assert [(i["rank"], i["code"], i["name"], i["value"]) for i in body["items"]] == [
        (1, "38", "Isère", 30.0),
        (2, "01", "Ain", 15.0),
    ]


def test_rankings_limit(client: TestClient) -> None:
    body = client.get("/api/rankings?level=department&metric=alerts_ha_last_4w&limit=1").json()

    assert [(i["code"], i["value"]) for i in body["items"]] == [("2A", 20.0)]
