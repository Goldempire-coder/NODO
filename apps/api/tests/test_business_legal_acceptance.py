from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from urllib.parse import urlencode

from fastapi.testclient import TestClient

BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-business-legal",
        "NODO_BUILD_ID": "pytest-business-legal-build",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "JWT_SECRET": JWT_SECRET,
        "JWT_REFRESH_SECRET": JWT_REFRESH_SECRET,
        "AUTH_INIT_DATA_MAX_AGE_SECONDS": "86400",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "2592000",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
        "BUSINESS_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "BUSINESS_RATE_LIMIT_WINDOW_SECONDS": "60",
        "NODO_CREDIT_RECEIVING_WALLET_BASE": "0x1111111111111111111111111111111111111111",
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.modules.businesses.models import utc_now  # noqa: E402
from app.modules.businesses.pin_security import hash_pin  # noqa: E402


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
        "X-NODO-Surface": "business_mini_app",
        "Content-Type": "application/json",
    }


def _create_approved_business(client: TestClient, login: dict, key: str) -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, f"create_{key}"), "Idempotency-Key": f"create_{key}", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": f"Casa {key}", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201, response.text
    business = response.json()["data"]["business"]
    stored = client.app.state.business_repository.get_business(business["id"])
    stored.verification_status = "approved"
    stored.approved_at = stored.updated_at
    stored_user = client.app.state.user_repository.get_user_by_id(login["user"]["id"])
    link = client.app.state.business_repository.create_access_link(
        business_id=business["id"],
        user_id=login["user"]["id"],
        telegram_id_snapshot=stored_user.telegram_id,
        role_in_business="owner",
        linked_by_admin_id=login["user"]["id"],
        reason="business_legal_test_access",
    )
    client.app.state.business_repository.set_access_link_pin_hash(link_id=link.id, pin_hash=hash_pin("1234"))
    client.app.state.business_repository.mark_access_link_pin_verified(link_id=link.id, unlocked_until=utc_now() + timedelta(minutes=15))
    return business


def _requirements_by_set(client: TestClient, login: dict) -> dict[str, dict]:
    response = client.get("/api/v1/business/legal/requirements", headers=_headers(login, "legal_requirements"))
    assert response.status_code == 200, response.text
    requirements = response.json()["data"]["requirements"]
    return {item["document_set"]: item for item in requirements}


def _accept_legal(client: TestClient, login: dict, document_set: str) -> dict:
    requirement = _requirements_by_set(client, login)[document_set]
    response = client.post(
        "/api/v1/business/legal/acceptances",
        headers=_headers(login, f"accept_{document_set}"),
        json={
            "document_set": document_set,
            "document_version": requirement["document_version"],
            "confirmation": "ACCEPTED_BY_AUTHORIZED_BUSINESS_REPRESENTATIVE",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def test_business_legal_requirements_are_explicit_and_acceptance_is_idempotent() -> None:
    client = _client()
    owner = _login(client, 62101, "owner_business_legal")
    _create_approved_business(client, owner, "legal")

    requirements = _requirements_by_set(client, owner)
    assert requirements["business_terms"]["accepted"] is False
    assert requirements["business_credit_terms"]["accepted"] is False

    first = _accept_legal(client, owner, "business_terms")
    second = _accept_legal(client, owner, "business_terms")

    assert first["acceptance"]["id"] == second["acceptance"]["id"]
    refreshed = {item["document_set"]: item for item in second["requirements"]}
    assert refreshed["business_terms"]["accepted"] is True
    assert refreshed["business_credit_terms"]["accepted"] is False
    assert any(event.event_type == "business_legal_terms_accepted" for event in client.app.state.audit_writer.events)


def test_business_credit_handoff_requires_credit_terms_without_touching_payment_runtime() -> None:
    client = _client()
    owner = _login(client, 62102, "owner_credit_terms_gate")
    _create_approved_business(client, owner, "credit_terms_gate")
    _accept_legal(client, owner, "business_terms")

    response = client.post(
        "/api/v1/business/credits/handoffs",
        headers=_headers(owner, "handoff_without_credit_terms"),
        json={"package_code": "starter"},
    )

    assert response.status_code == 403, response.text
    assert response.json()["error"]["code"] == "BUSINESS_CREDIT_TERMS_ACCEPTANCE_REQUIRED"
    assert client.app.state.credit_handoff_store._records == {}


def test_credit_status_reads_are_not_blocked_by_missing_credit_terms() -> None:
    client = _client()
    owner = _login(client, 62103, "owner_credit_status")
    _create_approved_business(client, owner, "credit_status")

    response = client.get(
        "/api/v1/business/credits/purchases/pending-contract",
        headers=_headers(owner, "pending_without_credit_terms"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["purchase"] is None
