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
        "APP_VERSION": "0.0.0-slice-20c",
        "NODO_BUILD_ID": "pytest-staff-20c-build",
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
    return response.json()["data"]


def _headers(login: dict, key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _bearer(login: dict, key: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": key}


def _make_user(client: TestClient, telegram_id: int, role: str, username: str | None = None) -> dict:
    login = _login(client, telegram_id, username or f"{role}_{telegram_id}")
    client.app.state.user_repository.set_user_role(login["user"]["id"], role)
    return login


def _create_business(client: TestClient, login: dict, key: str) -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, key), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": f"Casa {key}", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["business"]


def _approved_business_with_method(client: TestClient, login: dict, *, credits: int = 3) -> tuple[dict, str]:
    business = _create_business(client, login, f"biz_{login['user']['id']}")
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.verification_status = "approved"
    stored_user = client.app.state.user_repository.get_user_by_id(login["user"]["id"])
    link = client.app.state.business_repository.create_access_link(
        business_id=business["id"],
        user_id=login["user"]["id"],
        telegram_id_snapshot=stored_user.telegram_id,
        role_in_business="owner",
        linked_by_admin_id=login["user"]["id"],
        reason="test_active_business_access",
    )
    client.app.state.business_repository.set_access_link_pin_hash(link_id=link.id, pin_hash=hash_pin("1234"))
    client.app.state.business_repository.mark_access_link_pin_verified(link_id=link.id, unlocked_until=utc_now() + timedelta(minutes=15))
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
    client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=credits, created_by=login["user"]["id"])
    return business, payment.id


def _seed_ticket(client: TestClient) -> dict:
    owner = _make_user(client, 21001, "business_owner", "owner_staff_seed")
    _business, method_id = _approved_business_with_method(client, owner)
    ad_response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "staff_ad"), "Content-Type": "application/json"},
        json={
            "payment_method_id": method_id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert ad_response.status_code == 201, ad_response.text
    remitter = _make_user(client, 21002, "remitter", "remitter_staff_seed")
    order_response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "staff_order"), "Content-Type": "application/json"},
        json={
            "ad_id": ad_response.json()["data"]["ad"]["id"],
            "amount_usd": "50.00",
            "receiver_data": {"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Receptor Test"},
        },
    )
    assert order_response.status_code == 201, order_response.text
    ticket_response = client.post(
        "/api/v1/support/tickets",
        headers={**_headers(remitter, "staff_ticket"), "Content-Type": "application/json"},
        json={"scope": "client_order", "category": "technical_issue", "subject": "Ayuda", "message": "Necesito soporte", "order_id": order_response.json()["data"]["order"]["id"]},
    )
    assert ticket_response.status_code == 201, ticket_response.text
    return ticket_response.json()["data"]


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_super_admin_invites_staff_and_admin_cannot_mutate_staff() -> None:
    client = _client()
    super_admin = _make_user(client, 21100, "super_admin")
    admin = _make_user(client, 21101, "admin")
    support = _make_user(client, 21102, "support")

    payload = {
        "target_user_id": support["user"]["id"],
        "staff_role": "support_agent",
        "permissions": [{"permission": "view_assigned_support_tickets", "scope": "assigned_only", "scope_value": None}],
        "expires_at": "2027-01-01T00:00:00Z",
        "reason": "Alta soporte asignado",
    }
    created = client.post("/api/v1/admin/staff/invites", headers={**_headers(super_admin, "staff_invite"), "Content-Type": "application/json"}, json=payload)
    forbidden = client.post("/api/v1/admin/staff/invites", headers={**_headers(admin, "staff_invite_admin"), "Content-Type": "application/json"}, json=payload)
    listed = client.get("/api/v1/admin/staff", headers=_bearer(admin, "staff_list_admin"))

    assert created.status_code == 201, created.text
    assert created.json()["data"]["invite"]["staff_profile_id"]
    assert forbidden.status_code == 403
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"]["items"][0]["permission_count"] == 1
    assert {"staff_invite_created", "staff_activated"}.issubset(set(_event_types(client)))
    combined = created.text + listed.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined


def test_staff_permissions_gate_support_and_revocation_blocks_access() -> None:
    client = _client()
    ticket = _seed_ticket(client)
    super_admin = _make_user(client, 21200, "super_admin")
    support = _make_user(client, 21201, "support")

    no_profile = client.get("/api/v1/admin/support/tickets", headers=_bearer(support, "staff_no_profile"))
    assert no_profile.status_code == 403
    assert no_profile.json()["error"]["code"] == "STAFF_PERMISSION_DENIED"

    profile = client.app.state.staff_repository.create_or_activate_profile(
        user_id=support["user"]["id"],
        staff_role="support_agent",
        display_name=support["user"]["first_name"],
        actor_id=super_admin["user"]["id"],
        reason="Permitir ticket asignado",
    )
    client.app.state.staff_repository.replace_permissions(
        profile_id=profile.id,
        permissions=[
            {"permission": "view_assigned_support_tickets", "scope": "assigned_only", "scope_value": None},
            {"permission": "reply_support_ticket", "scope": "assigned_only", "scope_value": None},
        ],
        actor_id=super_admin["user"]["id"],
        reason="Permitir ticket asignado",
    )

    queue_denied = client.get("/api/v1/admin/support/tickets", headers=_bearer(support, "staff_queue_denied"))
    assert queue_denied.status_code == 403

    assigned_ticket = client.app.state.support_repository.get_ticket(ticket["id"])
    client.app.state.support_repository.update_ticket(assigned_ticket, assigned_support_user_id=support["user"]["id"])
    detail = client.get(f"/api/v1/admin/support/tickets/{ticket['id']}", headers=_bearer(support, "staff_assigned_detail"))
    reply = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/messages",
        headers={**_headers(support, "staff_reply"), "Content-Type": "application/json"},
        json={"body": "Te ayudo por aqui.", "visibility": "participants"},
    )
    assert detail.status_code == 200, detail.text
    assert reply.status_code == 201, reply.text

    revoke = client.post(
        f"/api/v1/admin/staff/{profile.id}/revoke",
        headers={**_headers(super_admin, "staff_revoke"), "Content-Type": "application/json"},
        json={"reason": "Fin de acceso"},
    )
    blocked = client.get(f"/api/v1/admin/support/tickets/{ticket['id']}", headers=_bearer(support, "staff_after_revoke"))
    assert revoke.status_code == 200, revoke.text
    assert blocked.status_code == 403
    assert "staff_revoked" in _event_types(client)


def test_staff_cannot_mutate_users_access_links_credits_businesses_or_disputes() -> None:
    client = _client()
    ticket = _seed_ticket(client)
    super_admin = _make_user(client, 21300, "super_admin")
    support = _make_user(client, 21301, "support")
    profile = client.app.state.staff_repository.create_or_activate_profile(
        user_id=support["user"]["id"],
        staff_role="support_lead",
        display_name=support["user"]["first_name"],
        actor_id=super_admin["user"]["id"],
        reason="Soporte limitado",
    )
    client.app.state.staff_repository.replace_permissions(
        profile_id=profile.id,
        permissions=[{"permission": "view_support_queue", "scope": "queue_scope", "scope_value": None}],
        actor_id=super_admin["user"]["id"],
        reason="Solo cola soporte",
    )

    target = _make_user(client, 21302, "remitter")
    suspend_user = client.post(
        f"/api/v1/admin/users/{target['user']['id']}/suspend",
        headers={**_headers(support, "staff_suspend_user"), "Content-Type": "application/json"},
        json={"reason": "No permitido"},
    )
    credit_adjust = client.post(
        "/api/v1/admin/credits/adjust",
        headers={**_headers(support, "staff_credit_adjust"), "Content-Type": "application/json"},
        json={"business_id": "11111111-1111-1111-1111-111111111111", "amount": 1, "direction": "add", "reason": "No permitido"},
    )
    resolve_dispute = client.post(
        "/api/v1/admin/disputes/11111111-1111-1111-1111-111111111111/resolve",
        headers={**_headers(support, "staff_dispute"), "Content-Type": "application/json"},
        json={"resolution_type": "completed", "reason": "No permitido"},
    )
    business_review = client.post(
        "/api/v1/admin/businesses/11111111-1111-1111-1111-111111111111/approve",
        headers={**_headers(support, "staff_business"), "Content-Type": "application/json"},
        json={"reason": "No permitido"},
    )
    ticket_list = client.get("/api/v1/admin/support/tickets", headers=_bearer(support, "staff_ticket_list"))

    assert suspend_user.status_code == 403
    assert credit_adjust.status_code == 403
    assert resolve_dispute.status_code == 403
    assert business_review.status_code == 403
    assert ticket_list.status_code == 200, ticket_list.text
    assert any(item["id"] == ticket["id"] for item in ticket_list.json()["data"]["items"])


def test_staff_permission_contract_rejects_forbidden_permissions_and_requires_reason_idempotency() -> None:
    client = _client()
    super_admin = _make_user(client, 21400, "super_admin")
    support = _make_user(client, 21401, "support")

    missing_key = client.post(
        "/api/v1/admin/staff/invites",
        headers={**_bearer(super_admin, "staff_no_key"), "Content-Type": "application/json"},
        json={
            "target_user_id": support["user"]["id"],
            "staff_role": "support_agent",
            "permissions": [],
            "expires_at": "2027-01-01T00:00:00Z",
            "reason": "Alta sin key",
        },
    )
    forbidden_permission = client.post(
        "/api/v1/admin/staff/invites",
        headers={**_headers(super_admin, "staff_forbidden_perm"), "Content-Type": "application/json"},
        json={
            "target_user_id": support["user"]["id"],
            "staff_role": "support_agent",
            "permissions": [{"permission": "block_user", "scope": "global_readonly", "scope_value": None}],
            "expires_at": "2027-01-01T00:00:00Z",
            "reason": "Intento peligroso",
        },
    )

    assert missing_key.status_code == 400
    assert missing_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert forbidden_permission.status_code == 409
    assert forbidden_permission.json()["error"]["code"] == "STAFF_PERMISSION_CONFLICT"


def test_staff_role_permission_and_base_role_compatibility_are_enforced() -> None:
    client = _client()
    super_admin = _make_user(client, 21500, "super_admin")
    support = _make_user(client, 21501, "support")
    admin = _make_user(client, 21502, "admin")

    readonly_with_mutation = client.post(
        "/api/v1/admin/staff/invites",
        headers={**_headers(super_admin, "staff_readonly_mutation"), "Content-Type": "application/json"},
        json={
            "target_user_id": support["user"]["id"],
            "staff_role": "operations_readonly",
            "permissions": [{"permission": "reply_support_ticket", "scope": "global_readonly", "scope_value": None}],
            "expires_at": "2027-01-01T00:00:00Z",
            "reason": "No debe mutar tickets",
        },
    )
    support_as_admin_staff = client.post(
        "/api/v1/admin/staff/invites",
        headers={**_headers(super_admin, "staff_role_mismatch"), "Content-Type": "application/json"},
        json={
            "target_user_id": support["user"]["id"],
            "staff_role": "admin",
            "permissions": [{"permission": "view_users_masked", "scope": "global_readonly", "scope_value": None}],
            "expires_at": "2027-01-01T00:00:00Z",
            "reason": "No debe elevar rol base",
        },
    )
    admin_as_admin_staff = client.post(
        "/api/v1/admin/staff/invites",
        headers={**_headers(super_admin, "staff_admin_valid"), "Content-Type": "application/json"},
        json={
            "target_user_id": admin["user"]["id"],
            "staff_role": "admin",
            "permissions": [{"permission": "view_users_masked", "scope": "global_readonly", "scope_value": None}],
            "expires_at": "2027-01-01T00:00:00Z",
            "reason": "Admin interno compatible",
        },
    )

    assert readonly_with_mutation.status_code == 409
    assert readonly_with_mutation.json()["error"]["code"] == "STAFF_PERMISSION_CONFLICT"
    assert support_as_admin_staff.status_code == 400
    assert support_as_admin_staff.json()["error"]["code"] == "STAFF_ASSIGNMENT_INVALID"
    assert admin_as_admin_staff.status_code == 201, admin_as_admin_staff.text
