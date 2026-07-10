from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-14B1",
        "NODO_BUILD_ID": "pytest-business-access-control-build",
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
    return response.json()["data"]


def _headers(login: dict, key: str = "idem") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _bearer(login: dict, key: str = "req") -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": key}


def _business_headers(login: dict, key: str = "req") -> dict[str, str]:
    return {**_bearer(login, key), "X-NODO-Surface": "business_mini_app"}


def _create_approved_business(client: TestClient, owner: dict) -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={
            **_headers(owner, f"create_{owner['user']['id']}"),
            "Content-Type": "application/json",
            "X-NODO-Test-Fixture": "business_create",
        },
        json={"business_name": "Casa Link", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201, response.text
    business = response.json()["data"]["business"]
    stored = client.app.state.business_repository.get_business(business["id"])
    stored.verification_status = "approved"
    stored.approved_at = stored.updated_at
    return business


def _admin_login(client: TestClient, telegram_id: int = 14001) -> dict:
    admin = _login(client, telegram_id, "admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    return admin


def _link_business(client: TestClient, admin: dict, business: dict, owner: dict, key: str = "link") -> dict:
    response = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_headers(admin, key), "Content-Type": "application/json"},
        json={"user_id": owner["user"]["id"], "role_in_business": "owner", "reason": "admin approved owner access"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["access_link"]


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_surface_session_allows_approved_business_with_active_link() -> None:
    client = _client()
    owner = _login(client, 14101, "owner")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client)
    _link_business(client, admin, business, owner)

    response = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_allowed"))

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["allowed"] is True
    assert data["surface"] == "business_mini_app"
    assert data["access_state"] == "allowed"
    assert data["business"]["id"] == business["id"]
    assert "telegram_id" not in data["user"]
    assert "business.ads.create" in data["capabilities"]


def test_surface_session_denies_remitter_and_business_owner_without_link() -> None:
    client = _client()
    remitter = _login(client, 14111, "remitter")
    denied_remitter = client.get("/api/v1/surface/session", headers=_business_headers(remitter, "req_surface_remitter"))
    assert denied_remitter.status_code == 403
    assert denied_remitter.json()["error"]["code"] == "SURFACE_ACCESS_DENIED"

    owner = _login(client, 14112, "owner_without_link")
    _create_approved_business(client, owner)
    denied_owner = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_no_link"))
    assert denied_owner.status_code == 403
    assert denied_owner.json()["error"]["code"] == "BUSINESS_ACCESS_LINK_REQUIRED"
    assert "surface_access_denied" in _event_types(client)


def test_surface_session_denies_link_statuses_and_business_user_statuses() -> None:
    client = _client()
    admin = _admin_login(client)
    for status, expected_code in [
        ("suspended", "BUSINESS_ACCESS_SUSPENDED"),
        ("revoked", "BUSINESS_ACCESS_REVOKED"),
        ("blocked", "BUSINESS_ACCESS_BLOCKED"),
    ]:
        owner = _login(client, 14200 + len(_event_types(client)), f"owner_{status}")
        business = _create_approved_business(client, owner)
        link = _link_business(client, admin, business, owner, key=f"link_{status}")
        client.app.state.business_repository.set_access_link_status(
            link=client.app.state.business_repository.get_access_link(link["id"]),
            status=status,
            reason=f"test {status}",
        )
        response = client.get("/api/v1/surface/session", headers=_business_headers(owner, f"req_surface_{status}"))
        assert response.status_code == 403
        assert response.json()["error"]["code"] == expected_code

    user_blocked = _login(client, 14220, "blocked_user")
    blocked_business = _create_approved_business(client, user_blocked)
    _link_business(client, admin, blocked_business, user_blocked, key="link_user_blocked")
    client.app.state.user_repository.set_user_status(user_blocked["user"]["id"], "blocked")
    response = client.get("/api/v1/surface/session", headers=_business_headers(user_blocked, "req_blocked_user"))
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "USER_BLOCKED"

    suspended_business_owner = _login(client, 14221, "suspended_business")
    business = _create_approved_business(client, suspended_business_owner)
    _link_business(client, admin, business, suspended_business_owner, key="link_business_suspended")
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.verification_status = "suspended"
    business_response = client.get("/api/v1/surface/session", headers=_business_headers(suspended_business_owner, "req_business_suspended"))
    assert business_response.status_code == 403
    assert business_response.json()["error"]["code"] == "BUSINESS_SUSPENDED"

    blocked_business_owner = _login(client, 14222, "blocked_business")
    blocked_business = _create_approved_business(client, blocked_business_owner)
    _link_business(client, admin, blocked_business, blocked_business_owner, key="link_business_blocked")
    stored_blocked_business = client.app.state.business_repository.get_business(blocked_business["id"])
    stored_blocked_business.verification_status = "blocked"
    blocked_business_response = client.get("/api/v1/surface/session", headers=_business_headers(blocked_business_owner, "req_business_blocked"))
    assert blocked_business_response.status_code == 403
    assert blocked_business_response.json()["error"]["code"] == "BUSINESS_BLOCKED"


def test_admin_access_link_lifecycle_requires_reason_idempotency_and_blocks_support() -> None:
    client = _client()
    owner = _login(client, 14301, "owner_lifecycle")
    business = _create_approved_business(client, owner)
    admin = _admin_login(client)
    support = _login(client, 14303, "support")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")

    no_idem = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_bearer(admin, "req_no_idem"), "Content-Type": "application/json"},
        json={"user_id": owner["user"]["id"], "reason": "missing idempotency"},
    )
    assert no_idem.status_code == 400
    assert no_idem.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    support_attempt = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_headers(support, "support_link"), "Content-Type": "application/json"},
        json={"user_id": owner["user"]["id"], "reason": "support cannot mutate"},
    )
    assert support_attempt.status_code == 403

    different_user = _login(client, 14304, "different_owner")
    wrong_owner_attempt = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_headers(admin, "wrong_owner_link"), "Content-Type": "application/json"},
        json={"user_id": different_user["user"]["id"], "role_in_business": "owner", "reason": "cannot link a different owner"},
    )
    assert wrong_owner_attempt.status_code == 422
    assert wrong_owner_attempt.json()["error"]["code"] == "VALIDATION_ERROR"

    link = _link_business(client, admin, business, owner, key="link_lifecycle")
    replay = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_headers(admin, "link_lifecycle"), "Content-Type": "application/json"},
        json={"user_id": owner["user"]["id"], "role_in_business": "owner", "reason": "admin approved owner access"},
    )
    assert replay.status_code in {200, 201}
    assert replay.json()["data"]["access_link"]["id"] == link["id"]

    for action, expected_status in [
        ("suspend", "suspended"),
        ("reactivate", "active"),
        ("revoke", "revoked"),
        ("block", "blocked"),
    ]:
        response = client.post(
            f"/api/v1/admin/businesses/{business['id']}/access-links/{link['id']}/{action}",
            headers={**_headers(admin, f"{action}_link"), "Content-Type": "application/json"},
            json={"reason": f"{action} access"},
        )
        assert response.status_code == 200, response.text
        assert response.json()["data"]["access_link"]["status"] == expected_status

    assert {"business_access_linked", "business_access_suspended", "business_access_reactivated", "business_access_unlinked", "business_access_blocked"}.issubset(set(_event_types(client)))


def test_business_operations_fail_without_active_link_and_pass_with_link() -> None:
    client = _client()
    owner = _login(client, 14401, "owner_ops")
    business = _create_approved_business(client, owner)
    payment = client.app.state.business_repository.add_payment_method(
        business_id=business["id"],
        method_type="zelle",
        network=None,
        account_value="owner@example.com",
        account_masked="***.com",
        holder_name="Owner Test",
    )
    payment.verified_status = "approved"
    payment.active = True
    client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=2, created_by=owner["user"]["id"])

    blocked = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "ad_without_link"), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment.id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "BUSINESS_ACCESS_LINK_REQUIRED"

    admin = _admin_login(client)
    _link_business(client, admin, business, owner)
    allowed = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "ad_with_link"), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment.id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert allowed.status_code == 201, allowed.text
