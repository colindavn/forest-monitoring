from fastapi.testclient import TestClient

from .conftest import WEB_ORIGIN


def test_meta_lists_sources_versions_and_thresholds(client: TestClient) -> None:
    body = client.get("/api/meta").json()

    assert body["thresholds"] == [10, 30, 50]
    assert body["default_threshold"] == 30
    assert body["versions"] == {"boundaries": ["test"], "hansen": ["test"], "alerts": ["test"]}
    assert body["latest_loss_year"] == 2003
    assert body["synthetic"] is False
    assert {s["id"] for s in body["sources"]} >= {"hansen", "dist_alert", "admin_express"}
    assert all(s["licence"] for s in body["sources"])


def test_responses_are_cacheable_for_one_hour(client: TestClient) -> None:
    resp = client.get("/api/health")

    assert resp.headers["cache-control"] == "public, max-age=3600"


def test_cors_allows_only_the_web_origin(client: TestClient) -> None:
    allowed = client.get("/api/health", headers={"Origin": WEB_ORIGIN})
    other = client.get("/api/health", headers={"Origin": "https://evil.example"})

    assert allowed.headers["access-control-allow-origin"] == WEB_ORIGIN
    assert "access-control-allow-origin" not in other.headers
