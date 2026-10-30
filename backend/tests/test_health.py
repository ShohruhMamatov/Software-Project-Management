from app.config import settings


def test_health_is_ok(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_openapi_lists_every_router(client):
    paths = client.get("/openapi.json").json()["paths"]

    assert {"/health", "/auth/login", "/stores/me", "/cameras", "/events", "/agent/config"} <= set(paths)


def test_cors_preflight_allows_configured_origin(client):
    origin = settings.cors_origins.split(",")[0].strip()

    response = client.options(
        "/health", headers={"Origin": origin, "Access-Control-Request-Method": "GET"}
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_cors_preflight_rejects_unknown_origin(client):
    response = client.options(
        "/health", headers={"Origin": "http://evil.test", "Access-Control-Request-Method": "GET"}
    )

    assert "access-control-allow-origin" not in response.headers
