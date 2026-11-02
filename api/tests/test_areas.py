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
