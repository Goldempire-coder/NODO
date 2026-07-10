from __future__ import annotations

import os

from fastapi.testclient import TestClient


def _set_env() -> None:
    os.environ["APP_ENV"] = "test"
    os.environ["APP_NAME"] = "NODO"
    os.environ["APP_VERSION"] = "0.0.0-slice-00"
    os.environ["NODO_BUILD_ID"] = "pytest-build"
    os.environ["DATABASE_URL"] = "postgresql://user:password@127.0.0.1:1/nodo"
    os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"
    os.environ["API_CORS_ORIGINS"] = "http://localhost:3000"


_set_env()

from app.main import create_app  # noqa: E402


def test_health_endpoint_returns_contract_payload() -> None:
    _set_env()
    client = TestClient(create_app())
    response = client.get("/api/v1/health", headers={"X-Request-Id": "req_health"})
    assert response.status_code == 200
    assert response.json()["request_id"] == "req_health"
    assert response.json()["data"]["status"] == "ok"


def test_health_endpoint_returns_runtime_timing_headers() -> None:
    _set_env()
    client = TestClient(create_app())
    response = client.get("/api/v1/health", headers={"X-Request-Id": "req_health_timing"})
    assert response.status_code == 200
    assert float(response.headers["X-NODO-Process-Time-Ms"]) >= 0
    assert response.headers["Server-Timing"].startswith("app;dur=")
    assert "DATABASE_URL" not in response.headers["Server-Timing"]
    assert "REDIS_URL" not in response.headers["Server-Timing"]


def test_version_endpoint_returns_build_metadata() -> None:
    _set_env()
    client = TestClient(create_app())
    response = client.get("/api/v1/version", headers={"X-Request-Id": "req_version"})
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["version"] == "0.0.0-slice-00"
    assert payload["build_id"] == "pytest-build"


def test_ready_endpoint_uses_safe_error_when_dependencies_down() -> None:
    _set_env()
    client = TestClient(create_app())
    response = client.get("/api/v1/ready", headers={"X-Request-Id": "req_ready"})
    assert response.status_code == 503
    payload = response.json()
    assert payload["request_id"] == "req_ready"
    assert payload["error"]["code"] == "UPSTREAM_UNAVAILABLE"
    assert "password" not in response.text
