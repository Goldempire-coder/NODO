from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-22",
        "NODO_BUILD_ID": "pytest-api-input-validation-hardening",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "BUSINESS_INTAKE_BOT_TOKEN": BOT_TOKEN,
        "JWT_SECRET": JWT_SECRET,
        "JWT_REFRESH_SECRET": JWT_REFRESH_SECRET,
        "AUTH_INIT_DATA_MAX_AGE_SECONDS": "86400",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "2592000",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
        "BUSINESS_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "BUSINESS_RATE_LIMIT_WINDOW_SECONDS": "60",
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    return TestClient(create_app())


def _signed_init_data(telegram_id: int, username: str) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": username}, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def _login(client: TestClient, telegram_id: int, username: str) -> dict:
    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": f"req_login_{telegram_id}"},
        json={"init_data": _signed_init_data(telegram_id, username)},
    )
    assert response.status_code == 200, response.text
    login = response.json()["data"]
    terms = client.post(
        "/api/v1/users/me/terms-acceptance",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": f"req_terms_{telegram_id}"},
        json={"terms_version": "2026-07-06"},
    )
    assert terms.status_code == 200, terms.text
    login["user"] = terms.json()["data"]
    return login


def _headers(login: dict, key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _bearer(login: dict, key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": key}


def _assert_safe_validation_error(response) -> None:  # type: ignore[no-untyped-def]
    assert response.status_code == 422, response.text
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"
    text = response.text.lower()
    forbidden_fragments = [
        "traceback",
        "sql",
        "storage_path",
        "account_value",
        "authorization",
        "bearer ",
        JWT_SECRET.lower(),
        JWT_REFRESH_SECRET.lower(),
        BOT_TOKEN.lower(),
    ]
    assert all(fragment not in text for fragment in forbidden_fragments)


def test_auth_payloads_reject_uncontracted_fields_with_safe_error() -> None:
    client = _client()
    auth_response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": "req_strict_auth"},
        json={"init_data": _signed_init_data(22001, "strict_auth"), "role": "admin"},
    )
    refresh_response = client.post(
        "/api/v1/auth/refresh",
        headers={"X-Request-Id": "req_strict_refresh"},
        json={"refresh_token": "refresh", "surface": "admin_web"},
    )

    _assert_safe_validation_error(auth_response)
    _assert_safe_validation_error(refresh_response)


def test_nested_order_receiver_rejects_uncontracted_fields_before_service_logic() -> None:
    client = _client()
    login = _login(client, 22002, "strict_order")
    response = client.post(
        "/api/v1/orders",
        headers={**_headers(login, "strict_order_extra"), "Content-Type": "application/json"},
        json={
            "ad_id": "ad_missing",
            "amount_usd": "25.00",
            "receiver_data": {
                "bank": "Banco",
                "phone": "+584121234567",
                "document": "V12345678",
                "holder": "Cliente Receptor",
                "storage_path": "private/path/should/not/be/accepted",
            },
        },
    )

    _assert_safe_validation_error(response)


def test_support_and_staff_payloads_reject_extra_fields() -> None:
    client = _client()
    remitter = _login(client, 22003, "strict_support")
    super_admin = _login(client, 22004, "strict_super_admin")
    support = _login(client, 22005, "strict_support_staff")
    client.app.state.user_repository.set_user_role(super_admin["user"]["id"], "super_admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")

    support_response = client.post(
        "/api/v1/support/tickets",
        headers={**_headers(remitter, "strict_ticket_extra"), "Content-Type": "application/json"},
        json={
            "scope": "client_general",
            "category": "technical",
            "subject": "No puedo entrar",
            "message": "Necesito ayuda con la app",
            "admin_only": True,
        },
    )
    staff_response = client.post(
        "/api/v1/admin/staff/invites",
        headers={**_headers(super_admin, "strict_staff_extra"), "Content-Type": "application/json"},
        json={
            "target_user_id": support["user"]["id"],
            "staff_role": "support_agent",
            "permissions": [
                {
                    "permission": "view_assigned_support_tickets",
                    "scope": "assigned_only",
                    "scope_value": None,
                    "can_mutate_credits": True,
                }
            ],
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "reason": "delegar soporte limitado",
        },
    )

    _assert_safe_validation_error(support_response)
    _assert_safe_validation_error(staff_response)


def test_admin_reason_whitespace_only_is_rejected_before_mutation() -> None:
    client = _client()
    admin = _login(client, 22006, "strict_admin")
    target = _login(client, 22007, "strict_target")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    response = client.post(
        f"/api/v1/admin/users/{target['user']['id']}/suspend",
        headers={**_headers(admin, "strict_admin_reason"), "Content-Type": "application/json"},
        json={"reason": "   "},
    )

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "ADMIN_REASON_REQUIRED"
    assert client.app.state.user_repository.get_user_by_id(target["user"]["id"]).status == "active"


def test_telegram_webhooks_reject_malformed_or_non_object_json_safely() -> None:
    client = _client()
    secret = hashlib.sha256(BOT_TOKEN.encode("utf-8")).hexdigest()[:40]

    client_bot_response = client.post(
        f"/api/v1/telegram/webhook/{secret}",
        headers={"Content-Type": "application/json", "X-Request-Id": "req_bad_client_bot_json"},
        content=b"{",
    )
    intake_bot_response = client.post(
        f"/api/v1/business-intake/telegram/webhook/{secret}",
        headers={"Content-Type": "application/json", "X-Request-Id": "req_bad_intake_bot_json"},
        json=["not", "an", "object"],
    )

    _assert_safe_validation_error(client_bot_response)
    assert intake_bot_response.status_code == 400, intake_bot_response.text
    assert intake_bot_response.json()["error"]["code"] == "BOT_INPUT_INVALID"
    assert "traceback" not in intake_bot_response.text.lower()


def test_auth_rejects_oversized_init_data_before_signature_validation() -> None:
    client = _client()
    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": "req_oversized_init_data"},
        json={"init_data": "x" * 9000},
    )

    _assert_safe_validation_error(response)


def test_nested_attachment_ids_reject_oversized_items() -> None:
    client = _client()
    login = _login(client, 22008, "strict_attachment_ids")
    response = client.post(
        "/api/v1/support/tickets",
        headers={**_headers(login, "strict_ticket_attachment_id"), "Content-Type": "application/json"},
        json={
            "scope": "client_general",
            "category": "technical_issue",
            "subject": "Tengo un problema",
            "message": "Necesito soporte",
            "attachment_ids": ["a" * 200],
        },
    )

    _assert_safe_validation_error(response)


def test_upload_routes_reject_oversized_file_before_domain_lookup() -> None:
    client = _client()
    login = _login(client, 22009, "strict_upload")
    oversized = b"x" * ((5 * 1024 * 1024) + 1)
    response = client.post(
        "/api/v1/support/tickets/ticket_missing/attachments",
        headers=_headers(login, "strict_oversized_support_attachment"),
        files={"file": ("oversized.png", oversized, "image/png")},
    )

    assert response.status_code == 400, response.text
    assert response.json()["error"]["code"] == "SUPPORT_ATTACHMENT_TOO_LARGE"
    assert "traceback" not in response.text.lower()
