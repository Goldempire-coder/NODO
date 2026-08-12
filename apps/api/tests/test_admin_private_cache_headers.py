from __future__ import annotations

import os

from fastapi.testclient import TestClient


def _set_env() -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-admin-private-cache",
        "NODO_BUILD_ID": "pytest-admin-private-cache",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "JWT_SECRET": "test-access-secret",
        "JWT_REFRESH_SECRET": "test-refresh-secret",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
    }
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.modules.users.admin_passwords import hash_admin_password  # noqa: E402


def test_all_private_admin_surfaces_disable_response_caching() -> None:
    client = TestClient(create_app())
    client.app.state.user_repository.create_admin_user_with_credentials(
        username="private-cache@nodo.local",
        password_hash=hash_admin_password("PrivateCache42!"),
        role="super_admin",
        first_name="Private Cache Admin",
    )
    login = client.post(
        "/api/v1/auth/admin/login",
        headers={"X-Request-Id": "req_admin_private_cache_login", "X-NODO-Surface": "admin_web"},
        json={"username": "private-cache@nodo.local", "password": "PrivateCache42!"},
    )
    assert login.status_code == 200, login.text
    headers = {
        "Authorization": f"Bearer {login.json()['data']['access_token']}",
        "X-NODO-Surface": "admin_web",
    }

    paths = (
        "/api/v1/admin/users",
        "/api/v1/admin/businesses",
        "/api/v1/admin/orders",
        "/api/v1/admin/audit-logs",
        "/api/v1/admin/metrics",
        "/api/v1/admin/jobs/runs",
        "/api/v1/admin/business-intake",
        "/api/v1/admin/credit-purchases?status=pending_manual_review",
        "/api/v1/admin/staff",
        "/api/v1/admin/incident-console",
        "/api/v1/admin/ux-friction",
        "/api/v1/admin/notifications/unread-count",
        "/api/v1/admin/dashboard",
        "/api/v1/admin/disputes?status=open",
        "/api/v1/admin/support/tickets",
    )

    for index, path in enumerate(paths):
        response = client.get(path, headers={**headers, "X-Request-Id": f"req_admin_private_cache_{index}"})
        assert response.status_code == 200, f"{path}: {response.text}"
        assert response.headers.get("Cache-Control") == "private, no-store", path

    health = client.get("/health")
    assert health.status_code == 200
    assert health.headers.get("Cache-Control") != "private, no-store"


def test_admin_error_responses_disable_response_caching() -> None:
    client = TestClient(create_app())

    unauthorized = client.get(
        "/api/v1/admin/users",
        headers={"X-Request-Id": "req_admin_private_cache_unauthorized"},
    )
    assert unauthorized.status_code == 401
    assert unauthorized.headers.get("Cache-Control") == "private, no-store"

    not_found = client.get(
        "/api/v1/admin/route-that-does-not-exist",
        headers={"X-Request-Id": "req_admin_private_cache_not_found"},
    )
    assert not_found.status_code == 404
    assert not_found.headers.get("Cache-Control") == "private, no-store"
