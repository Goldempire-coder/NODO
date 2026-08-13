from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

import pytest
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
from app.modules.support.models import ACTIVE_SUPPORT_STATUSES  # noqa: E402
from app.modules.support.postgres_repository import PostgresSupportRepository  # noqa: E402
from app.shared.keyset_pagination import encode_keyset_cursor  # noqa: E402
from photo_test_data import photo_bytes, png_bytes  # noqa: E402


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


def _seed_repository_ticket(
    client: TestClient,
    *,
    requester: dict,
    status: str,
    subject: str,
    business_id: str | None = None,
    scope: str = "client_general",
) -> dict:
    ticket = client.app.state.support_repository.create_ticket(
        requester_user_id=requester["user"]["id"],
        requester_role=requester["user"]["role"],
        requester_surface="business_mini_app" if requester["user"]["role"] == "business_owner" else "client_mini_app",
        scope=scope,
        category="technical_issue",
        status=status,
        priority="normal",
        subject=subject,
        business_id=business_id,
        order_id=None,
        ad_id=None,
        credit_purchase_id=None,
        dispute_id=None,
        assigned_support_user_id=None,
        last_message_at=None,
        escalated_at=None,
        resolved_at=utc_now() if status == "resolved" else None,
        closed_at=utc_now() if status == "closed" else None,
    )
    return {"id": ticket.id, "status": ticket.status}


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


def _create_operation_report(
    client: TestClient,
    login: dict,
    order_id: str,
    *,
    key: str,
    category: str = "order_help",
    message: str = "Necesito que Soporte revise esta operacion.",
):
    return client.post(
        f"/api/v1/orders/{order_id}/operation-report",
        headers={**_headers(login, key), "Content-Type": "application/json"},
        json={"category": category, "message": message},
    )


def test_client_creates_structured_operation_report_without_domain_side_effects() -> None:
    client = _client()
    _owner, business, ad, remitter, order = _seed_order(client, base_id=31000)
    stored_order = client.app.state.order_repository.get_by_id(order["id"])
    stored_order.status = "payment_confirmed"
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    before = {
        "order_status": stored_order.status,
        "ad_status": client.app.state.ad_repository.get_ad(ad["id"]).status,
        "wallet": (wallet.available_credits, wallet.blocked_credits, wallet.consumed_credits),
        "reservations": len(client.app.state.capacity_repository.reservations),
        "disputes": len(client.app.state.dispute_repository.disputes),
    }

    response = _create_operation_report(
        client,
        remitter,
        order["id"],
        key="structured_operation_report_success",
        category="payment_report_help",
    )

    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "private, no-store"
    data = response.json()["data"]
    ticket = data["ticket"]
    assert ticket["scope"] == "client_order"
    assert ticket["order_id"] == order["id"]
    assert "business_id" not in json.dumps(data)
    assert "report_kind" not in json.dumps(data)
    stored_ticket = client.app.state.support_repository.get_ticket(ticket["id"])
    assert stored_ticket.report_kind == "structured_operation_report"
    assert stored_ticket.order_id == order["id"]
    assert stored_ticket.business_id == business["id"]

    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert client.app.state.order_repository.get_by_id(order["id"]).status == before["order_status"]
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == before["ad_status"]
    assert (wallet_after.available_credits, wallet_after.blocked_credits, wallet_after.consumed_credits) == before["wallet"]
    assert len(client.app.state.capacity_repository.reservations) == before["reservations"]
    assert len(client.app.state.dispute_repository.disputes) == before["disputes"]


def test_structured_operation_report_enforces_ownership_states_and_strict_payload() -> None:
    reportable = {
        "payment_confirmed",
        "delivered",
        "completed",
        "payment_rejected",
        "disputed",
        "cancelled",
    }
    for index, status in enumerate(sorted(reportable)):
        client = _client()
        _owner, _business, _ad, remitter, order = _seed_order(client, base_id=32000 + index * 10)
        client.app.state.order_repository.get_by_id(order["id"]).status = status
        response = _create_operation_report(client, remitter, order["id"], key=f"reportable_{status}")
        assert response.status_code == 201, (status, response.text)

    for index, status in enumerate(("waiting_payment", "payment_reported", "expired")):
        client = _client()
        _owner, _business, _ad, remitter, order = _seed_order(client, base_id=33000 + index * 10)
        client.app.state.order_repository.get_by_id(order["id"]).status = status
        response = _create_operation_report(client, remitter, order["id"], key=f"not_reportable_{status}")
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "OPERATION_REPORT_NOT_ALLOWED"

    client = _client()
    _owner, business, _ad, remitter, order = _seed_order(client, base_id=34000)
    client.app.state.order_repository.get_by_id(order["id"]).status = "completed"
    other = _login(client, 34003, "structured_report_other_client")
    foreign = _create_operation_report(client, other, order["id"], key="structured_report_foreign")
    missing = _create_operation_report(client, remitter, "00000000-0000-0000-0000-000000000000", key="structured_report_missing")
    injected = client.post(
        f"/api/v1/orders/{order['id']}/operation-report",
        headers={**_headers(remitter, "structured_report_business_injection"), "Content-Type": "application/json"},
        json={"category": "order_help", "message": "Revision", "business_id": business["id"]},
    )
    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "ORDER_NOT_FOUND"
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "ORDER_NOT_FOUND"
    assert injected.status_code == 422


def test_structured_operation_report_is_idempotent_unique_and_hidden_from_business() -> None:
    client = _client()
    owner, business, _ad, remitter, order = _seed_order(client, base_id=35000)
    client.app.state.order_repository.get_by_id(order["id"]).status = "completed"
    first = _create_operation_report(client, remitter, order["id"], key="structured_report_replay")
    replay = _create_operation_report(client, remitter, order["id"], key="structured_report_replay")
    changed = _create_operation_report(
        client,
        remitter,
        order["id"],
        key="structured_report_replay",
        message="Contenido diferente.",
    )
    duplicate = _create_operation_report(client, remitter, order["id"], key="structured_report_other_key")

    assert first.status_code == 201, first.text
    assert replay.status_code == 201, replay.text
    assert replay.json()["data"]["ticket"]["id"] == first.json()["data"]["ticket"]["id"]
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "OPERATION_REPORT_DUPLICATE"
    assert len(client.app.state.support_repository.tickets) == 1

    business_list = client.get(
        "/api/v1/support/tickets",
        headers={**_bearer(owner, "structured_report_business_list"), "X-NODO-Surface": "business_mini_app"},
    )
    assert business_list.status_code == 200, business_list.text
    assert business_list.json()["data"]["items"] == []

    for telegram_id, role in ((35003, "admin"), (35004, "support")):
        staff = _make_admin(client, telegram_id, role)
        staff_detail = client.get(
            f"/api/v1/admin/support/tickets/{first.json()['data']['ticket']['id']}",
            headers=_bearer(staff, f"structured_report_{role}_detail"),
        )
        assert staff_detail.status_code == 200, staff_detail.text
        assert staff_detail.json()["data"]["business_id"] == business["id"]


def test_structured_operation_report_creates_private_hold_only_during_active_pause() -> None:
    client = _client()
    owner, business, _ad, remitter, order = _seed_order(client, base_id=35100)
    stored_order = client.app.state.order_repository.get_by_id(order["id"])
    stored_order.status = "completed"
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.ad_publication_paused_until = utc_now() + timedelta(minutes=15)

    active = _create_operation_report(
        client,
        remitter,
        order["id"],
        key="structured_report_active_hold",
    )

    assert active.status_code == 201, active.text
    active_payload = json.dumps(active.json()["data"]).lower()
    assert "hold" not in active_payload
    assert "business_id" not in active_payload
    holds = list(client.app.state.support_repository.publication_holds.values())
    assert len(holds) == 1
    assert holds[0].business_id == business["id"]
    assert holds[0].order_id == order["id"]
    assert holds[0].support_ticket_id == active.json()["data"]["ticket"]["id"]
    assert holds[0].status == "active"
    hold_events = [
        event
        for event in client.app.state.audit_writer.events
        if event.event_type == "business_publication_hold_started"
    ]
    assert len(hold_events) == 1
    serialized_event = json.dumps(hold_events[0].metadata_json).lower()
    for forbidden in ("rating", "stars", "message", "phone", "wallet", "account_value"):
        assert forbidden not in serialized_event

    client_detail = client.get(
        f"/api/v1/support/tickets/{active.json()['data']['ticket']['id']}",
        headers=_bearer(remitter, "structured_report_hold_client_detail"),
    )
    admin = _make_admin(client, 35103, "admin")
    admin_detail = client.get(
        f"/api/v1/admin/support/tickets/{active.json()['data']['ticket']['id']}",
        headers=_bearer(admin, "structured_report_hold_admin_detail"),
    )
    assert client_detail.status_code == 200, client_detail.text
    assert "publication_hold" not in client_detail.json()["data"]
    assert admin_detail.status_code == 200, admin_detail.text
    assert admin_detail.json()["data"]["publication_hold"]["id"] == holds[0].id

    business_list = client.get(
        "/api/v1/support/tickets",
        headers={**_bearer(owner, "structured_report_hold_business_list"), "X-NODO-Surface": "business_mini_app"},
    )
    assert business_list.status_code == 200, business_list.text
    assert business_list.json()["data"]["items"] == []

    second_client = _client()
    _owner, second_business, _ad, second_remitter, second_order = _seed_order(
        second_client,
        base_id=35200,
    )
    second_client.app.state.order_repository.get_by_id(second_order["id"]).status = "completed"
    second_client.app.state.business_repository.get_business(
        second_business["id"]
    ).ad_publication_paused_until = utc_now()
    expired = _create_operation_report(
        second_client,
        second_remitter,
        second_order["id"],
        key="structured_report_expired_pause",
    )
    assert expired.status_code == 201, expired.text
    assert second_client.app.state.support_repository.publication_holds == {}


def test_admin_release_publication_hold_is_explicit_idempotent_and_ticket_independent() -> None:
    client = _client()
    _owner, business, _ad, remitter, order = _seed_order(client, base_id=35300)
    client.app.state.order_repository.get_by_id(order["id"]).status = "completed"
    client.app.state.business_repository.get_business(
        business["id"]
    ).ad_publication_paused_until = utc_now() + timedelta(minutes=15)
    report = _create_operation_report(
        client,
        remitter,
        order["id"],
        key="structured_report_release",
    )
    hold = next(iter(client.app.state.support_repository.publication_holds.values()))
    admin = _make_admin(client, 35303, "admin")

    resolved = client.post(
        f"/api/v1/admin/support/tickets/{report.json()['data']['ticket']['id']}/resolve",
        headers=_headers(admin, "resolve_ticket_does_not_release_hold"),
        json={"reason": "Ticket revisado"},
    )
    assert resolved.status_code == 200, resolved.text
    assert client.app.state.support_repository.get_publication_hold(hold.id).status == "active"

    empty_reason = client.post(
        f"/api/v1/admin/business-publication-holds/{hold.id}/release",
        headers=_headers(admin, "hold_release_empty_reason"),
        json={"reason": ""},
    )
    assert empty_reason.status_code == 422

    first = client.post(
        f"/api/v1/admin/business-publication-holds/{hold.id}/release",
        headers=_headers(admin, "hold_release_replay"),
        json={"reason": "Revision administrativa completada"},
    )
    replay = client.post(
        f"/api/v1/admin/business-publication-holds/{hold.id}/release",
        headers=_headers(admin, "hold_release_replay"),
        json={"reason": "Revision administrativa completada"},
    )
    changed = client.post(
        f"/api/v1/admin/business-publication-holds/{hold.id}/release",
        headers=_headers(admin, "hold_release_replay"),
        json={"reason": "Carga diferente"},
    )

    assert first.status_code == 200, first.text
    assert first.headers["cache-control"] == "private, no-store"
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"] == first.json()["data"]
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"
    assert client.app.state.support_repository.get_publication_hold(hold.id).status == "released"
    release_events = [
        event
        for event in client.app.state.audit_writer.events
        if event.event_type == "business_publication_hold_released"
    ]
    assert len(release_events) == 1

    forbidden = client.post(
        f"/api/v1/admin/business-publication-holds/{hold.id}/release",
        headers=_headers(remitter, "hold_release_client_forbidden"),
        json={"reason": "No autorizado"},
    )
    missing = client.post(
        f"/api/v1/admin/business-publication-holds/{uuid4()}/release",
        headers=_headers(admin, "hold_release_missing"),
        json={"reason": "No existe"},
    )
    support = _make_admin(client, 35304, "support")
    support_forbidden = client.post(
        f"/api/v1/admin/business-publication-holds/{hold.id}/release",
        headers=_headers(support, "hold_release_support_forbidden"),
        json={"reason": "No tiene permiso durable"},
    )
    assert forbidden.status_code == 403
    assert support_forbidden.status_code == 403
    assert missing.status_code == 404


def test_releasing_one_of_multiple_business_holds_keeps_business_under_review() -> None:
    client = _client()
    _owner, business, _ad, remitter, order = _seed_order(client, base_id=35400)
    client.app.state.order_repository.get_by_id(order["id"]).status = "completed"
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.ad_publication_paused_until = utc_now() + timedelta(minutes=15)
    first_report = _create_operation_report(client, remitter, order["id"], key="first_business_hold")
    closed = client.post(
        f"/api/v1/support/tickets/{first_report.json()['data']['ticket']['id']}/close",
        headers=_headers(remitter, "close_ticket_keeps_hold"),
    )
    assert closed.status_code == 200, closed.text
    assert client.app.state.support_repository.has_active_publication_hold(business["id"])

    _other_owner, _other_business, _other_ad, second_remitter, second_order = _seed_order(
        client,
        base_id=35500,
    )
    second_stored_order = client.app.state.order_repository.get_by_id(second_order["id"])
    second_stored_order.status = "completed"
    second_stored_order.business_id = business["id"]
    _create_operation_report(client, second_remitter, second_order["id"], key="second_business_hold")

    holds = list(client.app.state.support_repository.publication_holds.values())
    assert len(holds) == 2
    admin = _make_admin(client, 35403, "super_admin")
    released = client.post(
        f"/api/v1/admin/business-publication-holds/{holds[0].id}/release",
        headers=_headers(admin, "release_one_of_multiple_holds"),
        json={"reason": "Primer caso revisado"},
    )
    assert released.status_code == 200, released.text
    assert client.app.state.support_repository.has_active_publication_hold(business["id"])
    released_second = client.post(
        f"/api/v1/admin/business-publication-holds/{holds[1].id}/release",
        headers=_headers(admin, "release_second_business_hold"),
        json={"reason": "Segundo caso revisado"},
    )
    assert released_second.status_code == 200, released_second.text
    assert not client.app.state.support_repository.has_active_publication_hold(business["id"])


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
    listed_ticket = next(item for item in listed.json()["data"]["items"] if item["id"] == ticket["id"])
    assert listed_ticket["business_name"] == business["business_name"]

    detail = client.get(f"/api/v1/admin/support/tickets/{ticket['id']}", headers=_bearer(support, "support_admin_detail"))
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["business_name"] == business["business_name"]

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
    assert response.json()["data"]["ticket"]["business_name"] == business["business_name"]

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

    support_close = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/close",
        headers={**_headers(support, "support_close"), "Content-Type": "application/json"},
        json={"reason": "Caso cerrado"},
    )
    assert support_close.status_code == 403

    closed = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/close",
        headers={**_headers(admin, "admin_close"), "Content-Type": "application/json"},
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


def test_admin_support_replies_notify_each_participant_once_without_private_content() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner, business, _, remitter, _ = _seed_order(client, base_id=20100)
    admin = _make_admin(client, 20103, "admin")
    client_ticket = _create_ticket(
        client,
        remitter,
        scope="client_general",
        key="slice48b1_client_ticket",
    )
    business_ticket = _create_ticket(
        client,
        owner,
        scope="business_general",
        key="slice48b1_business_ticket",
        business_id=business["id"],
    )

    client_reply_headers = {
        **_headers(admin, "slice48b1_client_admin_reply"),
        "Content-Type": "application/json",
    }
    client_reply_payload = {
        "body": "PRIVATE_SUPPORT_REPLY_BODY_48B1",
        "visibility": "participants",
    }
    first = client.post(
        f"/api/v1/admin/support/tickets/{client_ticket['id']}/messages",
        headers=client_reply_headers,
        json=client_reply_payload,
    )
    replay = client.post(
        f"/api/v1/admin/support/tickets/{client_ticket['id']}/messages",
        headers=client_reply_headers,
        json=client_reply_payload,
    )
    assert first.status_code == 201, first.text
    assert replay.status_code == 201, replay.text

    business_reply = client.post(
        f"/api/v1/admin/support/tickets/{business_ticket['id']}/messages",
        headers={**_headers(admin, "slice48b1_business_admin_reply"), "Content-Type": "application/json"},
        json={"body": "PRIVATE_BUSINESS_SUPPORT_REPLY_48B1", "visibility": "participants"},
    )
    assert business_reply.status_code == 201, business_reply.text

    participant_jobs = [
        job
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.notification_type == "support_message_created_participant"
    ]
    assert len(participant_jobs) == 2
    client_job = next(job for job in participant_jobs if job.recipient_user_id == remitter["user"]["id"])
    business_job = next(job for job in participant_jobs if job.recipient_user_id == owner["user"]["id"])
    assert client_job.metadata_json["target_surface"] == "client_mini_app"
    assert client_job.metadata_json["action_url"].endswith(
        f"/?view=support&ticket_id={client_ticket['id']}"
    )
    assert business_job.metadata_json["target_surface"] == "business_mini_app"
    assert business_job.metadata_json["action_url"].endswith(
        f"/business/?view=business-support&ticket_id={business_ticket['id']}"
    )
    serialized = json.dumps([job.__dict__ for job in participant_jobs], default=str)
    assert "PRIVATE_SUPPORT_REPLY_BODY_48B1" not in serialized
    assert "PRIVATE_BUSINESS_SUPPORT_REPLY_48B1" not in serialized
    assert "storage_path" not in serialized
    assert "file_asset_id" not in serialized
    assert "signed_url" not in serialized

    participant_reply = client.post(
        f"/api/v1/support/tickets/{client_ticket['id']}/messages",
        headers={**_headers(remitter, "slice48b1_participant_reply"), "Content-Type": "application/json"},
        json={"body": "Respuesta del participante"},
    )
    assert participant_reply.status_code == 201, participant_reply.text
    assert len(
        [
            job
            for job in client.app.state.job_repository.notification_jobs.values()
            if job.notification_type == "support_message_created_participant"
        ]
    ) == 2
    assert any(
        notification.notification_type == "client_support_message_created"
        for notification in client.app.state.admin_notification_repository.notifications.values()
    )


def test_resolved_and_closed_support_tickets_are_read_only_and_preserve_evidence() -> None:
    client = _client()
    _owner, _business, _ad, remitter, _order = _seed_order(client, base_id=26000)
    ticket = _create_ticket(client, remitter, scope="client_general", key="archived_read_only")
    admin = _make_admin(client, 26003, "admin")

    uploaded = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/attachments",
        headers=_headers(remitter, "archived_evidence_attachment"),
        files={"file": ("evidence.png", png_bytes(b"safe-evidence"), "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    evidence_message_id = uploaded.json()["data"]["message"]["id"]

    resolved_headers = {**_headers(admin, "archive_resolve"), "Content-Type": "application/json"}
    resolved = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/resolve",
        headers=resolved_headers,
        json={"reason": "Caso atendido"},
    )
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["data"]["status"] == "resolved"

    replay = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/resolve",
        headers=resolved_headers,
        json={"reason": "Caso atendido"},
    )
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"]["status"] == "resolved"

    user_reply = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/messages",
        headers={**_headers(remitter, "resolved_user_reply"), "Content-Type": "application/json"},
        json={"body": "No debe reabrir el ticket."},
    )
    assert user_reply.status_code == 400

    admin_reply = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/messages",
        headers={**_headers(admin, "resolved_admin_reply"), "Content-Type": "application/json"},
        json={"body": "Tampoco debe reabrirlo.", "visibility": "participants"},
    )
    assert admin_reply.status_code == 400

    user_attachment = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/attachments",
        headers=_headers(remitter, "resolved_user_attachment"),
        files={"file": ("late.png", b"late-evidence", "image/png")},
    )
    assert user_attachment.status_code == 400

    invalid_escalation = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/escalate",
        headers={**_headers(admin, "resolved_escalate"), "Content-Type": "application/json"},
        json={"reason": "No debe reabrir"},
    )
    assert invalid_escalation.status_code == 400

    invalid_assignment = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/assign",
        headers={**_headers(admin, "resolved_assign"), "Content-Type": "application/json"},
        json={"assigned_support_user_id": admin["user"]["id"], "reason": "No debe modificar archivados"},
    )
    assert invalid_assignment.status_code == 400

    closed = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/close",
        headers={**_headers(admin, "archive_close"), "Content-Type": "application/json"},
        json={"reason": "Cierre definitivo"},
    )
    assert closed.status_code == 200, closed.text
    assert closed.json()["data"]["status"] == "closed"

    closed_reply = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/messages",
        headers={**_headers(admin, "closed_admin_reply"), "Content-Type": "application/json"},
        json={"body": "No debe aceptar mensajes.", "visibility": "participants"},
    )
    assert closed_reply.status_code == 400

    detail = client.get(
        f"/api/v1/support/tickets/{ticket['id']}",
        headers=_bearer(remitter, "archived_evidence_detail"),
    )
    assert detail.status_code == 200, detail.text
    messages = detail.json()["data"]["messages"]
    evidence_message = next(message for message in messages if message["id"] == evidence_message_id)
    assert len(evidence_message["attachments"]) == 1
    assert evidence_message["attachments"][0]["mime_type"] == "image/png"


def test_requesters_can_close_only_their_own_active_support_tickets() -> None:
    client = _client()
    owner, _business, _ad, remitter, order = _seed_order(client, base_id=27000)
    other = _login(client, 27003, "other_requester_close")
    client_ticket = _create_ticket(client, remitter, scope="client_general", key="client_requester_close")
    business_ticket = _create_ticket(client, owner, scope="business_general", key="business_requester_close")
    client_order_ticket = _create_ticket(
        client,
        remitter,
        scope="client_order",
        key="client_order_requester_close",
        order_id=order["id"],
    )
    business_order_ticket = _create_ticket(
        client,
        owner,
        scope="business_order",
        key="business_order_requester_close",
        order_id=order["id"],
    )

    cross_close = client.post(
        f"/api/v1/support/tickets/{client_ticket['id']}/close",
        headers=_headers(other, "cross_requester_close"),
    )
    assert cross_close.status_code == 404

    business_cannot_close_client_ticket = client.post(
        f"/api/v1/support/tickets/{client_order_ticket['id']}/close",
        headers=_headers(owner, "business_cannot_close_client_ticket"),
    )
    assert business_cannot_close_client_ticket.status_code == 404

    client_cannot_close_business_ticket = client.post(
        f"/api/v1/support/tickets/{business_order_ticket['id']}/close",
        headers=_headers(remitter, "client_cannot_close_business_ticket"),
    )
    assert client_cannot_close_business_ticket.status_code == 404

    client_close = client.post(
        f"/api/v1/support/tickets/{client_ticket['id']}/close",
        headers=_headers(remitter, "client_requester_close_apply"),
    )
    assert client_close.status_code == 200, client_close.text
    assert client_close.json()["data"]["status"] == "closed"

    business_close = client.post(
        f"/api/v1/support/tickets/{business_ticket['id']}/close",
        headers=_headers(owner, "business_requester_close_apply"),
    )
    assert business_close.status_code == 200, business_close.text
    assert business_close.json()["data"]["status"] == "closed"

    archived = client.get(
        "/api/v1/support/tickets?status=closed",
        headers=_bearer(remitter, "client_requester_archived"),
    )
    assert archived.status_code == 200, archived.text
    assert client_ticket["id"] in {item["id"] for item in archived.json()["data"]["items"]}

    business_archived = client.get(
        "/api/v1/support/tickets?status=closed",
        headers=_bearer(owner, "business_requester_archived"),
    )
    assert business_archived.status_code == 200, business_archived.text
    assert business_ticket["id"] in {item["id"] for item in business_archived.json()["data"]["items"]}

    admin = _make_admin(client, 27004, "admin")
    admin_archived = client.get(
        "/api/v1/admin/support/tickets?status=closed",
        headers=_bearer(admin, "admin_requester_archived"),
    )
    assert admin_archived.status_code == 200, admin_archived.text
    archived_ids = {item["id"] for item in admin_archived.json()["data"]["items"]}
    assert {client_ticket["id"], business_ticket["id"]} <= archived_ids

    second_close = client.post(
        f"/api/v1/support/tickets/{client_ticket['id']}/close",
        headers=_headers(remitter, "client_requester_close_again"),
    )
    assert second_close.status_code == 400


def test_support_status_groups_are_filtered_before_the_first_50_for_all_surfaces() -> None:
    client = _client()
    owner, business, _ad, remitter, _order = _seed_order(client, base_id=27500)
    admin = _make_admin(client, 27503, "admin")
    client_archived = _seed_repository_ticket(
        client,
        requester=remitter,
        status="resolved",
        subject="Client archived outside mixed first page",
    )
    business_archived = _seed_repository_ticket(
        client,
        requester=owner,
        status="closed",
        subject="Business archived outside mixed first page",
        business_id=business["id"],
        scope="business_general",
    )
    for index in range(50):
        _seed_repository_ticket(
            client,
            requester=remitter,
            status="open",
            subject=f"Client active {index}",
        )
        _seed_repository_ticket(
            client,
            requester=owner,
            status="waiting_support",
            subject=f"Business active {index}",
            business_id=business["id"],
            scope="business_general",
        )

    client_response = client.get(
        "/api/v1/support/tickets?status_group=archived&limit=50",
        headers=_bearer(remitter, "client_archived_group"),
    )
    assert client_response.status_code == 200, client_response.text
    assert [item["id"] for item in client_response.json()["data"]["items"]] == [client_archived["id"]]

    business_response = client.get(
        "/api/v1/support/tickets?status_group=archived&limit=50",
        headers=_bearer(owner, "business_archived_group"),
    )
    assert business_response.status_code == 200, business_response.text
    assert [item["id"] for item in business_response.json()["data"]["items"]] == [business_archived["id"]]

    admin_response = client.get(
        "/api/v1/admin/support/tickets?status_group=archived&limit=50",
        headers=_bearer(admin, "admin_archived_group"),
    )
    assert admin_response.status_code == 200, admin_response.text
    assert {item["id"] for item in admin_response.json()["data"]["items"]} == {
        client_archived["id"],
        business_archived["id"],
    }

    client_active = client.get(
        "/api/v1/support/tickets?status_group=active&limit=50",
        headers=_bearer(remitter, "client_active_group"),
    )
    assert client_active.status_code == 200, client_active.text
    assert len(client_active.json()["data"]["items"]) == 50
    assert all(item["status"] in ACTIVE_SUPPORT_STATUSES for item in client_active.json()["data"]["items"])
    assert client_active.json()["data"]["next_cursor"] is None

    invalid_group = client.get(
        "/api/v1/support/tickets?status_group=unknown",
        headers=_bearer(remitter, "invalid_status_group"),
    )
    assert invalid_group.status_code == 400
    assert invalid_group.json()["error"]["code"] == "SUPPORT_TICKET_STATUS_GROUP_INVALID"

    conflicting_filters = client.get(
        "/api/v1/admin/support/tickets?status=closed&status_group=active",
        headers=_bearer(admin, "conflicting_status_filters"),
    )
    assert conflicting_filters.status_code == 400
    assert conflicting_filters.json()["error"]["code"] == "SUPPORT_TICKET_STATUS_FILTER_CONFLICT"


def test_postgres_support_status_group_is_applied_before_limit(monkeypatch) -> None:
    captured: dict = {}

    class FakeCursor:
        def fetchall(self) -> list:
            return []

    class FakeConnection:
        def execute(self, sql: str, params: list) -> FakeCursor:
            captured["sql"] = sql
            captured["params"] = params
            return FakeCursor()

    class FakeConnectionContext:
        def __enter__(self) -> FakeConnection:
            return FakeConnection()

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

    repository = PostgresSupportRepository("postgresql://unused")
    monkeypatch.setattr(repository, "_connect", lambda: FakeConnectionContext())

    repository.list_tickets(
        requester_user_id=None,
        business_id=None,
        statuses=ACTIVE_SUPPORT_STATUSES,
        scope=None,
        category=None,
        priority=None,
        assigned_support_user_id=None,
        cursor=None,
        limit=50,
    )

    normalized_sql = " ".join(captured["sql"].split())
    assert "status = any(%s)" in normalized_sql
    assert normalized_sql.index("status = any(%s)") < normalized_sql.index("order by updated_at desc, id desc limit %s")
    assert set(captured["params"][0]) == ACTIVE_SUPPORT_STATUSES
    assert captured["params"][-1] == 51


def test_support_resolution_notifications_are_deduped_and_safe() -> None:
    client = _client()
    _owner, _business, _ad, remitter, _order = _seed_order(client, base_id=28000)
    ticket = _create_ticket(client, remitter, scope="client_general", key="safe_resolution_notice")
    admin = _make_admin(client, 28003, "admin")

    resolved = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/resolve",
        headers={**_headers(admin, "safe_resolution_notice_apply"), "Content-Type": "application/json"},
        json={"reason": "Contenido privado que no debe entrar en la notificacion"},
    )
    assert resolved.status_code == 200, resolved.text

    closed = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/close",
        headers={**_headers(admin, "safe_close_notice_apply"), "Content-Type": "application/json"},
        json={"reason": "Otro contenido privado"},
    )
    assert closed.status_code == 200, closed.text

    participant_jobs = [
        job
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.notification_type in {"support_ticket_resolved_participant", "support_ticket_closed_participant"}
    ]
    assert {job.notification_type for job in participant_jobs} == {
        "support_ticket_resolved_participant",
        "support_ticket_closed_participant",
    }
    assert all(job.recipient_user_id == remitter["user"]["id"] for job in participant_jobs)
    assert len({job.dedupe_key for job in participant_jobs}) == 2
    serialized = json.dumps([job.__dict__ for job in participant_jobs], default=str).lower()
    assert "contenido privado" not in serialized
    assert "storage_path" not in serialized
    assert "signed_url" not in serialized
    assert "account_value" not in serialized
    assert "attachment" not in serialized


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


def test_admin_support_assignment_ui_uses_existing_active_staff_contract() -> None:
    root = Path(__file__).resolve().parents[3]
    support_model = (root / "apps/web/src/hooks/admin-web/useAdminSupportModel.ts").read_text(encoding="utf-8")
    admin_model = (root / "apps/web/src/hooks/useAdminWebModel.ts").read_text(encoding="utf-8")
    support_screen = (root / "apps/web/src/screens/admin-web/AdminSupportScreens.tsx").read_text(encoding="utf-8")

    assert "adminAssignSupportTicket" in support_model
    assert "listAdminStaff" in support_model
    assert 'status: "active", limit: 50' in support_model
    assert 'new Set(["support_agent", "support_lead", "admin", "super_admin"])' in support_model
    assert "operations_readonly" not in support_model.split("ASSIGNABLE_STAFF_ROLES", 1)[1].split(");", 1)[0]
    assert "supportAssignmentReason" in support_model
    assert "assigningSupportTicketId" in support_model
    assert "supportAssignmentInFlight" in support_model
    assert "getIdempotencyKey" in support_model
    assert "clearIdempotencyKey" in support_model
    assert "adminMutable" in support_model
    assert "assignSupportTicket: support.assignSupportTicket" in admin_model
    assert "Cargar responsables" in support_screen
    assert "Motivo breve" in support_screen
    assert "Asignando..." in support_screen
    assert "model.adminMutable" in support_screen
    assert "assigned_support_user_id" not in support_screen
    assert "Asignar a user id support" not in support_screen


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
        files={"file": ("proof.png", png_bytes(b"support-proof"), "image/png")},
    )
    assert valid.status_code == 201, valid.text
    upload_payload = valid.json()["data"]
    file_id = upload_payload["attachment"]["id"]
    assert upload_payload["message"]["body"] == "Adjunto enviado."
    assert upload_payload["message"]["attachments"][0]["id"] == file_id
    assert upload_payload["message"]["attachments"][0]["resource_type"] == "support_message"

    user_detail = client.get(f"/api/v1/support/tickets/{ticket['id']}", headers=_bearer(remitter, "support_attachment_user_detail"))
    assert user_detail.status_code == 200, user_detail.text
    assert user_detail.json()["data"]["messages"][-1]["attachments"][0]["id"] == file_id

    admin_detail = client.get(f"/api/v1/admin/support/tickets/{ticket['id']}", headers=_bearer(support, "support_attachment_admin_detail"))
    assert admin_detail.status_code == 200, admin_detail.text
    assert admin_detail.json()["data"]["messages"][-1]["attachments"][0]["id"] == file_id

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
    assert view_url.json()["data"]["download_filename"].startswith("nodo-support-")
    assert view_url.json()["data"]["download_filename"].endswith(".png")
    combined = valid.text + view_url.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert signed_url not in json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "support_attachment_uploaded" in _events(client)
    assert "support_message_created" in _events(client)
    assert "support_attachment_viewed" in _events(client)


@pytest.mark.parametrize(
    ("image_format", "mime_type", "expected_extension"),
    [
        ("JPEG", "image/jpeg", ".jpg"),
        ("PNG", "image/png", ".png"),
        ("WEBP", "image/webp", ".webp"),
    ],
)
def test_support_attachment_accepts_only_decodable_supported_photos(
    image_format: str,
    mime_type: str,
    expected_extension: str,
) -> None:
    client = _client()
    _owner, _business, _ad, remitter, order = _seed_order(client, base_id=26100)
    ticket = _create_ticket(client, remitter, scope="client_order", key=f"valid_support_{image_format.lower()}", order_id=order["id"])

    accepted = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/attachments",
        headers=_headers(remitter, f"valid_support_photo_{image_format.lower()}"),
        files={
            "file": (
                f"photo.{image_format.lower()}",
                photo_bytes(image_format, image_format.encode("ascii")),
                mime_type,
            )
        },
    )

    assert accepted.status_code == 201, accepted.text
    assert accepted.json()["data"]["attachment"]["mime_type"] == mime_type
    file_id = accepted.json()["data"]["attachment"]["id"]
    assert client.app.state.support_repository.files[file_id].storage_path.endswith(expected_extension)


@pytest.mark.parametrize(
    ("file_name", "content", "declared_mime", "error_code"),
    [
        ("proof.png", b"proof", "image/png", "SUPPORT_ATTACHMENT_INVALID"),
        ("photo.jpg", b"<html><script>alert(1)</script></html>", "image/jpeg", "SUPPORT_ATTACHMENT_INVALID"),
        ("document.pdf", b"%PDF-1.7", "application/pdf", "SUPPORT_ATTACHMENT_TYPE_NOT_ALLOWED"),
        ("document.jpg", b"%PDF-1.7", "image/jpeg", "SUPPORT_ATTACHMENT_INVALID"),
        ("corrupt.webp", b"RIFF-corrupt-webp", "image/webp", "SUPPORT_ATTACHMENT_INVALID"),
        ("photo.jpg", png_bytes(b"mismatched-support-photo"), "image/jpeg", "SUPPORT_ATTACHMENT_INVALID"),
    ],
)
def test_support_attachment_rejects_disguised_or_invalid_files_without_persisting(
    file_name: str,
    content: bytes,
    declared_mime: str,
    error_code: str,
) -> None:
    client = _client()
    _owner, _business, _ad, remitter, order = _seed_order(client, base_id=26200)
    ticket = _create_ticket(client, remitter, scope="client_order", key="invalid_support_attachment", order_id=order["id"])

    rejected = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/attachments",
        headers=_headers(remitter, f"reject_support_{error_code.lower()}"),
        files={"file": (file_name, content, declared_mime)},
    )

    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == error_code
    assert rejected.json()["error"]["message"] == "No pudimos aceptar ese archivo. Usa una imagen valida."
    assert client.app.state.support_repository.files == {}
    assert not any(path.startswith(f"private/support/{ticket['id']}/") for path in client.app.state.private_storage._objects)


def test_support_list_rejects_invalid_cursor_with_400() -> None:
    client = _client()
    remitter = _login(client, 26300, "support_cursor_invalid")

    response = client.get(
        "/api/v1/support/tickets?cursor=not-a-cursor",
        headers=_bearer(remitter, "support_cursor_invalid"),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PAGINATION_CURSOR_INVALID"


def test_support_list_rejects_structurally_valid_cursor_with_non_uuid_id() -> None:
    client = _client()
    remitter = _login(client, 26301, "support_cursor_invalid_uuid")
    cursor = encode_keyset_cursor(utc_now(), "not-a-uuid")

    response = client.get(
        "/api/v1/support/tickets",
        params={"cursor": cursor},
        headers=_bearer(remitter, "support_cursor_invalid_uuid"),
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "PAGINATION_CURSOR_INVALID"
    assert "not-a-uuid" not in response.text


def test_support_detail_pages_large_tied_message_history_without_leaks_or_duplicates() -> None:
    client = _client()
    _owner, _business, _ad, remitter, order = _seed_order(client, base_id=26400)
    ticket = _create_ticket(client, remitter, scope="client_order", key="paged_support_detail", order_id=order["id"])
    repository = client.app.state.support_repository
    tied_at = utc_now() - timedelta(hours=1)

    created_ids = {ticket["messages"][0]["id"]}
    for index in range(124):
        message = repository.create_message(
            ticket_id=ticket["id"],
            sender_user_id=remitter["user"]["id"],
            sender_role="remitter",
            body=f"Mensaje historico {index + 1}",
            visibility="participants",
        )
        message.created_at = tied_at
        message.updated_at = tied_at
        created_ids.add(message.id)

    oldest_message_id = min(created_ids)
    old_file = repository.create_file_asset(
        file_id=str(uuid4()),
        owner_user_id=remitter["user"]["id"],
        resource_type="support_message",
        resource_id=oldest_message_id,
        storage_path=f"private/support/{ticket['id']}/old.png",
        mime_type="image/png",
        size_bytes=128,
    )

    seen: list[str] = []
    cursor: str | None = None
    first_payload: dict | None = None
    for page_number in range(10):
        params = {"messages_limit": 25}
        if cursor:
            params["messages_cursor"] = cursor
        response = client.get(
            f"/api/v1/support/tickets/{ticket['id']}",
            params=params,
            headers=_bearer(remitter, f"paged_support_detail_{page_number}"),
        )
        assert response.status_code == 200, response.text
        payload = response.json()["data"]
        if first_payload is None:
            first_payload = payload
            assert len(payload["messages"]) == 25
            assert old_file.id not in response.text
        page_ids = [item["id"] for item in payload["messages"]]
        assert len(page_ids) == len(set(page_ids))
        assert not set(page_ids).intersection(seen)
        seen.extend(page_ids)
        cursor = payload["messages_next_cursor"]
        if cursor is None:
            break

    assert first_payload is not None
    assert set(seen) == created_ids
    assert len(seen) == 125

    invalid_cursor = client.get(
        f"/api/v1/support/tickets/{ticket['id']}",
        params={"messages_cursor": "not-a-cursor"},
        headers=_bearer(remitter, "invalid_support_detail_cursor"),
    )
    assert invalid_cursor.status_code == 400
    assert invalid_cursor.json()["error"]["code"] == "PAGINATION_CURSOR_INVALID"


def test_admin_support_detail_limits_events_and_attachment_view_does_not_scan_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client = _client()
    _owner, _business, _ad, remitter, order = _seed_order(client, base_id=26500)
    ticket = _create_ticket(client, remitter, scope="client_order", key="paged_admin_detail", order_id=order["id"])
    support = _make_admin(client, 26503, "support")
    repository = client.app.state.support_repository
    tied_at = utc_now() - timedelta(minutes=30)

    for index in range(120):
        event = repository.create_event(
            ticket_id=ticket["id"],
            actor_user_id=support["user"]["id"],
            actor_role="support",
            event_type="support_message_created",
            metadata_json={"sequence": index},
        )
        event.created_at = tied_at

    upload = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/attachments",
        headers=_headers(remitter, "paged_support_attachment"),
        files={"file": ("proof.png", png_bytes(b"paged-support-proof"), "image/png")},
    )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["data"]["attachment"]["id"]
    other_ticket = _create_ticket(client, remitter, scope="client_general", key="other_paged_attachment")
    other_upload = client.post(
        f"/api/v1/support/tickets/{other_ticket['id']}/attachments",
        headers=_headers(remitter, "other_paged_support_attachment"),
        files={"file": ("other.png", png_bytes(b"other-paged-support-proof"), "image/png")},
    )
    assert other_upload.status_code == 201, other_upload.text
    other_file_id = other_upload.json()["data"]["attachment"]["id"]

    detail = client.get(
        f"/api/v1/admin/support/tickets/{ticket['id']}",
        params={"messages_limit": 25, "events_limit": 25},
        headers=_bearer(support, "paged_admin_support_detail"),
    )
    assert detail.status_code == 200, detail.text
    assert len(detail.json()["data"]["events"]) == 25
    assert detail.json()["data"]["events_next_cursor"] is not None

    seen_events: list[str] = []
    events_cursor: str | None = None
    for page_number in range(10):
        params = {"events_limit": 25}
        if events_cursor:
            params["events_cursor"] = events_cursor
        events_page = client.get(
            f"/api/v1/admin/support/tickets/{ticket['id']}",
            params=params,
            headers=_bearer(support, f"paged_admin_support_events_{page_number}"),
        )
        assert events_page.status_code == 200, events_page.text
        events_data = events_page.json()["data"]
        page_ids = [item["id"] for item in events_data["events"]]
        assert not set(page_ids).intersection(seen_events)
        seen_events.extend(page_ids)
        events_cursor = events_data["events_next_cursor"]
        if events_cursor is None:
            break
    assert len(seen_events) == 123
    assert len(seen_events) == len(set(seen_events))

    invalid_events_cursor = client.get(
        f"/api/v1/admin/support/tickets/{ticket['id']}",
        params={"events_cursor": "not-a-cursor"},
        headers=_bearer(support, "invalid_admin_support_events_cursor"),
    )
    assert invalid_events_cursor.status_code == 400
    assert invalid_events_cursor.json()["error"]["code"] == "PAGINATION_CURSOR_INVALID"

    monkeypatch.setattr(
        repository,
        "list_messages_page",
        lambda **_kwargs: pytest.fail("attachment authorization scanned the complete support thread"),
    )
    view_url = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/attachments/{file_id}/view-url",
        headers={**_bearer(support, "paged_support_view_url"), "Content-Type": "application/json"},
        json={"reason": "Validar adjunto acotado"},
    )
    assert view_url.status_code == 200, view_url.text
    cross_ticket_view = client.post(
        f"/api/v1/admin/support/tickets/{ticket['id']}/attachments/{other_file_id}/view-url",
        headers={**_bearer(support, "cross_paged_support_view_url"), "Content-Type": "application/json"},
        json={"reason": "No debe cruzar tickets"},
    )
    assert cross_ticket_view.status_code == 403
    assert cross_ticket_view.json()["error"]["code"] == "SUPPORT_ATTACHMENT_ACCESS_DENIED"
