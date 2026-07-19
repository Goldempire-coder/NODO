from __future__ import annotations

import json
import os

from fastapi.testclient import TestClient

from app.auth.jwt import decode_access_token


JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-admin-auth",
        "NODO_BUILD_ID": "pytest-admin-auth-build",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": "123456:test-bot-token",
        "JWT_SECRET": JWT_SECRET,
        "JWT_REFRESH_SECRET": JWT_REFRESH_SECRET,
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.modules.users.admin_passwords import hash_admin_password  # noqa: E402


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    return TestClient(create_app())


def _seed_admin(client: TestClient, *, username: str = "owner@nodo.local", password: str = "CorrectHorse42!", role: str = "super_admin"):
    return client.app.state.user_repository.create_admin_user_with_credentials(
        username=username,
        password_hash=hash_admin_password(password),
        role=role,
        first_name="NODO Admin",
    )


def _login_admin(client: TestClient, *, username: str = "owner@nodo.local", password: str = "CorrectHorse42!"):
    return client.post(
        "/api/v1/auth/admin/login",
        headers={"X-Request-Id": "req_admin_login", "X-NODO-Surface": "admin_web"},
        json={"username": username, "password": password},
    )


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_admin_credentials_login_returns_existing_admin_session_without_telegram() -> None:
    client = _client()
    admin = _seed_admin(client)

    response = _login_admin(client, username=" OWNER@NODO.LOCAL ", password="CorrectHorse42!")

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "Bearer"
    assert data["user"]["id"] == admin.id
    assert data["user"]["role"] == "super_admin"
    assert "telegram_id" not in data["user"]
    claims = decode_access_token(data["access_token"], JWT_SECRET)
    assert claims["sub"] == admin.id
    assert claims["role"] == "super_admin"
    assert "admin_login" in _event_types(client)


def test_admin_credentials_login_does_not_require_telegram_bot_token() -> None:
    client = _client(BOT_TOKEN="")
    admin = _seed_admin(client)

    response = _login_admin(client)

    assert response.status_code == 200, response.text
    assert response.json()["data"]["user"]["id"] == admin.id


def test_admin_credentials_login_rejects_wrong_password_without_storing_plain_secret() -> None:
    client = _client()
    _seed_admin(client, password="CorrectHorse42!")

    response = _login_admin(client, password="WrongHorse42!")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "ADMIN_LOGIN_INVALID"
    assert "admin_login_failed" in _event_types(client)
    repository_text = json.dumps(
        {
            "users": [user.__dict__ for user in client.app.state.user_repository._users_by_id.values()],
            "credentials": [credential.__dict__ for credential in client.app.state.user_repository._admin_credentials_by_id.values()],
            "sessions": [session.__dict__ for session in client.app.state.user_repository._sessions_by_id.values()],
        },
        default=str,
    )
    assert "CorrectHorse42!" not in repository_text
    assert "WrongHorse42!" not in repository_text
    assert client.app.state.user_repository._sessions_by_id == {}


def test_admin_credentials_login_rejects_non_admin_roles() -> None:
    client = _client()
    _seed_admin(client, username="support@nodo.local", role="support")
    _seed_admin(client, username="client@nodo.local", role="remitter")

    support_response = _login_admin(client, username="support@nodo.local")
    remitter_response = _login_admin(client, username="client@nodo.local")

    assert support_response.status_code == 200
    assert support_response.json()["data"]["user"]["role"] == "support"
    assert remitter_response.status_code == 401
    assert remitter_response.json()["error"]["code"] == "ADMIN_LOGIN_INVALID"


def test_admin_credentials_login_locks_after_repeated_failures() -> None:
    client = _client()
    _seed_admin(client, password="CorrectHorse42!")

    for _ in range(5):
        assert _login_admin(client, password="bad-password").status_code == 401
    locked = _login_admin(client, password="CorrectHorse42!")

    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "RATE_LIMITED"
