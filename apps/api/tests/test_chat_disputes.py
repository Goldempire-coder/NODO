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
        "APP_VERSION": "0.0.0-slice-07",
        "NODO_BUILD_ID": "pytest-chat-disputes-build",
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


def _upload_payment_evidence(client: TestClient, remitter: dict, order_id: str, key: str = "evidence") -> dict:
    response = client.post(
        f"/api/v1/orders/{order_id}/payment-evidence",
        headers=_headers(remitter, key),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", b"proof", "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _report_payment(client: TestClient, remitter: dict, order: dict, *, key: str = "report") -> dict:
    evidence = _upload_payment_evidence(client, remitter, order["id"], key=f"{key}_evidence")
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


def _seed_reported_order(client: TestClient, *, owner_id: int = 800, remitter_id: int = 801) -> tuple[dict, dict, dict, dict, dict]:
    owner = _login(client, owner_id, f"owner_{owner_id}")
    business, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key=f"ad_{owner_id}")
    remitter = _login(client, remitter_id, f"remitter_{remitter_id}")
    order = _create_order(client, remitter, ad["id"], key=f"order_{remitter_id}")
    _report_payment(client, remitter, order, key=f"report_{remitter_id}")
    return owner, business, ad, remitter, order


def _confirm_payment(client: TestClient, owner: dict, order_id: str, key: str) -> dict:
    response = client.post(
        f"/api/v1/business/orders/{order_id}/confirm-payment",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _reject_payment(client: TestClient, owner: dict, order_id: str, key: str) -> dict:
    response = client.post(
        f"/api/v1/business/orders/{order_id}/reject-payment-report",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={"reason": "Referencia no coincide"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _mark_delivered(client: TestClient, owner: dict, order_id: str, key: str) -> dict:
    response = client.post(
        f"/api/v1/business/orders/{order_id}/mark-delivered",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={"reason": "Pago movil enviado"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_messages_are_order_scoped_idempotent_and_audited() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(client)
    other = _login(client, 802, "other")

    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "msg_1"), "Content-Type": "application/json"},
        json={"body": "<b>Pago reportado</b>", "attachment_ids": []},
    )
    replay = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "msg_1"), "Content-Type": "application/json"},
        json={"body": "<b>Pago reportado</b>", "attachment_ids": []},
    )
    mismatch = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "msg_1"), "Content-Type": "application/json"},
        json={"body": "distinto", "attachment_ids": []},
    )
    business_list = client.get(f"/api/v1/orders/{order['id']}/messages", headers=_bearer(owner, "req_messages_business"))
    foreign = client.get(f"/api/v1/orders/{order['id']}/messages", headers=_bearer(other, "req_messages_foreign"))
    unauthenticated = client.get(f"/api/v1/orders/{order['id']}/messages", headers={"X-Request-Id": "req_no_auth"})

    assert created.status_code == 201, created.text
    assert created.json()["data"]["message"]["body"] == "Pago reportado"
    assert replay.status_code == 201
    assert replay.json()["data"]["message"]["id"] == created.json()["data"]["message"]["id"]
    assert mismatch.status_code == 409
    assert business_list.status_code == 200, business_list.text
    assert len(business_list.json()["data"]["items"]) == 1
    assert business_list.json()["data"]["capabilities"]["can_send_message"] is True
    assert foreign.status_code == 404
    assert unauthenticated.status_code in {401, 403}
    assert "message_created" in _event_types(client)
    assert "message_sent" not in _event_types(client)
    combined = created.text + business_list.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "owner@example.com" not in combined
    assert "account_value" not in combined
    assert "storage_path" not in combined
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined


def test_message_validation_and_state_rules_are_safe() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(client, owner_id=810, remitter_id=811)
    empty = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "empty_msg"), "Content-Type": "application/json"},
        json={"body": "", "attachment_ids": []},
    )
    stored = client.app.state.order_repository.get_by_id(order["id"])
    client.app.state.order_repository.update_order(stored, status="waiting_payment")
    invalid_state = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "state_msg"), "Content-Type": "application/json"},
        json={"body": "todavia no", "attachment_ids": []},
    )
    no_key = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_bearer(remitter, "req_no_key"), "Content-Type": "application/json"},
        json={"body": "sin key", "attachment_ids": []},
    )

    assert empty.status_code == 400
    assert empty.json()["error"]["code"] == "MESSAGE_BODY_REQUIRED"
    assert invalid_state.status_code == 409
    assert invalid_state.json()["error"]["code"] == "ORDER_STATUS_INVALID"
    assert no_key.status_code == 400
    assert no_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_message_attachments_are_private_limited_and_never_expose_storage_path() -> None:
    client = _client()
    _, _, _, remitter, order = _seed_reported_order(client, owner_id=820, remitter_id=821)

    valid = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, "attach_ok"),
        files={"file": ("chat-proof.png", b"proof", "image/png")},
    )
    invalid_mime = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, "attach_mime"),
        files={"file": ("bad.txt", b"bad", "text/plain")},
    )
    oversize = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, "attach_large"),
        files={"file": ("large.pdf", b"x" * (5 * 1024 * 1024 + 1), "application/pdf")},
    )
    with_attachment = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "msg_attach"), "Content-Type": "application/json"},
        json={"body": "Adjunto evidencia", "attachment_ids": [valid.json()["data"]["attachment"]["id"]]},
    )

    assert valid.status_code == 201, valid.text
    assert valid.json()["data"]["attachment"]["file_type"] == "message_attachment"
    assert invalid_mime.status_code == 400
    assert invalid_mime.json()["error"]["code"] == "MESSAGE_ATTACHMENT_TYPE_NOT_ALLOWED"
    assert oversize.status_code == 400
    assert oversize.json()["error"]["code"] == "MESSAGE_ATTACHMENT_TOO_LARGE"
    assert with_attachment.status_code == 201, with_attachment.text
    assert with_attachment.json()["data"]["message"]["attachments"][0]["id"] == valid.json()["data"]["attachment"]["id"]
    assert "message_attachment_uploaded" in _event_types(client)
    combined = valid.text + with_attachment.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "storage_path" not in combined
    assert "private/message_attachments" not in combined


def test_open_dispute_from_payment_reported_keeps_credits_and_ad_state_and_enables_dispute_messages() -> None:
    client = _client()
    owner, business, ad, remitter, order = _seed_reported_order(client, owner_id=830, remitter_id=831)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before = wallet_before.blocked_credits
    consumed_before = wallet_before.consumed_credits

    evidence = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, "dispute_evidence"),
        files={"file": ("dispute-proof.png", b"proof", "image/png")},
    )
    invalid_evidence = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(remitter, "dispute_bad_evidence"), "Content-Type": "application/json"},
        json={"reason": "business_no_payment_confirmation", "description": "No responde", "evidence_file_ids": ["00000000-0000-0000-0000-000000000000"]},
    )
    opened = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(remitter, "dispute_open"), "Content-Type": "application/json"},
        json={"reason": "business_no_payment_confirmation", "description": "No responde", "evidence_file_ids": [evidence.json()["data"]["attachment"]["id"]]},
    )
    message = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "dispute_msg"), "Content-Type": "application/json"},
        json={"body": "Estamos revisando", "attachment_ids": []},
    )

    assert evidence.status_code == 201, evidence.text
    assert invalid_evidence.status_code == 400
    assert invalid_evidence.json()["error"]["code"] == "MESSAGE_ATTACHMENT_INVALID"
    assert opened.status_code == 201, opened.text
    assert opened.json()["data"]["dispute"]["previous_order_status"] == "payment_reported"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "disputed"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.blocked_credits == blocked_before
    assert wallet_after.consumed_credits == consumed_before
    assert message.status_code == 201, message.text
    events = _event_types(client)
    assert "dispute_opened" in events
    assert "dispute_message_created" in events
    assert "dispute_resolved" not in events
    assert any(event.event_type == "dispute_opened" for event in client.app.state.order_repository.events)
    assert client.app.state.dispute_repository.events[-1].event_type == "dispute_opened"


def test_open_dispute_effects_for_rejected_confirmed_and_delivered_states_are_contract_safe() -> None:
    client = _client()

    owner_rejected, business_rejected, ad_rejected, remitter_rejected, order_rejected = _seed_reported_order(client, owner_id=840, remitter_id=841)
    _reject_payment(client, owner_rejected, order_rejected["id"], "reject_for_dispute")
    wallet_rejected = client.app.state.ad_repository.get_wallet(business_rejected["id"])
    rejected = client.post(
        f"/api/v1/orders/{order_rejected['id']}/disputes",
        headers={**_headers(remitter_rejected, "dispute_rejected"), "Content-Type": "application/json"},
        json={"reason": "amount_incorrect", "description": "Monto no coincide", "evidence_file_ids": []},
    )

    owner_confirmed, business_confirmed, ad_confirmed, remitter_confirmed, order_confirmed = _seed_reported_order(client, owner_id=842, remitter_id=843)
    _confirm_payment(client, owner_confirmed, order_confirmed["id"], "confirm_for_dispute")
    wallet_confirmed = client.app.state.ad_repository.get_wallet(business_confirmed["id"])
    confirmed = client.post(
        f"/api/v1/orders/{order_confirmed['id']}/disputes",
        headers={**_headers(remitter_confirmed, "dispute_confirmed"), "Content-Type": "application/json"},
        json={"reason": "business_confirmed_payment_but_not_delivered", "description": "No ha enviado", "evidence_file_ids": []},
    )

    owner_delivered, business_delivered, ad_delivered, remitter_delivered, order_delivered = _seed_reported_order(client, owner_id=844, remitter_id=845)
    _confirm_payment(client, owner_delivered, order_delivered["id"], "confirm_for_delivered")
    _mark_delivered(client, owner_delivered, order_delivered["id"], "delivered_for_dispute")
    wallet_delivered = client.app.state.ad_repository.get_wallet(business_delivered["id"])
    delivered = client.post(
        f"/api/v1/orders/{order_delivered['id']}/disputes",
        headers={**_headers(remitter_delivered, "dispute_delivered"), "Content-Type": "application/json"},
        json={"reason": "payment_mobile_not_received", "description": "No recibido", "evidence_file_ids": []},
    )

    assert rejected.status_code == 201, rejected.text
    assert client.app.state.ad_repository.get_ad(ad_rejected["id"]).status == "in_order"
    assert client.app.state.ad_repository.get_wallet(business_rejected["id"]).blocked_credits == wallet_rejected.blocked_credits
    assert confirmed.status_code == 201, confirmed.text
    assert client.app.state.ad_repository.get_ad(ad_confirmed["id"]).status == "archived"
    assert client.app.state.ad_repository.get_wallet(business_confirmed["id"]).consumed_credits == wallet_confirmed.consumed_credits
    assert delivered.status_code == 201, delivered.text
    assert client.app.state.ad_repository.get_ad(ad_delivered["id"]).status == "archived"
    assert client.app.state.ad_repository.get_wallet(business_delivered["id"]).consumed_credits == wallet_delivered.consumed_credits


def test_disputes_are_idempotent_and_support_cannot_resolve_in_admin_console() -> None:
    client = _client()
    _, _, _, remitter, order = _seed_reported_order(client, owner_id=850, remitter_id=851)
    admin = _login(client, 852, "admin")
    support = _login(client, 853, "support")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")

    payload = {"reason": "business_no_payment_confirmation", "description": "Sin respuesta", "evidence_file_ids": []}
    opened = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(remitter, "dispute_idem"), "Content-Type": "application/json"},
        json=payload,
    )
    replay = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(remitter, "dispute_idem"), "Content-Type": "application/json"},
        json=payload,
    )
    second_key = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(remitter, "dispute_second"), "Content-Type": "application/json"},
        json=payload,
    )
    listing = client.get("/api/v1/admin/disputes?limit=20", headers=_bearer(admin, "req_admin_disputes"))
    detail = client.get(f"/api/v1/admin/disputes/{opened.json()['data']['dispute']['id']}", headers=_bearer(support, "req_support_dispute"))
    resolve = client.post(
        f"/api/v1/admin/disputes/{opened.json()['data']['dispute']['id']}/resolve",
        headers={**_headers(support, "resolve_forbidden"), "Content-Type": "application/json"},
        json={"resolution_type": "keep_under_review", "reason": "support read only"},
    )

    assert opened.status_code == 201, opened.text
    assert replay.status_code == 201
    assert replay.json()["data"]["dispute"]["id"] == opened.json()["data"]["dispute"]["id"]
    assert second_key.status_code == 409
    assert second_key.json()["error"]["code"] == "DISPUTE_ALREADY_OPEN"
    assert listing.status_code == 200, listing.text
    assert listing.json()["data"]["items"][0]["status"] == "open"
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["events"][0]["event_type"] == "dispute_opened"
    assert detail.json()["data"]["messages"] == []
    assert resolve.status_code == 403
    assert "dispute_resolved" not in _event_types(client)
    combined = listing.text + detail.text
    assert "storage_path" not in combined
    assert "account_value" not in combined


def test_slice_07_migration_and_contract_prohibitions_are_explicit() -> None:
    migration = open("database/migrations/0008_slice_07_chat_disputes.up.sql", encoding="utf-8").read()
    app_source = open("apps/api/app/main.py", encoding="utf-8").read()
    slice_api = open("control_plane/09_SLICES/slice_07_chat_disputes/API_CONTRACT.md", encoding="utf-8").read()

    for expected in [
        "create table if not exists messages",
        "create table if not exists message_attachments",
        "create table if not exists disputes",
        "create table if not exists dispute_events",
        "messages_order_created_idx",
        "disputes_open_order_idx",
    ]:
        assert expected in migration
    assert "chat_messages" not in migration
    assert "'admin_only'" in migration
    assert "'hidden'" in migration
    assert "resolution text" not in migration
    assert "'dispute_status_changed'" in migration
    assert "'dispute_resolved'" in migration
    assert "/confirm-received" not in app_source
    assert "/rating" not in app_source
    assert "/complete" not in app_source
    assert "POST /api/v1/admin/disputes/{id}/resolve" in slice_api
    assert "Endpoints explicitly not authorized in slice 07" in slice_api
