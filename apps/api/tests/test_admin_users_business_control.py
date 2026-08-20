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
from app.modules.businesses.models import BusinessAccessLinkRecord, new_id, utc_now  # noqa: E402


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
    assert admin_search.json()["data"]["items"][0]["phone"] is None
    assert admin_search.json()["data"]["items"][0]["phone_masked"]
    assert admin_search.json()["data"]["items"][0]["telegram_id"] == 20103
    assert support_search.status_code == 200, support_search.text
    assert support_search.json()["data"]["items"][0]["phone"] is None
    assert support_search.json()["data"]["items"][0]["phone_masked"]
    assert support_search.json()["data"]["items"][0]["telegram_id"] is None
    assert support_search.json()["data"]["items"][0]["telegram_id_masked"]
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["user"]["phone"] is None
    assert detail.json()["data"]["user"]["phone_masked"]
    assert detail.json()["data"]["access_links"][0]["id"] == link["id"]
    assert business_links.status_code == 200, business_links.text
    assert business_links.json()["data"]["items"][0]["user"]["telegram_id_masked"]
    combined = admin_search.text + support_search.text + detail.text + business_links.text
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert BOT_TOKEN not in combined


def test_admin_businesses_filter_by_business_id_or_name() -> None:
    client = _client()
    admin = _make_admin(client, 20111, "admin")
    owner_a = _login(client, 20112, "owner_business_a")
    owner_b = _login(client, 20113, "owner_business_b")
    business_a = _approved_business(client, owner_a)
    business_b = _approved_business(client, owner_b)
    stored_b = client.app.state.business_repository.get_business(business_b["id"])
    stored_b.business_name = "Envios Zulia"

    by_id = client.get(
        f"/api/v1/admin/businesses?business_id={business_b['id']}&limit=20",
        headers=_bearer(admin, "req_business_filter_id"),
    )
    by_name = client.get(
        "/api/v1/admin/businesses?business_name=zulia&limit=20",
        headers=_bearer(admin, "req_business_filter_name"),
    )
    by_short_name = client.get(
        "/api/v1/admin/businesses?business_name=zu&limit=20",
        headers=_bearer(admin, "req_business_filter_short"),
    )

    assert by_id.status_code == 200, by_id.text
    assert [item["id"] for item in by_id.json()["data"]["items"]] == [business_b["id"]]
    assert by_name.status_code == 200, by_name.text
    assert [item["id"] for item in by_name.json()["data"]["items"]] == [business_b["id"]]
    assert business_a["id"] not in by_name.text
    assert by_short_name.status_code == 400


def test_admin_can_reveal_user_phone_with_reason_and_audit() -> None:
    client = _client()
    admin = _make_admin(client, 20121, "admin")
    support = _make_admin(client, 20122, "support")
    owner = _login(client, 20123, "owner_reveal_phone")
    _profile(client, owner, "+58 414 999 3333")

    detail = client.get(f"/api/v1/admin/users/{owner['user']['id']}", headers=_bearer(admin, "req_masked_user_detail"))
    missing_reason = client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/phone/reveal",
        headers={**_bearer(admin, "req_reveal_phone_missing"), "Content-Type": "application/json"},
        json={"reason": ""},
    )
    support_forbidden = client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/phone/reveal",
        headers={**_bearer(support, "req_reveal_phone_support"), "Content-Type": "application/json"},
        json={"reason": "police report request"},
    )
    reveal_reason = "police report request"
    revealed = client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/phone/reveal",
        headers={**_bearer(admin, "req_reveal_phone_admin"), "Content-Type": "application/json"},
        json={"reason": reveal_reason},
    )

    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["user"]["phone"] is None
    assert "+58 414 999 3333" not in detail.text
    assert missing_reason.status_code == 400
    assert missing_reason.json()["error"]["code"] == "ADMIN_REASON_REQUIRED"
    assert support_forbidden.status_code == 403
    assert revealed.status_code == 200, revealed.text
    assert revealed.headers["Cache-Control"] == "private, no-store"
    assert revealed.json()["data"]["phone"] == "+58 414 999 3333"
    assert revealed.json()["data"]["phone_masked"]
    audit_events = client.app.state.audit_writer.events
    assert any(event.event_type == "admin_user_phone_revealed" for event in audit_events)
    audit_metadata = json.dumps([event.metadata_json for event in audit_events])
    assert "+58 414 999 3333" not in audit_metadata
    assert reveal_reason not in audit_metadata


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
    denied_blocked = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_after_block"))
    business_access_links = client.get(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers=_headers(admin, "business_access_links_after_user_block"),
    )
    blocked_to_active = client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/reactivate",
        headers={**_headers(admin, "reactivate_blocked"), "Content-Type": "application/json"},
        json={"reason": "owner approved account unblock"},
    )
    unblock_replay = client.post(
        f"/api/v1/admin/users/{owner['user']['id']}/reactivate",
        headers={**_headers(admin, "reactivate_blocked"), "Content-Type": "application/json"},
        json={"reason": "owner approved account unblock"},
    )
    allowed_after_unblock = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_surface_after_unblock"))

    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["data"]["user"]["status"] == "restricted"
    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "USER_NOT_ACTIVE"
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["data"]["user"]["status"] == "active"
    assert blocked.status_code == 200, blocked.text
    assert blocked.json()["data"]["user"]["status"] == "blocked"
    assert denied_blocked.status_code == 403
    assert denied_blocked.json()["error"]["code"] == "USER_BLOCKED"
    assert business_access_links.status_code == 200, business_access_links.text
    assert business_access_links.json()["data"]["items"][0]["user"]["status"] == "blocked"
    assert blocked_to_active.status_code == 200, blocked_to_active.text
    assert blocked_to_active.json()["data"]["user"]["status"] == "active"
    assert unblock_replay.status_code == 200, unblock_replay.text
    assert unblock_replay.json()["data"]["user"]["status"] == "active"
    assert allowed_after_unblock.status_code == 200, allowed_after_unblock.text
    assert {"user_suspended", "user_reactivated", "user_blocked"}.issubset(set(_event_types(client)))

    suspended_notifications = _notifications_by_type(client, "user_suspended_account")
    reactivated_notifications = _notifications_by_type(client, "user_reactivated_account")
    blocked_notifications = _notifications_by_type(client, "user_blocked_account")
    assert len(suspended_notifications) == 1
    assert len(reactivated_notifications) == 2
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


def test_admin_business_detail_diagnoses_the_same_blocked_owner_as_surface_gate() -> None:
    client = _client()
    admin = _make_admin(client, 20211, "admin")
    owner = _login(client, 20212, "owner_diagnostic")
    business = _approved_business(client, owner)
    _link_business(client, admin, business, owner)
    client.app.state.user_repository.set_user_status(owner["user"]["id"], "blocked")

    denied = client.get(
        "/api/v1/surface/session",
        headers=_business_headers(owner, "req_surface_owner_blocked_diagnostic"),
    )
    detail = client.get(
        f"/api/v1/admin/businesses/{business['id']}",
        headers=_bearer(admin, "req_business_owner_blocked_diagnostic"),
    )

    assert denied.status_code == 403
    assert denied.json()["error"]["code"] == "USER_BLOCKED"
    assert detail.status_code == 200, detail.text
    diagnostic = detail.json()["data"]["access_diagnostic"]
    assert diagnostic == {
        "business_status": "approved",
        "business_risk_level": "normal",
        "business_can_access_surface": False,
        "owner_user_id": owner["user"]["id"],
        "owner_user_status": "blocked",
        "owner_role_valid": True,
        "owner_link_id": diagnostic["owner_link_id"],
        "owner_link_status": "active",
        "owner_link_role": "owner",
        "owner_link_conflict": False,
        "telegram_matches": True,
        "blocking_reason": "USER_BLOCKED",
        "recommended_admin_action": "unblock_owner_user",
    }
    assert diagnostic["owner_link_id"]
    assert "telegram_id_snapshot" not in detail.text
    assert "init_data" not in detail.text


def test_admin_business_detail_rejects_active_operator_as_owner_access() -> None:
    client = _client()
    admin = _make_admin(client, 20221, "admin")
    owner = _login(client, 20222, "operator_diagnostic")
    business = _approved_business(client, owner)
    operator_link = client.app.state.business_repository.create_access_link(
        business_id=business["id"],
        user_id=owner["user"]["id"],
        telegram_id_snapshot=20222,
        role_in_business="operator",
        linked_by_admin_id=admin["user"]["id"],
        reason="operator role reserved for future use",
    )

    detail = client.get(
        f"/api/v1/admin/businesses/{business['id']}",
        headers=_bearer(admin, "req_business_operator_diagnostic"),
    )

    assert detail.status_code == 200, detail.text
    diagnostic = detail.json()["data"]["access_diagnostic"]
    assert diagnostic["business_can_access_surface"] is False
    assert diagnostic["owner_link_id"] == operator_link.id
    assert diagnostic["owner_link_status"] == "active"
    assert diagnostic["owner_link_role"] == "operator"
    assert diagnostic["blocking_reason"] == "BUSINESS_ACCESS_LINK_REQUIRED"
    assert diagnostic["recommended_admin_action"] == "create_owner_link"
    assert "telegram_id_snapshot" not in detail.text
    assert "init_data" not in detail.text


def test_admin_business_access_collapses_duplicate_owner_links() -> None:
    client = _client()
    admin = _make_admin(client, 20225, "admin")
    owner = _login(client, 20226, "owner_duplicate_link")
    business = _approved_business(client, owner)
    active_link = _link_business(client, admin, business, owner)
    now = utc_now()
    blocked_duplicate = BusinessAccessLinkRecord(
        id=new_id(),
        business_id=business["id"],
        user_id=owner["user"]["id"],
        telegram_id_snapshot=20226,
        role_in_business="owner",
        status="blocked",
        linked_by_admin_id=admin["user"]["id"],
        linked_at=now - timedelta(minutes=5),
        blocked_at=now,
        reason="legacy duplicate block",
        created_at=now - timedelta(minutes=5),
        updated_at=now + timedelta(seconds=5),
    )
    client.app.state.business_repository.access_links[blocked_duplicate.id] = blocked_duplicate

    detail = client.get(
        f"/api/v1/admin/businesses/{business['id']}",
        headers=_bearer(admin, "req_business_duplicate_link_detail"),
    )
    business_links = client.get(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers=_bearer(admin, "req_business_duplicate_link_list"),
    )

    assert detail.status_code == 200, detail.text
    diagnostic = detail.json()["data"]["access_diagnostic"]
    assert diagnostic["owner_link_id"] == active_link["id"]
    assert diagnostic["owner_link_status"] == "active"
    assert diagnostic["owner_link_conflict"] is False
    assert diagnostic["business_can_access_surface"] is True
    assert business_links.status_code == 200, business_links.text
    items = business_links.json()["data"]["items"]
    assert [item["status"] for item in items if item["user_id"] == owner["user"]["id"] and item["role_in_business"] == "owner"] == ["active"]


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
        json={"reason": "owner approved business unblock"},
    )
    allowed_after_unblock = client.get("/api/v1/surface/session", headers=_business_headers(owner, "req_business_surface_unblocked"))

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
    assert blocked_to_active.status_code == 200, blocked_to_active.text
    assert blocked_to_active.json()["data"]["business"]["verification_status"] == "approved"
    assert allowed_after_unblock.status_code == 200, allowed_after_unblock.text
    assert {"business_suspended", "business_reactivated", "business_blocked"}.issubset(set(_event_types(client)))

    suspended_notifications = _notifications_by_type(client, "business_suspended_owner")
    reactivated_notifications = _notifications_by_type(client, "business_reactivated_owner")
    blocked_notifications = _notifications_by_type(client, "business_blocked_owner")
    assert len(suspended_notifications) == 1
    assert len(reactivated_notifications) == 2
    assert len(blocked_notifications) == 1

    for notification, expected_text in [
        (suspended_notifications[0], "suspendido"),
        (reactivated_notifications[0], "reactivado"),
        (reactivated_notifications[1], "reactivado"),
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
    duplicate_active_link = BusinessAccessLinkRecord(
        id=new_id(),
        business_id=business["id"],
        user_id=owner["user"]["id"],
        telegram_id_snapshot=20242,
        role_in_business="owner",
        status="active",
        linked_by_admin_id=admin["user"]["id"],
        linked_at=utc_now() - timedelta(minutes=10),
        reason="legacy duplicate active",
        created_at=utc_now() - timedelta(minutes=10),
        updated_at=utc_now() - timedelta(minutes=10),
    )
    client.app.state.business_repository.access_links[duplicate_active_link.id] = duplicate_active_link

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
    business_links_after_block = client.get(
        f"/api/v1/admin/businesses/{business['id']}/access-links",
        headers=_bearer(admin, "req_access_links_after_group_block"),
    )

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
    assert business_links_after_block.status_code == 200, business_links_after_block.text
    assert [item["status"] for item in business_links_after_block.json()["data"]["items"] if item["user_id"] == owner["user"]["id"] and item["role_in_business"] == "owner"] == ["blocked"]
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
