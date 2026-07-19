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
        "APP_VERSION": "0.0.0-slice-20A",
        "NODO_BUILD_ID": "pytest-admin-users-business-control",
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


def _make_admin(client: TestClient, telegram_id: int = 20001, role: str = "admin") -> dict:
    admin = _login(client, telegram_id, role)
    client.app.state.user_repository.set_user_role(admin["user"]["id"], role)
    return admin


def _profile(client: TestClient, login: dict, phone: str) -> None:
    response = client.post(
        "/api/v1/users/me/profile",
        headers={**_bearer(login, f"profile_{login['user']['id']}"), "Content-Type": "application/json"},
        json={"first_name": login["user"]["first_name"], "phone": phone},
    )
    assert response.status_code == 200, response.text


def _approved_business(client: TestClient, owner: dict) -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(owner, f"create_biz_{owner['user']['id']}"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": "Casa Control", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201, response.text
    business = response.json()["data"]["business"]
    stored = client.app.state.business_repository.get_business(business["id"])
    stored.verification_status = "approved"
    stored.approved_at = stored.updated_at
    return business


def _link_business(client: TestClient, admin: dict, business: dict, owner: dict, key: str = "access_link") -> dict:
    response = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers={**_headers(admin, key), "Content-Type": "application/json"},
        json={"user_id": owner["user"]["id"], "role_in_business": "owner", "reason": "owner access approved"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["access_link"]


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def _notifications_by_type(client: TestClient, notification_type: str) -> list:
    return [
        notification
        for notification in client.app.state.job_repository.notification_jobs.values()
        if notification.notification_type == notification_type
    ]


def test_admin_user_search_support_masking_and_access_links_are_separated() -> None:
    client = _client()
    admin = _make_admin(client, 20101, "admin")
    support = _make_admin(client, 20102, "support")
    owner = _login(client, 20103, "owner_control")
    _profile(client, owner, "+58 414 999 2222")
    business = _approved_business(client, owner)
    link = _link_business(client, admin, business, owner)

    admin_search = client.get("/api/v1/admin/users?phone=999&limit=20", headers=_bearer(admin, "req_user_search"))
    support_search = client.get("/api/v1/admin/users?telegram_id=20103&limit=20", headers=_bearer(support, "req_support_user_search"))
    detail = client.get(f"/api/v1/admin/users/{owner['user']['id']}", headers=_bearer(admin, "req_user_detail"))
    business_links = client.get(f"/api/v1/admin/businesses/{business['id']}/access-links", headers=_bearer(admin, "req_business_links"))

    assert admin_search.status_code == 200, admin_search.text
    assert admin_search.json()["data"]["items"][0]["phone"] == "+58 414 999 2222"
    assert admin_search.json()["data"]["items"][0]["telegram_id"] == 20103
    assert support_search.status_code == 200, support_search.text
    assert support_search.json()["data"]["items"][0]["phone"] is None
    assert support_search.json()["data"]["items"][0]["phone_masked"]
    assert support_search.json()["data"]["items"][0]["telegram_id"] is None
    assert support_search.json()["data"]["items"][0]["telegram_id_masked"]
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["access_links"][0]["id"] == link["id"]
    assert business_links.status_code == 200, business_links.text
    assert business_links.json()["data"]["items"][0]["user"]["telegram_id_masked"]
    combined = admin_search.text + support_search.text + detail.text + business_links.text
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert BOT_TOKEN not in combined


def test_admin_user_status_lifecycle_and_surface_session_denial() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    admin = _make_admin(client, 20201, "admin")
    owner = _login(client, 20202, "owner_status")
    business = _approved_business(client, owner)
    _link_business(client, admin, business, owner)

    allowed = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_before_suspend"))
    assert allowed.status_code == 200, allowed.text

    suspended = client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/suspend",
        headers={**_headers(admin, "suspend_user"), "Content-Type": "application/json"},
        json={"reason": "temporary abuse review"},
    )
    denied = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_after_suspend"))
    reactivated = client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/reactivate",
        headers={**_headers(admin, "reactivate_user"), "Content-Type": "application/json"},
        json={"reason": "review completed"},
    )
    blocked = client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/block",
        headers={**_headers(admin, "block_user"), "Content-Type": "application/json"},
        json={"reason": "confirmed account abuse"},
    )
    blocked_to_active = client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/reactivate",
        headers={**_headers(admin, "reactivate_blocked"), "Content-Type": "application/json"},
        json={"reason": "blocked cannot reactivate in 20A"},
    )

    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["data"]["user"]["status"] == "restricted"
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "USER_NOT_ACTIVE"
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["data"]["user"]["status"] == "active"
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["data"]["user"]["status"] == "blocked"
    assert blocked_to_active.status_code == 409
    assert blocked_to_active.json()["error"]["code"] == "USER_STATUS_TRANSITION_INVALID"
    assert {"user_suspended", "user_reactivated", "user_blocked"}.issubset(set(_event_types(client)))

    suspended_notifications = _notifications_by_type(client, "user_suspended_account")
    reactivated_notifications = _notifications_by_type(client, "user_reactivated_account")
    blocked_notifications = _notifications_by_type(client, "user_blocked_account")
    assert len(suspended_notifications) == 1
    assert len(reactivated_notifications) == 1
    assert len(blocked_notifications) == 1

    for notification, expected_text in [
        (suspended_notifications[0], "suspendida"),
        (reactivated_notifications[0], "reactivada"),
        (blocked_notifications[0], "bloqueada"),
    ]:
        assert notification.recipient_user_id == owner["user"]["id"]
        assert notification.business_id == business["id"]
        assert notification.order_id is None
        assert notification.status == "pending"
        assert notification.metadata_json["channel"] == "telegram"
        assert notification.metadata_json["target_surface"] == "business_mini_app"
        assert notification.metadata_json["action_text"] == "Abrir NODO Negocio"
        assert notification.metadata_json["action_url"].endswith("/business/")
        assert expected_text in notification.metadata_json["message_text"]
        assert "temporary abuse review" not in notification.metadata_json["message_text"]
        assert "confirmed account abuse" not in notification.metadata_json["message_text"]


def test_admin_business_status_lifecycle_controls_business_surface_access() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    admin = _make_admin(client, 20231, "admin")
    support = _make_admin(client, 20232, "support")
    owner = _login(client, 20233, "owner_business_status")
    business = _approved_business(client, owner)
    _link_business(client, admin, business, owner)
    business_owner_id = client.app.state.business_repository.get_business(business["id"]).owner_user_id

    allowed = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_business_surface_allowed"))
    support_attempt = client.post(
        f"/api/v1/admin/businesses/{business['id']}/suspend",
        headers={**_headers(support, "support_suspend_business"), "Content-Type": "application/json"},
        json={"reason": "support cannot mutate business status"},
    )
    suspended = client.post(
        f"/api/v1/admin/businesses/{business['id']}/suspend",
        headers={**_headers(admin, "suspend_business"), "Content-Type": "application/json"},
        json={"reason": "temporary business review"},
    )
    denied_suspended = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_business_surface_suspended"))
    reactivated = client.post(
        f"/api/v1/admin/businesses/{business['id']}/reactivate",
        headers={**_headers(admin, "reactivate_business"), "Content-Type": "application/json"},
        json={"reason": "business review completed"},
    )
    allowed_again = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_business_surface_reactivated"))
    blocked = client.post(
        f"/api/v1/admin/businesses/{business['id']}/block",
        headers={**_headers(admin, "block_business"), "Content-Type": "application/json"},
        json={"reason": "confirmed business abuse"},
    )
    denied_blocked = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_business_surface_blocked"))
    blocked_to_active = client.post(
        f"/api/v1/admin/businesses/{business['id']}/reactivate",
        headers={**_headers(admin, "reactivate_blocked_business"), "Content-Type": "application/json"},
        json={"reason": "blocked businesses cannot reactivate"},
    )

    assert allowed.status_code == 200, allowed.text
    assert support_attempt.status_code == 403
    assert support_attempt.json()["error"]["code"] == "FORBIDDEN"
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["data"]["business"]["verification_status"] == "suspended"
    assert denied_suspended.status_code == 403
    assert denied_suspended.json()["error"]["code"] == "BUSINESS_SUSPENDED"
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["data"]["business"]["verification_status"] == "approved"
    assert allowed_again.status_code == 200, allowed_again.text
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["data"]["business"]["verification_status"] == "blocked"
    assert denied_blocked.status_code == 403
    assert denied_blocked.json()["error"]["code"] == "BUSINESS_BLOCKED"
    assert blocked_to_active.status_code == 409
    assert blocked_to_active.json()["error"]["code"] == "BUSINESS_STATUS_INVALID"
    assert {"business_suspended", "business_reactivated", "business_blocked"}.issubset(set(_event_types(client)))

    suspended_notifications = _notifications_by_type(client, "business_suspended_owner")
    reactivated_notifications = _notifications_by_type(client, "business_reactivated_owner")
    blocked_notifications = _notifications_by_type(client, "business_blocked_owner")
    assert len(suspended_notifications) == 1
    assert len(reactivated_notifications) == 1
    assert len(blocked_notifications) == 1

    for notification, expected_text in [
        (suspended_notifications[0], "suspendido"),
        (reactivated_notifications[0], "reactivado"),
        (blocked_notifications[0], "bloqueado"),
    ]:
        assert notification.recipient_user_id == business_owner_id
        assert notification.business_id == business["id"]
        assert notification.order_id is None
        assert notification.status == "pending"
        assert notification.metadata_json["channel"] == "telegram"
        assert notification.metadata_json["target_surface"] == "business_mini_app"
        assert notification.metadata_json["action_text"] == "Abrir NODO Negocio"
        assert notification.metadata_json["action_url"].endswith("/business/")
        assert expected_text in notification.metadata_json["message_text"]
        assert "temporary business review" not in notification.metadata_json["message_text"]
        assert "confirmed business abuse" not in notification.metadata_json["message_text"]


def test_admin_business_access_link_status_lifecycle_notifies_owner_and_controls_surface_access() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    admin = _make_admin(client, 20241, "admin")
    owner = _login(client, 20242, "owner_access_link_status")
    business = _approved_business(client, owner)
    link = _link_business(client, admin, business, owner)

    allowed = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_access_link_surface_allowed"))
    suspended = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links/{link['id']}/suspend",
        headers={**_headers(admin, "suspend_access_link"), "Content-Type": "application/json"},
        json={"reason": "temporary access review"},
    )
    denied_suspended = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_access_link_surface_suspended"))
    reactivated = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links/{link['id']}/reactivate",
        headers={**_headers(admin, "reactivate_access_link"), "Content-Type": "application/json"},
        json={"reason": "access review completed"},
    )
    allowed_again = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_access_link_surface_reactivated"))
    blocked = client.post(
        f"/api/v1/admin/businesses/{business['id']}/access-links/{link['id']}/block",
        headers={**_headers(admin, "block_access_link"), "Content-Type": "application/json"},
        json={"reason": "confirmed access abuse"},
    )
    denied_blocked = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_access_link_surface_blocked"))

    assert allowed.status_code == 200, allowed.text
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["data"]["access_link"]["status"] == "suspended"
    assert denied_suspended.status_code == 403
    assert denied_suspended.json()["error"]["code"] == "BUSINESS_ACCESS_SUSPENDED"
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["data"]["access_link"]["status"] == "active"
    assert allowed_again.status_code == 200, allowed_again.text
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["data"]["access_link"]["status"] == "blocked"
    assert denied_blocked.status_code == 403
    assert denied_blocked.json()["error"]["code"] == "BUSINESS_ACCESS_BLOCKED"
    assert {"business_access_suspended", "business_access_reactivated", "business_access_blocked"}.issubset(set(_event_types(client)))

    suspended_notifications = _notifications_by_type(client, "business_access_suspended_owner")
    reactivated_notifications = _notifications_by_type(client, "business_access_reactivated_owner")
    blocked_notifications = _notifications_by_type(client, "business_access_blocked_owner")
    assert len(suspended_notifications) == 1
    assert len(reactivated_notifications) == 1
    assert len(blocked_notifications) == 1

    for notification, expected_text in [
        (suspended_notifications[0], "suspendido"),
        (reactivated_notifications[0], "reactivado"),
        (blocked_notifications[0], "bloqueado"),
    ]:
        assert notification.recipient_user_id == owner["user"]["id"]
        assert notification.business_id == business["id"]
        assert notification.order_id is None
        assert notification.status == "pending"
        assert notification.metadata_json["channel"] == "telegram"
        assert notification.metadata_json["target_surface"] == "business_mini_app"
        assert notification.metadata_json["action_text"] == "Abrir NODO Negocio"
        assert notification.metadata_json["action_url"].endswith("/business/")
        assert expected_text in notification.metadata_json["message_text"]
        assert "temporary access review" not in notification.metadata_json["message_text"]
        assert "confirmed access abuse" not in notification.metadata_json["message_text"]


def test_admin_user_status_change_invalidates_auth_user_cache() -> None:
    from app.shared.cache import InMemoryTTLCache

    client = _client(AUTH_USER_CACHE_TTL_SECONDS="300")
    admin = _make_admin(client, 20211, "admin")
    owner = _login(client, 20212, "owner_cached_status")
    business = _approved_business(client, owner)
    _link_business(client, admin, business, owner)
    client.app.state.auth_user_cache = InMemoryTTLCache()

    allowed = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_cache_prime"))
    blocked = client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/block",
        headers={**_headers(admin, "block_cached_user"), "Content-Type": "application/json"},
        json={"reason": "cache invalidation security check"},
    )
    denied = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_after_cache_block"))

    assert allowed.status_code == 200, allowed.text
    assert blocked.status_code == 200, blocked.text
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "USER_BLOCKED"


def test_admin_read_model_cache_keys_are_role_scoped_aggregate_views() -> None:
    from app.shared.cache import InMemoryTTLCache

    client = _client(ADMIN_READ_MODEL_CACHE_TTL_SECONDS="300")
    cache = InMemoryTTLCache()
    client.app.state.admin_read_model_cache = cache
    admin = _make_admin(client, 20221, "admin")
    support = _make_admin(client, 20222, "support")

    admin_dashboard = client.get("/api/v1/admin/dashboard", headers=_bearer(admin, "req_admin_dashboard_cache"))
    support_dashboard = client.get("/api/v1/admin/dashboard", headers=_bearer(support, "req_support_dashboard_cache"))
    admin_metrics = client.get("/api/v1/admin/metrics", headers=_bearer(admin, "req_admin_metrics_cache"))

    assert admin_dashboard.status_code == 200, admin_dashboard.text
    assert support_dashboard.status_code == 200, support_dashboard.text
    assert admin_metrics.status_code == 200, admin_metrics.text
    keys = set(cache._items)  # noqa: SLF001 - cache key shape is the security guardrail under test.
    assert "admin:dashboard:v1:role:admin" in keys
    assert "admin:dashboard:v1:role:support" in keys
    assert "admin:metrics:v1:role:admin" in keys


def test_admin_user_mutation_rbac_and_last_super_admin_guard() -> None:
    client = _client()
    admin = _make_admin(client, 20301, "admin")
    support = _make_admin(client, 20302, "support")
    super_admin = _make_admin(client, 20303, "super_admin")
    remitter = _login(client, 20304, "regular_user")

    support_attempt = client.post(
        f"/api/v1/admin/users/{remitter['user']['id']}/suspend",
        headers={**_headers(support, "support_suspend"), "Content-Type": "application/json"},
        json={"reason": "support read only"},
    )
    admin_mutates_super = client.post(
        f"/api/v1/admin/users/{super_admin['user']['id']}/suspend",
        headers={**_headers(admin, "admin_suspend_super"), "Content-Type": "application/json"},
        json={"reason": "admin cannot mutate super admin"},
    )
    super_blocks_admin = client.post(
        f"/api/v1/admin/users/{admin['user']['id']}/block",
        headers={**_headers(super_admin, "super_block_admin"), "Content-Type": "application/json"},
        json={"reason": "super admin can block admin"},
    )
    last_super = client.post(
        f"/api/v1/admin/users/{super_admin['user']['id']}/block",
        headers={**_headers(super_admin, "block_last_super"), "Content-Type": "application/json"},
        json={"reason": "cannot block last super admin"},
    )

    assert support_attempt.status_code == 403
    assert admin_mutates_super.status_code == 403
    assert admin_mutates_super.json()["error"]["code"] == "USER_STATUS_MUTATION_NOT_ALLOWED"
    assert super_blocks_admin.status_code == 200, super_blocks_admin.text
    assert super_blocks_admin.json()["data"]["user"]["status"] == "blocked"
    assert last_super.status_code == 409
    assert last_super.json()["error"]["code"] == "LAST_SUPER_ADMIN_REQUIRED"
