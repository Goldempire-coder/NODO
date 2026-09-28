from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient


def _set_env() -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-private-cache",
        "NODO_BUILD_ID": "pytest-private-cache",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "JWT_SECRET": "test-access-secret",
        "JWT_REFRESH_SECRET": "test-refresh-secret",
        "BOT_TOKEN": "123456:test-bot-token",
        "BUSINESS_INTAKE_BOT_TOKEN": "123456:test-business-intake-bot-token",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
    }
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app
from app.modules.users.admin_passwords import hash_admin_password

PRIVATE_NO_STORE = "private, no-store"


def _authenticated_admin_client() -> tuple[TestClient, dict[str, str]]:
    client = TestClient(create_app())
    client.app.state.user_repository.create_admin_user_with_credentials(
        username="private-api-cache@nodo.local",
        password_hash=hash_admin_password("PrivateApiCache42!"),
        role="super_admin",
        first_name="Private API Cache",
    )
    login = client.post(
        "/api/v1/auth/admin/login",
        headers={"X-Request-Id": "req_private_api_login", "X-NODO-Surface": "admin_web"},
        json={"username": "private-api-cache@nodo.local", "password": "PrivateApiCache42!"},
    )
    assert login.status_code == 200, login.text
    assert login.headers.get("Cache-Control") == PRIVATE_NO_STORE
    return client, {
        "Authorization": f"Bearer {login.json()['data']['access_token']}",
        "X-NODO-Surface": "admin_web",
    }


def test_authenticated_private_success_responses_disable_caching() -> None:
    client, headers = _authenticated_admin_client()

    responses = (
        client.get("/api/v1/users/me", headers={**headers, "X-Request-Id": "req_private_users_me"}),
        client.get("/api/v1/surface/session", headers={**headers, "X-Request-Id": "req_private_surface_session"}),
        client.get("/api/v1/admin/users", headers={**headers, "X-Request-Id": "req_private_admin_users"}),
    )

    for response in responses:
        assert response.status_code == 200, response.text
        assert response.headers.get("Cache-Control") == PRIVATE_NO_STORE


def test_private_surface_errors_disable_caching() -> None:
    client = TestClient(create_app())
    private_paths = (
        "/api/v1/users/me",
        "/api/v1/surface/session",
        "/api/v1/businesses/me",
        "/api/v1/business/payment-methods",
        "/api/v1/business/credits/wallet",
        "/api/v1/business/orders",
        "/api/v1/orders/mine",
        "/api/v1/orders/00000000-0000-0000-0000-000000000001/messages",
        "/api/v1/orders/00000000-0000-0000-0000-000000000001/payment-instructions",
        "/api/v1/orders/00000000-0000-0000-0000-000000000001/receiver-details",
        "/api/v1/support/tickets",
        "/api/v1/notifications/attention-summary",
    )

    for index, path in enumerate(private_paths):
        response = client.get(path, headers={"X-Request-Id": f"req_private_error_{index}"})
        assert response.status_code == 401, f"{path}: {response.text}"
        assert response.headers.get("Cache-Control") == PRIVATE_NO_STORE, path

    missing = client.get(
        "/api/v1/users/private-route-that-does-not-exist/extra",
        headers={"X-Request-Id": "req_private_missing"},
    )
    assert missing.status_code == 404
    assert missing.headers.get("Cache-Control") == PRIVATE_NO_STORE

    intake_error = client.post(
        "/api/v1/business-intake/start",
        headers={"X-Request-Id": "req_private_intake_error"},
        json={"telegram_user_id": 1, "telegram_chat_id": 1, "telegram_update_id": 1},
    )
    assert intake_error.status_code in {403, 503}
    assert intake_error.headers.get("Cache-Control") == PRIVATE_NO_STORE

    telegram_webhook_error = client.post(
        "/api/v1/telegram/webhook/not-real-secret",
        headers={"X-Request-Id": "req_private_telegram_webhook_error"},
        json={"update_id": 1},
    )
    assert telegram_webhook_error.status_code == 403
    assert telegram_webhook_error.headers.get("Cache-Control") == PRIVATE_NO_STORE


def test_public_and_marketplace_responses_keep_their_existing_cache_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from app.core.network import ConnectivityResult
    from app.repositories.database import DatabaseRepository
    from app.repositories.redis import RedisRepository

    connectivity_calls = {"database": 0, "redis": 0}

    def database_unavailable(_repository: DatabaseRepository) -> ConnectivityResult:
        connectivity_calls["database"] += 1
        return ConnectivityResult(False, "UPSTREAM_UNAVAILABLE", "Connection failed.")

    def redis_unavailable(_repository: RedisRepository) -> ConnectivityResult:
        connectivity_calls["redis"] += 1
        return ConnectivityResult(False, "UPSTREAM_UNAVAILABLE", "Connection failed.")

    monkeypatch.setattr(DatabaseRepository, "check_connectivity", database_unavailable)
    monkeypatch.setattr(RedisRepository, "check_connectivity", redis_unavailable)
    client = TestClient(create_app())

    for path in ("/health", "/ready", "/version", "/api/v1/health", "/api/v1/ready", "/api/v1/version"):
        response = client.get(path)
        assert response.headers.get("Cache-Control") != PRIVATE_NO_STORE, path
        if path in {"/ready", "/api/v1/ready"}:
            assert response.status_code == 503
            assert response.json()["error"]["code"] == "UPSTREAM_UNAVAILABLE"

    assert connectivity_calls == {"database": 2, "redis": 2}

    for path in ("/api/v1/ads/search", "/api/v1/ads/not-a-real-ad", "/api/v1/telegram-public", "/assets/app.js"):
        response = client.get(path)
        assert response.headers.get("Cache-Control") != PRIVATE_NO_STORE, path
