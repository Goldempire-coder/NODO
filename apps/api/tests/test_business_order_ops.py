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
        "APP_VERSION": "0.0.0-slice-06",
        "NODO_BUILD_ID": "pytest-business-order-ops-build",
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


def _headers(login: dict, key: str = "idem") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _bearer(login: dict, key: str = "req") -> dict[str, str]:
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
    stored_business.max_order_amount_usd = stored_business.max_order_amount_usd * 20
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


def _upload_evidence(client: TestClient, remitter: dict, order_id: str, key: str = "evidence") -> dict:
    response = client.post(
        f"/api/v1/orders/{order_id}/payment-evidence",
        headers=_headers(remitter, key),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", b"proof", "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _report_payment(client: TestClient, remitter: dict, order: dict, *, key: str = "report") -> dict:
    evidence = _upload_evidence(client, remitter, order["id"], key=f"{key}_evidence")
    response = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={**_headers(remitter, key), "Content-Type": "application/json"},
        json={
            "payment_type": "zelle",
            "payment_reference": "ABC123456",
            "payment_sender_name": "Remitter Test",
            "payment_sender_account_masked": "***1234",
            "payment_amount": "50.00",
            "proof_file_id": evidence["file"]["id"],
            "pending_payment_report_id": evidence["pending_payment_report_id"],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _seed_reported_order(client: TestClient, *, owner_id: int = 700, remitter_id: int = 701) -> tuple[dict, dict, dict, dict, dict]:
    owner = _login(client, owner_id, f"owner_{owner_id}")
    business, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key=f"ad_{owner_id}")
    remitter = _login(client, remitter_id, f"remitter_{remitter_id}")
    order = _create_order(client, remitter, ad["id"], key=f"order_{remitter_id}")
    _report_payment(client, remitter, order, key=f"report_{remitter_id}")
    return owner, business, ad, remitter, order


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_business_list_detail_only_own_and_guest_blocked() -> None:
    client = _client()
    owner, _, _, _, order = _seed_reported_order(client)
    other_owner, _, _, _, _ = _seed_reported_order(client, owner_id=702, remitter_id=703)
    guest = _login(client, 704, "guest")

    listing = client.get("/api/v1/business/orders?limit=20", headers=_bearer(owner, "req_business_orders"))
    detail = client.get(f"/api/v1/business/orders/{order['id']}", headers=_bearer(owner, "req_business_order_detail"))
    foreign = client.get(f"/api/v1/business/orders/{order['id']}", headers=_bearer(other_owner, "req_business_order_foreign"))
    guest_list = client.get("/api/v1/business/orders", headers=_bearer(guest, "req_guest_business_orders"))

    assert listing.status_code == 200, listing.text
    assert len(listing.json()["data"]["items"]) == 1
    assert detail.status_code == 200, detail.text
    detail_data = detail.json()["data"]
    assert detail_data["receiver_data"]["phone_masked"] == "***4567"
    assert detail_data["receiver_data"]["document_masked"] == "***5678"
    assert "receiver_data" not in detail_data["order"]
    assert "+584121234567" not in detail.text
    assert "V12345678" not in detail.text
    assert "storage_path" not in detail.text
    assert "owner@example.com" not in detail.text
    assert "account_value" not in detail.text
    assert foreign.status_code == 404
    assert guest_list.status_code == 403


def test_business_orders_history_filter_and_public_order_code_for_claims() -> None:
    client = _client()
    owner, _, _, _, order = _seed_reported_order(client, owner_id=705, remitter_id=706)
    confirm = client.post(
        f"/api/v1/business/orders/{order['id']}/confirm-payment",
        headers={**_headers(owner, "confirm_for_history"), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )
    assert confirm.status_code == 200, confirm.text
    delivered = client.post(
        f"/api/v1/business/orders/{order['id']}/mark-delivered",
        headers={**_headers(owner, "deliver_for_history"), "Content-Type": "application/json"},
        json={"reason": "Pago movil enviado"},
    )
    assert delivered.status_code == 200, delivered.text

    history = client.get("/api/v1/business/orders?status=history&limit=20", headers=_bearer(owner, "req_business_orders_history"))
    completed = client.get("/api/v1/business/orders?status=completed&limit=20", headers=_bearer(owner, "req_business_orders_completed"))

    assert history.status_code == 200, history.text
    assert completed.status_code == 200, completed.text
    history_items = history.json()["data"]["items"]
    assert [item["public_order_code"] for item in history_items] == [order["public_order_code"]]
    assert history_items[0]["status"] == "delivered"


def test_business_offline_hides_marketplace_ad_and_blocks_direct_order_creation() -> None:
    client = _client()
    owner = _login(client, 707, "owner_707")
    business, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key="ad_offline")
    remitter = _login(client, 708, "remitter_708")

    before = client.get("/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&limit=20", headers=_bearer(remitter, "req_ads_before_offline"))
    assert before.status_code == 200, before.text
    assert ad["id"] in {item["id"] for item in before.json()["data"]["items"]}

    offline = client.patch(
        "/api/v1/business/availability",
        headers={**_headers(owner, "req_business_offline"), "Content-Type": "application/json"},
        json={"accepting_orders": False},
    )
    assert offline.status_code == 200, offline.text
    assert offline.json()["data"]["business"]["is_accepting_orders"] is False
    assert client.app.state.business_repository.get_business(business["id"]).is_accepting_orders is False

    hidden = client.get("/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&limit=20", headers=_bearer(remitter, "req_ads_after_offline"))
    detail = client.get(f"/api/v1/ads/{ad['id']}", headers=_bearer(remitter, "req_ad_detail_offline"))
    blocked_order = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "order_offline"), "Content-Type": "application/json"},
        json={
            "ad_id": ad["id"],
            "amount_usd": "50.00",
            "receiver_data": {"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Receptor Test"},
        },
    )

    assert hidden.status_code == 200, hidden.text
    assert ad["id"] not in {item["id"] for item in hidden.json()["data"]["items"]}
    assert detail.status_code == 404
    assert blocked_order.status_code == 409
    assert blocked_order.json()["error"]["code"] == "BUSINESS_OFFLINE"
    assert "business_accepting_orders_updated" in _event_types(client)


def test_confirm_payment_consumes_once_accepts_report_archives_ad_and_sets_deadlines() -> None:
    client = _client()
    owner, business, ad, _, order = _seed_reported_order(client, owner_id=710, remitter_id=711)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before = wallet_before.blocked_credits
    consumed_before = wallet_before.consumed_credits

    response = client.post(
        f"/api/v1/business/orders/{order['id']}/confirm-payment",
        headers={**_headers(owner, "confirm_same"), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )
    replay = client.post(
        f"/api/v1/business/orders/{order['id']}/confirm-payment",
        headers={**_headers(owner, "confirm_same"), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )
    mismatch = client.post(
        f"/api/v1/business/orders/{order['id']}/confirm-payment",
        headers={**_headers(owner, "confirm_same"), "Content-Type": "application/json"},
        json={"reason": "Payload distinto"},
    )

    assert response.status_code == 200, response.text
    assert replay.status_code == 200, replay.text
    assert mismatch.status_code == 409
    body = response.json()["data"]
    assert body["order"]["status"] == "payment_confirmed"
    assert body["payment_report"]["status"] == "accepted"
    stored = client.app.state.order_repository.get_by_id(order["id"])
    assert stored.status == "payment_confirmed"
    assert stored.payment_confirmed_at is not None
    assert stored.delivery_warning_at is not None
    assert stored.delivery_deadline_at is not None
    assert stored.delivered_at is None
    assert stored.completed_at is None
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "archived"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.blocked_credits == blocked_before - 1
    assert wallet_after.consumed_credits == consumed_before + 1
    consumes = [item for item in client.app.state.ad_repository.ledger.values() if item.type == "consume" and item.related_order_id == order["id"]]
    assert len(consumes) == 1
    assert {"payment_confirmed", "credits_consumed", "ad_archived"}.issubset(set(_event_types(client)))
    assert client.app.state.order_repository.events[-1].event_type == "payment_confirmed"
    combined = response.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "owner@example.com" not in combined
    assert "storage_path" not in combined
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined


def test_confirm_payment_invalid_state_and_missing_hold_fail_safely() -> None:
    client = _client()
    owner, _, _, _, order = _seed_reported_order(client, owner_id=720, remitter_id=721)
    stored = client.app.state.order_repository.get_by_id(order["id"])
    client.app.state.order_repository.update_order(stored, status="waiting_payment")
    invalid = client.post(
        f"/api/v1/business/orders/{order['id']}/confirm-payment",
        headers={**_headers(owner, "confirm_invalid"), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )

    owner2, _, ad2, _, order2 = _seed_reported_order(client, owner_id=722, remitter_id=723)
    client.app.state.ad_repository.get_ad(ad2["id"]).credit_hold_ledger_id = None
    missing_hold = client.post(
        f"/api/v1/business/orders/{order2['id']}/confirm-payment",
        headers={**_headers(owner2, "confirm_no_hold"), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )

    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "PAYMENT_CONFIRMATION_NOT_ALLOWED"
    assert missing_hold.status_code == 409
    assert missing_hold.json()["error"]["code"] == "CREDIT_HOLD_NOT_FOUND"


def test_reject_payment_report_requires_reason_marks_rejected_and_does_not_consume() -> None:
    client = _client()
    owner, business, ad, _, order = _seed_reported_order(client, owner_id=730, remitter_id=731)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before = wallet_before.blocked_credits
    consumed_before = wallet_before.consumed_credits

    missing_reason = client.post(
        f"/api/v1/business/orders/{order['id']}/reject-payment-report",
        headers={**_headers(owner, "reject_missing"), "Content-Type": "application/json"},
        json={},
    )
    response = client.post(
        f"/api/v1/business/orders/{order['id']}/reject-payment-report",
        headers={**_headers(owner, "reject_ok"), "Content-Type": "application/json"},
        json={"reason": "Referencia no coincide"},
    )

    assert missing_reason.status_code == 400
    assert missing_reason.json()["error"]["code"] == "ADMIN_REASON_REQUIRED"
    assert response.status_code == 200, response.text
    assert response.json()["data"]["order"]["status"] == "payment_rejected"
    assert response.json()["data"]["payment_report"]["status"] == "rejected"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.blocked_credits == blocked_before
    assert wallet_after.consumed_credits == consumed_before
    assert "payment_report_rejected" in _event_types(client)


def test_mark_delivered_requires_confirmed_sets_timers_and_does_not_complete_or_double_consume() -> None:
    client = _client()
    owner, business, _, _, order = _seed_reported_order(client, owner_id=740, remitter_id=741)
    invalid = client.post(
        f"/api/v1/business/orders/{order['id']}/mark-delivered",
        headers={**_headers(owner, "deliver_invalid"), "Content-Type": "application/json"},
        json={"reason": "Pago movil enviado"},
    )
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "DELIVERY_NOT_ALLOWED"

    confirm = client.post(
        f"/api/v1/business/orders/{order['id']}/confirm-payment",
        headers={**_headers(owner, "confirm_for_delivery"), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )
    assert confirm.status_code == 200, confirm.text
    wallet_before_delivery = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before_delivery = wallet_before_delivery.blocked_credits
    consumed_before_delivery = wallet_before_delivery.consumed_credits

    delivered = client.post(
        f"/api/v1/business/orders/{order['id']}/mark-delivered",
        headers={**_headers(owner, "deliver_ok"), "Content-Type": "application/json"},
        json={"reason": "Pago movil enviado"},
    )

    assert delivered.status_code == 200, delivered.text
    stored = client.app.state.order_repository.get_by_id(order["id"])
    assert stored.status == "delivered"
    assert stored.delivered_at is not None
    assert stored.auto_complete_warning_12h_at is not None
    assert stored.auto_complete_warning_23h_at is not None
    assert stored.auto_complete_at is not None
    assert stored.completed_at is None
    wallet_after_delivery = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after_delivery.blocked_credits == blocked_before_delivery
    assert wallet_after_delivery.consumed_credits == consumed_before_delivery
    assert "order_delivered" in _event_types(client)


def test_no_chat_or_dispute_endpoints_and_migration_contains_slice_06_constraints() -> None:
    client = _client()
    owner, _, _, _, order = _seed_reported_order(client, owner_id=750, remitter_id=751)

    chat = client.post(f"/api/v1/business/orders/{order['id']}/chat", headers=_headers(owner, "chat_forbidden"))
    dispute = client.post(f"/api/v1/business/orders/{order['id']}/dispute", headers=_headers(owner, "dispute_forbidden"))

    assert chat.status_code == 404
    assert dispute.status_code == 404
    migration = open("database/migrations/0007_slice_06_business_order_ops.up.sql", encoding="utf-8").read()
    for expected in [
        "'payment_rejected'",
        "credits_ledger_related_order_type_idx",
        "credits_ledger_reference_type_id_type_idx",
        "payment_reports_order_status_created_idx",
    ]:
        assert expected in migration
