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
        "APP_VERSION": "0.0.0-slice-20b",
        "NODO_BUILD_ID": "pytest-support-20b-build",
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


def _create_business(client: TestClient, login: dict, key: str) -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, key), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": f"Casa {key}", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["business"]


def _approved_business_with_method(client: TestClient, login: dict, *, credits: int = 5) -> tuple[dict, str]:
    business = _create_business(client, login, f"biz_{login['user']['id']}")
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.verification_status = "approved"
    stored_business.approved_at = stored_business.updated_at
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
    if credits:
        client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=credits, created_by=login["user"]["id"])
    return business, payment.id


def _create_ad(client: TestClient, owner: dict, payment_method_id: str, *, key: str = "ad") -> dict:
    response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment_method_id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["ad"]


def _create_order(client: TestClient, remitter: dict, ad_id: str, *, key: str = "order") -> dict:
    response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, key), "Content-Type": "application/json"},
        json={
            "ad_id": ad_id,
            "amount_usd": "50.00",
            "receiver_data": {"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Receptor Test"},
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["order"]


def _seed_order(client: TestClient, *, base_id: int = 20000) -> tuple[dict, dict, dict, dict, dict]:
    owner = _login(client, base_id + 1, f"owner_support_{base_id}")
    business, method_id = _approved_business_with_method(client, owner, credits=3)
    ad = _create_ad(client, owner, method_id, key=f"ad_{base_id}")
    remitter = _login(client, base_id + 2, f"remitter_support_{base_id}")
    order = _create_order(client, remitter, ad["id"], key=f"order_{base_id}")
    return owner, business, ad, remitter, order


def _make_admin(client: TestClient, telegram_id: int, role: str) -> dict:
    login = _login(client, telegram_id, f"{role}_{telegram_id}")
    client.app.state.user_repository.set_user_role(login["user"]["id"], role)
    if role == "support":
        profile = client.app.state.staff_repository.create_or_activate_profile(
            user_id=login["user"]["id"],
            staff_role="support_lead",
            display_name=login["user"].get("first_name"),
            actor_id=login["user"]["id"],
            reason="test_support_staff_permissions",
        )
        client.app.state.staff_repository.replace_permissions(
            profile_id=profile.id,
            permissions=[
                {"permission": "view_support_queue", "scope": "queue_scope", "scope_value": None},
                {"permission": "view_assigned_support_tickets", "scope": "assigned_only", "scope_value": None},
                {"permission": "reply_support_ticket", "scope": "queue_scope", "scope_value": None},
                {"permission": "assign_support_ticket", "scope": "queue_scope", "scope_value": None},
                {"permission": "escalate_support_ticket", "scope": "queue_scope", "scope_value": None},
                {"permission": "resolve_support_ticket", "scope": "queue_scope", "scope_value": None},
                {"permission": "close_support_ticket", "scope": "queue_scope", "scope_value": None},
                {"permission": "view_support_attachment", "scope": "queue_scope", "scope_value": None},
            ],
            actor_id=login["user"]["id"],
            reason="test_support_staff_permissions",
        )
    return login


def _create_ticket(client: TestClient, login: dict, *, scope: str, key: str, **extra) -> dict:
    payload = {"scope": scope, "category": "technical_issue", "subject": "Necesito ayuda", "message": "Tengo una duda operativa.", **extra}
    response = client.post("/api/v1/support/tickets", headers={**_headers(login, key), "Content-Type": "application/json"}, json=payload)
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _events(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def _open_dispute_for_order(client: TestClient, order: dict, login: dict, *, key: str) -> dict:
    dispute = client.app.state.dispute_repository.create_dispute(
        order_id=order["id"],
        opened_by_user_id=login["user"]["id"],
        opened_by_role=login["user"]["role"],
        previous_order_status=order["status"],
        reason="business_no_payment_confirmation",
        description=f"fixture {key}",
    )
    return {"id": dispute.id, "order_id": dispute.order_id}


def test_client_support_general_and_order_ownership() -> None:
    client = _client()
    _owner, _business, _ad, remitter, order = _seed_order(client)
    other = _login(client, 20003, "other_remitter")

    general = _create_ticket(client, remitter, scope="client_general", key="client_general")
    by_order = _create_ticket(client, remitter, scope="client_order", key="client_order", order_id=order["id"])

    listing = client.get("/api/v1/support/tickets", headers=_bearer(remitter, "client_support_list"))
    assert listing.status_code == 200, listing.text
    ids = {item["id"] for item in listing.json()["data"]["items"]}
    assert {general["id"], by_order["id"]}.issubset(ids)

    forbidden = client.get(f"/api/v1/support/tickets/{by_order['id']}", headers=_bearer(other, "other_ticket"))
    assert forbidden.status_code == 404


def test_business_support_scopes_and_cross_business_denial() -> None:
    client = _client()
    owner, business, ad, _remitter, order = _seed_order(client)
    purchase = client.app.state.credit_repository.create_stripe_purchase(business_id=business["id"], package_code="starter", idempotency_key="support_purchase")
    other_owner = _login(client, 20004, "other_business")
    _approved_business_with_method(client, other_owner, credits=1)

    _create_ticket(client, owner, scope="business_general", key="business_general")
    _create_ticket(client, owner, scope="business_order", key="business_order", order_id=order["id"])
    _create_ticket(client, owner, scope="business_ad", key="business_ad", ad_id=ad["id"])
    _create_ticket(client, owner, scope="business_credit", key="business_credit", credit_purchase_id=purchase.id)

    other_detail = client.get("/api/v1/support/tickets", headers=_bearer(other_owner, "other_business_list"))
    assert other_detail.status_code == 200, other_detail.text
    assert other_detail.json()["data"]["items"] == []

    cross = client.post(
        "/api/v1/support/tickets",
        headers={**_headers(other_owner, "cross_ad"), "Content-Type": "application/json"},
        json={"scope": "business_ad", "category": "technical_issue", "subject": "Ajeno", "message": "No debe pasar", "ad_id": ad["id"]},
    )
    assert cross.status_code == 404


def test_business_support_ticket_detail_messages_and_attachments_require_active_access_link() -> None:
    client = _client()
    owner, business, _ad, _remitter, _order = _seed_order(client, base_id=23000)
    ticket = _create_ticket(client, owner, scope="business_general", key="business_access_ticket")
    link = client.app.state.business_repository.get_access_link_for_business_user(
        business_id=business["id"],
        user_id=owner["user"]["id"],
    )
    assert link is not None
    client.app.state.business_repository.set_access_link_status(
        link=link,
        status="revoked",
        reason="test_revoked_business_access",
    )

    detail = client.get(f"/api/v1/support/tickets/{ticket['id']}", headers=_bearer(owner, "revoked_business_ticket_detail"))
    assert detail.status_code == 404

    message = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/messages",
        headers={**_headers(owner, "revoked_business_ticket_message"), "Content-Type": "application/json"},
        json={"body": "No debo poder responder con acceso revocado."},
    )
    assert message.status_code == 404

    attachment = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/attachments",
        headers=_headers(owner, "revoked_business_ticket_attachment"),
        files={"file": ("proof.png", b"proof", "image/png")},
    )
    assert attachment.status_code == 404


def test_admin_support_queue_actions_do_not_mutate_domain_state() -> None:
    client = _client()
    owner, business, ad, remitter, order = _seed_order(client)
    ticket = _create_ticket(client, remitter, scope="client_order", key="support_lifecycle", order_id=order["id"])
    support = _make_admin(client, 20005, "support")
    admin = _make_admin(client, 20006, "admin")

    listed = client.get("/api/v1/admin/support/tickets", headers=_bearer(support, "support_admin_list"))
    assert listed.status_code == 200, listed.text
    assert any(item["id"] == ticket["id"] for item in listed.json()["data"]["items"])

    assigned = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/assign",
        headers={**_headers(admin, "assign_ticket"), "Content-Type": "application/json"},
        json={"assigned_support_user_id": support["user"]["id"], "reason": "Atencion de soporte"},
    )
    assert assigned.status_code == 200, assigned.text

    response = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/messages",
        headers={**_headers(support, "support_reply"), "Content-Type": "application/json"},
        json={"body": "Te ayudamos por aqui.", "visibility": "participants"},
    )
    assert response.status_code == 201, response.text

    escalated = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/escalate",
        headers={**_headers(support, "support_escalate"), "Content-Type": "application/json"},
        json={"reason": "Necesita revision interna"},
    )
    assert escalated.status_code == 200, escalated.text
    assert escalated.json()["data"]["status"] == "escalated"

    resolved = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/resolve",
        headers={**_headers(support, "support_resolve"), "Content-Type": "application/json"},
        json={"reason": "Aclarado sin cambios de dominio"},
    )
    assert resolved.status_code == 200, resolved.text

    closed = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/close",
        headers={**_headers(support, "support_close"), "Content-Type": "application/json"},
        json={"reason": "Caso cerrado"},
    )
    assert closed.status_code == 200, closed.text

    assert client.app.state.order_repository.get_by_id(order["id"]).status == "waiting_payment"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet.consumed_credits == 0
    event_types = _events(client)
    assert "support_ticket_assigned" in event_types
    assert "support_message_created" in event_types
    assert "support_ticket_escalated" in event_types
    assert "support_ticket_resolved" in event_types
    assert "support_ticket_closed" in event_types


def test_support_ticket_assignment_requires_active_staff_profile_for_support_assignee() -> None:
    client = _client()
    _owner, _business, _ad, remitter, order = _seed_order(client)
    ticket = _create_ticket(client, remitter, scope="client_order", key="support_assignment_staff_required", order_id=order["id"])
    admin = _make_admin(client, 20009, "admin")
    support_without_profile = _login(client, 20010, "support_without_profile")
    client.app.state.user_repository.set_user_role(support_without_profile["user"]["id"], "support")

    rejected = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/assign",
        headers={**_headers(admin, "assign_without_staff_profile"), "Content-Type": "application/json"},
        json={"assigned_support_user_id": support_without_profile["user"]["id"], "reason": "Debe tener perfil staff activo"},
    )

    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "SUPPORT_ASSIGNEE_INVALID"


def test_support_escalate_validates_existing_dispute_context() -> None:
    client = _client()
    _owner, _business, ad, remitter, order = _seed_order(client)
    _other_owner, _other_business, _other_ad, other_remitter, other_order = _seed_order(client, base_id=20100)
    ticket = _create_ticket(client, remitter, scope="client_order", key="support_dispute_context", order_id=order["id"])
    support = _make_admin(client, 20008, "support")
    dispute = _open_dispute_for_order(client, order, remitter, key="support_context_dispute")
    other_dispute = _open_dispute_for_order(client, other_order, other_remitter, key="support_other_context_dispute")

    missing = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/escalate",
        headers={**_headers(support, "support_escalate_missing_dispute"), "Content-Type": "application/json"},
        json={"reason": "No debe vincular falso", "existing_dispute_id": "11111111-1111-1111-1111-111111111111"},
    )
    wrong_order = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/escalate",
        headers={**_headers(support, "support_escalate_wrong_dispute"), "Content-Type": "application/json"},
        json={"reason": "No debe vincular disputa ajena", "existing_dispute_id": other_dispute["id"]},
    )
    linked = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/escalate",
        headers={**_headers(support, "support_escalate_valid_dispute"), "Content-Type": "application/json"},
        json={"reason": "Vincular disputa existente", "existing_dispute_id": dispute["id"]},
    )

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "DISPUTE_NOT_FOUND"
    assert wrong_order.status_code == 404
    assert wrong_order.json()["error"]["code"] == "DISPUTE_NOT_FOUND"
    assert linked.status_code == 200, linked.text
    assert linked.json()["data"]["dispute_id"] == dispute["id"]
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "waiting_payment"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"


def test_support_attachments_are_private_limited_and_signed_url_not_persisted() -> None:
    client = _client()
    _owner, _business, _ad, remitter, order = _seed_order(client)
    ticket = _create_ticket(client, remitter, scope="client_order", key="attachment_ticket", order_id=order["id"])
    support = _make_admin(client, 20007, "support")

    valid = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/attachments",
        headers=_headers(remitter, "support_attachment"),
        files={"file": ("proof.png", b"proof", "image/png")},
    )
    assert valid.status_code == 201, valid.text
    file_id = valid.json()["data"]["attachment"]["id"]

    bad_mime = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/attachments",
        headers=_headers(remitter, "support_attachment_bad"),
        files={"file": ("bad.exe", b"bad", "application/x-msdownload")},
    )
    assert bad_mime.status_code == 400

    too_large = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/attachments",
        headers=_headers(remitter, "support_attachment_large"),
        files={"file": ("large.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
    )
    assert too_large.status_code == 400

    view_url = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/attachments/{file_id}/view-url",
        headers={**_bearer(support, "support_view_url"), "Content-Type": "application/json"},
        json={"reason": "Revisar adjunto"},
    )
    assert view_url.status_code == 200, view_url.text
    signed_url = view_url.json()["data"]["url"]
    combined = valid.text + view_url.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert signed_url not in json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "support_attachment_viewed" in _events(client)
