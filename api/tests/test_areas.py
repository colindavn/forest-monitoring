from fastapi.testclient import TestClient


def test_health_reports_data_freshness(client: TestClient) -> None:
    resp = client.get("/api/health")

    assert resp.status_code == 200
    assert resp.json() == {
        "status": "ok",
        "latest_loss_year": 2003,
        "latest_alert_date": "2025-01-29",
        "synthetic": False,
    }


def test_region_returns_kpis_parent_and_departments(client: TestClient) -> None:
    body = client.get("/api/areas/regions/84").json()

    assert (body["area"]["code"], body["area"]["loss_total_ha"]) == ("84", 80.0)
    assert body["parent"] == {"level": "france", "code": "FR", "name": "France"}
    assert [(c["code"], c["rank_in_parent"]) for c in body["children"]] == [("38", 1), ("01", 2)]


def test_department_returns_kpis_and_parent_region(client: TestClient) -> None:
    body = client.get("/api/areas/departments/2A").json()

    assert body["area"]["name"] == "Corse-du-Sud"
    assert body["area"]["alerts_last_4w_ha"] == 20.0
    assert body["parent"] == {"level": "region", "code": "94", "name": "Corse"}


def test_codes_are_strings_not_numbers(client: TestClient) -> None:
    assert client.get("/api/areas/departments/01").json()["area"]["code"] == "01"
    assert client.get("/api/areas/departments/1").status_code == 404


def test_unknown_area_is_404(client: TestClient) -> None:
    assert client.get("/api/areas/regions/99").status_code == 404
    assert client.get("/api/areas/departments/2C").status_code == 404


def test_unsupported_threshold_is_422(client: TestClient) -> None:
    assert client.get("/api/areas/france?threshold=40").status_code == 422
    assert client.get("/api/areas/france?threshold=abc").status_code == 422


def test_france_returns_kpis_and_regions(client: TestClient) -> None:
    body = client.get("/api/areas/france").json()

    assert body["area"]["code"] == "FR"
    assert body["area"]["name"] == "France"
    assert body["area"]["loss_latest_ha"] == 45.0
    assert body["area"]["forest_2000_ha"] == 1700.0
    assert [(c["code"], c["name"], c["rank_in_parent"]) for c in body["children"]] == [
        ("84", "Auvergne-Rhône-Alpes", 1),
        ("94", "Corse", 2),
    ]
