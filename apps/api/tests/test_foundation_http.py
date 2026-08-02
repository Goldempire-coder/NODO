from __future__ import annotations

import os

from fastapi.testclient import TestClient


def _set_env() -> None:
    os.environ.pop("RAILWAY_GIT_COMMIT_SHA", None)
    os.environ.pop("RAILWAY_DEPLOYMENT_ID", None)
    os.environ["APP_ENV"] = "test"
    os.environ["APP_NAME"] = "NODO"
    os.environ["APP_VERSION"] = "0.0.0-slice-00"
    os.environ["NODO_BUILD_ID"] = "pytest-build"
    os.environ["DATABASE_URL"] = "postgresql://user:password@127.0.0.1:1/nodo"
    os.environ["REDIS_URL"] = "redis://127.0.0.1:1/0"
    os.environ["API_CORS_ORIGINS"] = "http://localhost:3000"


_set_env()

from app.core.config import load_settings  # noqa: E402
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


def test_railway_git_sha_is_authoritative_for_version_and_health_aliases() -> None:
    _set_env()
    commit_sha = "a" * 40
    os.environ["RAILWAY_GIT_COMMIT_SHA"] = commit_sha
    try:
        client = TestClient(create_app())

        for path in ("/version", "/api/v1/version"):
            response = client.get(path, headers={"X-Request-Id": "req_railway_version"})
            assert response.status_code == 200
            assert response.json()["data"]["version"] == "test-aaaaaaa"
            assert response.json()["data"]["build_id"] == commit_sha

        for path in ("/health", "/api/v1/health"):
            response = client.get(path, headers={"X-Request-Id": "req_railway_health"})
            assert response.status_code == 200
            assert response.json()["data"]["version"] == "test-aaaaaaa"
            assert response.json()["data"]["build_id"] == commit_sha
    finally:
        os.environ.pop("RAILWAY_GIT_COMMIT_SHA", None)


def test_local_version_metadata_has_clear_fallback_without_sha_or_labels() -> None:
    settings = load_settings(
        {
            "APP_ENV": "local",
            "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
            "REDIS_URL": "redis://127.0.0.1:1/0",
        }
    )

    assert settings.app_version == "local"
    assert settings.build_id == "local"


def test_invalid_railway_git_sha_does_not_override_explicit_fallback_labels() -> None:
    settings = load_settings(
        {
            "APP_ENV": "staging",
            "APP_VERSION": "staging-manual",
            "NODO_BUILD_ID": "manual-build",
            "RAILWAY_GIT_COMMIT_SHA": "not-a-commit-sha",
            "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
            "REDIS_URL": "redis://127.0.0.1:1/0",
        }
    )

    assert settings.app_version == "staging-manual"
    assert settings.build_id == "manual-build"


def test_railway_deployment_without_git_sha_does_not_reuse_stale_manual_labels() -> None:
    settings = load_settings(
        {
            "APP_ENV": "staging",
            "APP_VERSION": "staging-stale",
            "NODO_BUILD_ID": "stale-build",
            "RAILWAY_DEPLOYMENT_ID": "deployment-id",
            "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
            "REDIS_URL": "redis://127.0.0.1:1/0",
        }
    )

    assert settings.app_version == "staging-unknown"
    assert settings.build_id == "unknown"


def test_cors_allows_browser_write_methods_used_by_mini_apps() -> None:
    _set_env()
    client = TestClient(create_app())

    for method in ["PATCH", "DELETE"]:
        response = client.options(
            "/api/v1/business/payment-methods/00000000-0000-0000-0000-000000000000",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": method,
                "Access-Control-Request-Headers": "authorization,x-request-id",
            },
        )

        assert response.status_code == 200
        assert method in response.headers["access-control-allow-methods"]


def test_ready_endpoint_uses_safe_error_when_dependencies_down() -> None:
    _set_env()
    client = TestClient(create_app())
    response = client.get("/api/v1/ready", headers={"X-Request-Id": "req_ready"})
    assert response.status_code == 503
    payload = response.json()
    assert payload["request_id"] == "req_ready"
    assert payload["error"]["code"] == "UPSTREAM_UNAVAILABLE"
    assert "password" not in response.text
