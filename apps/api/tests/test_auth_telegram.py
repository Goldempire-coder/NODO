from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.auth.jwt import decode_access_token, hash_refresh_token
from app.modules.users.models import utc_now


BOT_TOKEN = "123456:test-bot-token"
BUSINESS_INTAKE_BOT_TOKEN = "123456:test-business-intake-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-01",
        "NODO_BUILD_ID": "pytest-auth-build",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "BUSINESS_INTAKE_BOT_TOKEN": BUSINESS_INTAKE_BOT_TOKEN,
        "JWT_SECRET": JWT_SECRET,
        "JWT_REFRESH_SECRET": JWT_REFRESH_SECRET,
        "AUTH_INIT_DATA_MAX_AGE_SECONDS": "86400",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "2592000",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    return TestClient(create_app())


def _signed_init_data(
    *,
    telegram_id: int = 101,
    username: str | None = "remitter_one",
    first_name: str | None = "Remitter",
    last_name: str | None = "One",
    auth_date: int | None = None,
    bot_token: str = BOT_TOKEN,
) -> str:
    user = {
        "id": telegram_id,
        "username": username,
        "first_name": first_name,
        "last_name": last_name,
    }
    payload = {
        "auth_date": str(auth_date or int(time.time())),
        "user": json.dumps(user, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def _login(client: TestClient, init_data: str | None = None):
    return client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": "req_login"},
        json={"init_data": init_data or _signed_init_data()},
    )


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_valid_init_data_authenticates_new_user_without_public_telegram_id() -> None:
    client = _client()
    response = _login(client)

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["token_type"] == "Bearer"
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["user"]["role"] == "remitter"
    assert data["user"]["status"] == "active"
    assert "telegram_id" not in data["user"]
    assert _event_types(client) == ["user_created", "user_login"]

    session = next(iter(client.app.state.user_repository._sessions_by_id.values()))
    assert session.refresh_token_hash != data["refresh_token"]
    assert len(session.refresh_token_hash) == 64


def test_user_accepts_terms_once_and_profile_persists_acceptance() -> None:
    client = _client()
    login = _login(client).json()["data"]

    accept_response = client.post(
        "/api/v1/users/me/terms-acceptance",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_terms_accept"},
        json={"terms_version": "2026-07-06"},
    )
    profile_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_terms_me"},
    )

    assert accept_response.status_code == 200
    accepted = accept_response.json()["data"]
    assert accepted["terms_accepted_at"]
    assert accepted["terms_version"] == "2026-07-06"
    assert profile_response.json()["data"]["terms_accepted_at"] == accepted["terms_accepted_at"]
    assert "terms_accepted" in _event_types(client)

    profile_update = client.post(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_profile_update"},
        json={"first_name": "Carlos Cliente", "phone": "+58 412 123 4567"},
    )
    assert profile_update.status_code == 200
    profile_data = profile_update.json()["data"]
    assert profile_data["first_name"] == "Carlos Cliente"
    assert profile_data["phone"] == "+58 412 123 4567"
    assert "client_profile_completed" in _event_types(client)

    bad_profile = client.post(
        "/api/v1/users/me/profile",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_bad_profile"},
        json={"first_name": "<x>", "phone": "<script>"},
    )
    assert bad_profile.status_code == 422


def test_invalid_hash_rejects_and_audits_auth_failed() -> None:
    client = _client()
    init_data = _signed_init_data().replace("hash=", "hash=bad")
    response = _login(client, init_data)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TELEGRAM_INIT_DATA_INVALID"
    assert _event_types(client) == ["auth_failed"]
    metadata = client.app.state.audit_writer.events[-1].metadata_json
    assert metadata["reason"] == "telegram_init_data_rejected"
    assert metadata["last_error_code"] == "TELEGRAM_INIT_DATA_INVALID"
    assert metadata["token_attempts"] == 1
    assert metadata["init_data"]["has_hash"] is True
    assert metadata["init_data"]["has_user"] is True
    assert metadata["init_data"]["has_auth_date"] is True
    assert metadata["init_data"]["telegram_user_id"] == 101
    assert "user" in metadata["init_data"]["keys"]
    assert init_data not in json.dumps(metadata)
    assert BOT_TOKEN not in json.dumps(metadata)


def test_business_surface_accepts_business_intake_bot_signed_init_data() -> None:
    client = _client()
    init_data = _signed_init_data(telegram_id=202, username="approved_business", bot_token=BUSINESS_INTAKE_BOT_TOKEN)

    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": "req_business_bot_login", "X-NODO-Surface": "business_mini_app"},
        json={"init_data": init_data},
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["user"]["username"] == "approved_business"


def test_business_surface_accepts_text_plain_auth_without_preflight_headers() -> None:
    client = _client()
    init_data = _signed_init_data(telegram_id=204, username="business_text_plain", bot_token=BUSINESS_INTAKE_BOT_TOKEN)

    response = client.post(
        "/api/v1/auth/telegram",
        headers={"Content-Type": "text/plain;charset=UTF-8"},
        content=json.dumps({"init_data": init_data, "surface": "business_mini_app"}),
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["user"]["username"] == "business_text_plain"


def test_client_surface_rejects_business_intake_bot_signed_init_data() -> None:
    client = _client()
    init_data = _signed_init_data(telegram_id=203, username="business_bot_wrong_surface", bot_token=BUSINESS_INTAKE_BOT_TOKEN)

    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": "req_business_bot_wrong_surface", "X-NODO-Surface": "client_mini_app"},
        json={"init_data": init_data},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TELEGRAM_INIT_DATA_INVALID"
    assert _event_types(client) == ["auth_failed"]


def test_expired_init_data_rejects() -> None:
    client = _client()
    expired = int(time.time()) - 90_000
    response = _login(client, _signed_init_data(auth_date=expired))

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "TELEGRAM_INIT_DATA_EXPIRED"


def test_existing_user_updates_last_seen_and_profile_fields() -> None:
    client = _client()
    first_response = _login(client, _signed_init_data(username="old_name"))
    user_id = first_response.json()["data"]["user"]["id"]
    first_seen = client.app.state.user_repository.get_user_by_id(user_id).last_seen_at

    second_response = _login(client, _signed_init_data(username="new_name", first_name="New"))
    updated = second_response.json()["data"]["user"]

    assert updated["id"] == user_id
    assert updated["username"] == "new_name"
    assert updated["first_name"] == "New"
    assert client.app.state.user_repository.get_user_by_id(user_id).last_seen_at >= first_seen
    assert len(client.app.state.user_repository._users_by_id) == 1


def test_blocked_user_cannot_authenticate() -> None:
    client = _client()
    response = _login(client)
    user_id = response.json()["data"]["user"]["id"]
    client.app.state.user_repository.set_user_status(user_id, "blocked")

    blocked_response = _login(client)

    assert blocked_response.status_code == 403
    assert blocked_response.json()["error"]["code"] == "USER_SUSPENDED"
    assert "auth_failed" in _event_types(client)


def test_dormant_user_cannot_refresh_or_use_authenticated_dependency() -> None:
    client = _client()
    login = _login(client).json()["data"]
    user_id = login["user"]["id"]
    client.app.state.user_repository.set_user_status(user_id, "dormant")

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Request-Id": "req_refresh_dormant"},
        json={"refresh_token": login["refresh_token"]},
    )
    me_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_me_dormant"},
    )

    assert refresh_response.status_code == 403
    assert refresh_response.json()["error"]["code"] == "USER_SUSPENDED"
    assert me_response.status_code == 403
    assert me_response.json()["error"]["code"] == "USER_SUSPENDED"


def test_restricted_admin_cannot_refresh_or_use_authenticated_dependency() -> None:
    client = _client()
    login = _login(client).json()["data"]
    user_id = login["user"]["id"]
    user = client.app.state.user_repository.get_user_by_id(user_id)
    user.role = "admin"
    client.app.state.user_repository.set_user_status(user_id, "restricted")

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Request-Id": "req_refresh_admin_restricted"},
        json={"refresh_token": login["refresh_token"]},
    )
    me_response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_me_admin_restricted"},
    )

    assert refresh_response.status_code == 403
    assert refresh_response.json()["error"]["code"] == "USER_SUSPENDED"
    assert me_response.status_code == 403
    assert me_response.json()["error"]["code"] == "USER_SUSPENDED"


def test_refresh_rotates_refresh_token_and_old_token_expires() -> None:
    client = _client()
    login = _login(client).json()["data"]

    refresh_response = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Request-Id": "req_refresh"},
        json={"refresh_token": login["refresh_token"]},
    )

    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()["data"]
    assert refreshed["refresh_token"] != login["refresh_token"]
    assert "session_refreshed" in _event_types(client)

    old_token_response = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Request-Id": "req_refresh_old"},
        json={"refresh_token": login["refresh_token"]},
    )
    assert old_token_response.status_code == 401
    assert old_token_response.json()["error"]["code"] == "SESSION_EXPIRED"


def test_expired_access_token_can_refresh_and_reauthenticate_requests() -> None:
    client = _client(ACCESS_TOKEN_TTL_SECONDS="1")
    login = _login(client).json()["data"]
    time.sleep(2.1)

    expired_me = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_expired_me"},
    )
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Request-Id": "req_refresh_after_expired_access"},
        json={"refresh_token": login["refresh_token"]},
    )

    assert expired_me.status_code == 401
    assert expired_me.json()["error"]["code"] == "SESSION_EXPIRED"
    assert refresh_response.status_code == 200
    refreshed = refresh_response.json()["data"]
    fresh_me = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {refreshed['access_token']}", "X-Request-Id": "req_fresh_me"},
    )
    assert fresh_me.status_code == 200
    assert fresh_me.json()["data"]["id"] == login["user"]["id"]


def test_refresh_token_replays_are_rejected_atomically_by_repository() -> None:
    client = _client()
    login = _login(client).json()["data"]
    repository = client.app.state.user_repository
    settings = client.app.state.settings
    old_hash = hash_refresh_token(login["refresh_token"], settings.jwt_refresh_secret)
    session = repository.get_session_by_refresh_hash(old_hash)

    assert session is not None
    first_rotation = repository.rotate_session_if_current(
        session,
        current_refresh_token_hash=old_hash,
        refresh_token_hash="0" * 64,
        access_token_jti="first-jti",
        expires_at=utc_now(),
    )
    replay_rotation = repository.rotate_session_if_current(
        session,
        current_refresh_token_hash=old_hash,
        refresh_token_hash="1" * 64,
        access_token_jti="second-jti",
        expires_at=utc_now(),
    )

    assert first_rotation is True
    assert replay_rotation is False


def test_refresh_uses_current_user_role_and_status_claims() -> None:
    client = _client()
    login = _login(client).json()["data"]
    user_id = login["user"]["id"]
    client.app.state.user_repository.set_user_role(user_id, "support")

    response = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Request-Id": "req_refresh_role_change"},
        json={"refresh_token": login["refresh_token"]},
    )

    assert response.status_code == 200
    refreshed = response.json()["data"]
    claims = decode_access_token(refreshed["access_token"], JWT_SECRET)
    assert claims["role"] == "support"
    assert claims["status"] == "active"


def test_logout_revokes_session_and_is_idempotent() -> None:
    client = _client()
    login = _login(client).json()["data"]
    headers = {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_logout"}

    response = client.post("/api/v1/auth/logout", headers=headers, json={"refresh_token": login["refresh_token"]})
    repeat = client.post("/api/v1/auth/logout", headers=headers, json={"refresh_token": login["refresh_token"]})

    assert response.status_code == 200
    assert repeat.status_code == 200
    session = next(iter(client.app.state.user_repository._sessions_by_id.values()))
    assert session.status == "revoked"
    assert session.revoked_at is not None
    assert _event_types(client).count("user_logout") == 2


def test_logout_revokes_refresh_session_even_when_access_token_expired() -> None:
    client = _client(ACCESS_TOKEN_TTL_SECONDS="1")
    login = _login(client).json()["data"]
    time.sleep(2.1)

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_logout_expired_access"},
        json={"refresh_token": login["refresh_token"]},
    )
    refresh_after_logout = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Request-Id": "req_refresh_after_logout"},
        json={"refresh_token": login["refresh_token"]},
    )

    assert response.status_code == 200
    assert response.json()["data"]["logged_out"] is True
    session = next(iter(client.app.state.user_repository._sessions_by_id.values()))
    assert session.status == "revoked"
    assert session.revoked_at is not None
    assert refresh_after_logout.status_code == 401
    assert refresh_after_logout.json()["error"]["code"] == "SESSION_EXPIRED"


def test_users_me_returns_only_current_public_profile() -> None:
    client = _client()
    login = _login(client).json()["data"]
    response = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_me"},
    )

    assert response.status_code == 200
    profile = response.json()["data"]
    assert profile["id"] == login["user"]["id"]
    assert "telegram_id" not in profile


def test_auth_payloads_do_not_store_init_data_or_plain_tokens_or_secrets() -> None:
    client = _client()
    init_data = _signed_init_data()
    login = _login(client, init_data).json()["data"]

    audit_text = json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    repository_text = json.dumps(
        {
            "users": [user.__dict__ for user in client.app.state.user_repository._users_by_id.values()],
            "sessions": [session.__dict__ for session in client.app.state.user_repository._sessions_by_id.values()],
        },
        default=str,
    )
    combined = audit_text + repository_text

    assert init_data not in combined
    assert login["refresh_token"] not in combined
    assert login["access_token"] not in combined
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined


def test_auth_rate_limit_returns_rate_limited() -> None:
    client = _client(AUTH_RATE_LIMIT_MAX_ATTEMPTS="1")
    invalid = _signed_init_data().replace("hash=", "hash=bad")

    first = _login(client, invalid)
    second = _login(client, invalid)

    assert first.status_code == 401
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "RATE_LIMITED"
