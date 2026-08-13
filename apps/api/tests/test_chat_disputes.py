from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from urllib.parse import urlencode

import pytest
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
from app.modules.orders.receiver_details import receiver_payload_hash  # noqa: E402
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


def _approved_business_with_method(
    client: TestClient,
    login: dict,
    *,
    credits: int = 5,
    method: str = "zelle",
) -> tuple[dict, str]:
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
        method_type=method,
        network="TRC20" if method == "usdt_trc20" else None,
        account_value="TFullWalletValue123456789" if method == "usdt_trc20" else "owner@example.com",
        account_masked="TFull...6789" if method == "usdt_trc20" else "***.com",
        holder_name="Owner Test",
    )
    payment.verified_status = "approved"
    payment.active = True
    if credits:
        client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=credits, created_by=login["user"]["id"])
    return business, payment.id


def _create_ad(
    client: TestClient,
    owner: dict,
    payment_method_id: str,
    *,
    key: str = "ad",
    method: str = "zelle",
) -> dict:
    response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment_method_id,
            "payment_method": method,
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
    content = png_bytes(f"proof:{order_id}:{key}".encode("utf-8"))
    response = client.post(
        f"/api/v1/orders/{order_id}/payment-evidence",
        headers=_headers(remitter, key),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", content, "image/png")},
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


def _share_zelle(client: TestClient, owner: dict, order_id: str, *, key: str = "share_zelle") -> dict:
    response = client.post(
        f"/api/v1/orders/{order_id}/share-zelle",
        headers=_headers(owner, key),
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _seed_reported_order(client: TestClient, *, owner_id: int = 800, remitter_id: int = 801) -> tuple[dict, dict, dict, dict, dict]:
    owner = _login(client, owner_id, f"owner_{owner_id}")
    business, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key=f"ad_{owner_id}")
    remitter = _login(client, remitter_id, f"remitter_{remitter_id}")
    order = _create_order(client, remitter, ad["id"], key=f"order_{remitter_id}")
    _share_zelle(client, owner, order["id"], key=f"share_zelle_{owner_id}_{remitter_id}")
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


def _seed_historical_payment_rejected(client: TestClient, order_id: str) -> None:
    order = client.app.state.order_repository.get_by_id(order_id)
    report = client.app.state.order_repository.get_submitted_payment_report_for_order(order_id)
    assert order is not None
    assert report is not None
    client.app.state.order_repository.update_payment_report(report, status="rejected")
    client.app.state.order_repository.update_order(order, status="payment_rejected")


def _mark_delivered(client: TestClient, owner: dict, order_id: str, key: str) -> dict:
    order = client.app.state.order_repository.get_by_id(order_id)
    payload = {
        "bank": "0102",
        "phone": "+584121234567",
        "document": "V12345678",
        "holder": "Receptor Test",
    }
    client.app.state.order_repository.create_receiver_details_atomically(
        order_id=order.id,
        remitter_user_id=order.remitter_user_id,
        payload=payload,
        payload_hash=receiver_payload_hash(payload),
        request_id=f"fixture_receiver_{order_id}",
        audit_metadata={"schema": "pago_movil_receiver_v1", "fixture": True},
    )
    response = client.post(
        f"/api/v1/business/orders/{order_id}/mark-delivered",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={"reason": "Pago movil enviado"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def _admin_notifications(client: TestClient) -> list:
    return list(client.app.state.admin_notification_repository.notifications.values())


def test_slice_50a_waiting_payment_chat_is_immediate_virtual_and_private() -> None:
    client = _client()
    owner = _login(client, 7801, "slice50a_chat_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="slice50a_chat_ad")
    remitter = _login(client, 7802, "slice50a_chat_client")
    other = _login(client, 7803, "slice50a_chat_other")
    order = _create_order(client, remitter, ad["id"], key="slice50a_chat_order")

    client_chat = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_slice50a_client_chat"),
    )
    business_chat = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(owner, "req_slice50a_business_chat"),
    )
    foreign_read = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(other, "req_slice50a_foreign_chat"),
    )
    foreign_write = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(other, "slice50a_foreign_write"), "Content-Type": "application/json"},
        json={"body": "No pertenezco a esta orden", "attachment_ids": []},
    )

    assert client_chat.status_code == 200, client_chat.text
    assert business_chat.status_code == 200, business_chat.text
    assert foreign_read.status_code == 404
    assert foreign_write.status_code == 404
    client_data = client_chat.json()["data"]
    business_data = business_chat.json()["data"]
    assert client_data["items"] == []
    assert client_data["system_messages"] == [
        {
            "id": f"system:negotiation-created:{order['id']}",
            "order_id": order["id"],
            "sender_role": "system",
            "body": (
                "Negociacion creada. Coordinen por aqui. "
                "No envies el pago hasta que el negocio comparta sus datos."
            ),
            "visibility": "parties",
            "status": "visible",
            "attachments": [],
            "created_at": order["created_at"],
        }
    ]
    assert client_data["capabilities"]["can_send_message"] is True
    assert client_data["capabilities"]["payment_details_shared"] is False
    assert client_data["capabilities"]["can_report_payment"] is False
    assert business_data["capabilities"]["can_send_message"] is True
    assert business_data["capabilities"]["can_share_zelle"] is True
    assert not any(
        event.event_type == "message_created"
        and event.resource_id == f"system:negotiation-created:{order['id']}"
        for event in client.app.state.audit_writer.events
    )


@pytest.mark.parametrize(
    ("role", "telegram_id"),
    [("admin", 7804), ("super_admin", 7805), ("support", 7806)],
)
def test_waiting_payment_chat_body_is_hidden_from_internal_roles(role: str, telegram_id: int) -> None:
    client = _client()
    owner = _login(client, telegram_id + 100, f"private_chat_owner_{role}")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key=f"private_chat_ad_{role}")
    remitter = _login(client, telegram_id + 200, f"private_chat_client_{role}")
    order = _create_order(client, remitter, ad["id"], key=f"private_chat_order_{role}")
    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, f"private_chat_message_{role}"), "Content-Type": "application/json"},
        json={"body": "Mensaje privado previo al pago", "attachment_ids": []},
    )
    internal_user = _login(client, telegram_id, f"private_chat_{role}")
    client.app.state.user_repository.set_user_role(internal_user["user"]["id"], role)

    response = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(internal_user, f"req_private_chat_{role}"),
    )

    assert created.status_code == 201, created.text
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "ORDER_NOT_FOUND"


def test_waiting_payment_chat_body_remains_available_to_direct_participants() -> None:
    client = _client()
    owner = _login(client, 7810, "private_chat_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="private_chat_participant_ad")
    remitter = _login(client, 7811, "private_chat_client")
    order = _create_order(client, remitter, ad["id"], key="private_chat_participant_order")
    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "private_chat_participant_message"), "Content-Type": "application/json"},
        json={"body": "Mensaje visible solo a participantes", "attachment_ids": []},
    )

    client_read = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_private_chat_client_read"),
    )
    business_read = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(owner, "req_private_chat_business_read"),
    )

    assert created.status_code == 201, created.text
    assert client_read.status_code == 200, client_read.text
    assert business_read.status_code == 200, business_read.text
    assert client_read.json()["data"]["items"][0]["body"] == "Mensaje visible solo a participantes"
    assert business_read.json()["data"]["items"][0]["body"] == "Mensaje visible solo a participantes"


def test_client_cancelled_order_keeps_chat_readable_closed_and_private_to_participants() -> None:
    client = _client()
    owner = _login(client, 7814, "cancelled_chat_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="cancelled_chat_ad")
    remitter = _login(client, 7815, "cancelled_chat_client")
    other = _login(client, 7816, "cancelled_chat_other")
    admin = _login(client, 7817, "cancelled_chat_admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    order = _create_order(client, remitter, ad["id"], key="cancelled_chat_order")
    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "cancelled_chat_message"), "Content-Type": "application/json"},
        json={"body": "Hola, voy a revisar esta cotizacion.", "attachment_ids": []},
    )
    cancelled = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={**_headers(remitter, "cancelled_chat_order"), "Content-Type": "application/json"},
        json={"reason": "choose_another_business", "payment_not_sent_confirmed": True},
    )

    business_read = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(owner, "req_cancelled_chat_business_read"),
    )
    client_read = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_cancelled_chat_client_read"),
    )
    admin_read = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(admin, "req_cancelled_chat_admin_read"),
    )
    foreign_read = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(other, "req_cancelled_chat_foreign_read"),
    )
    write_after_cancel = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "cancelled_chat_write"), "Content-Type": "application/json"},
        json={"body": "Sigo escribiendo despues del cierre", "attachment_ids": []},
    )

    assert created.status_code == 201, created.text
    assert cancelled.status_code == 200, cancelled.text
    assert business_read.status_code == 200, business_read.text
    assert client_read.status_code == 200, client_read.text
    assert admin_read.status_code == 404
    assert foreign_read.status_code == 404
    assert write_after_cancel.status_code == 409
    data = business_read.json()["data"]
    assert data["order"]["status"] == "cancelled"
    assert data["capabilities"]["can_send_message"] is False
    assert data["capabilities"]["can_open_dispute"] is False
    assert any(
        message["id"] == f"system:order-cancelled:{order['id']}"
        and "Cliente cancelo la negociacion" in message["body"]
        for message in data["system_messages"]
    )
    combined = business_read.text + client_read.text
    assert "storage_path" not in combined
    assert "signed_url" not in combined


@pytest.mark.parametrize(
    ("role", "telegram_id"),
    [("admin", 7820), ("super_admin", 7821), ("support", 7822)],
)
def test_internal_roles_keep_existing_chat_read_access_after_payment_report(
    role: str,
    telegram_id: int,
) -> None:
    client = _client()
    owner = _login(client, telegram_id + 100, f"reported_chat_owner_{role}")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key=f"reported_chat_ad_{role}")
    remitter = _login(client, telegram_id + 200, f"reported_chat_client_{role}")
    order = _create_order(client, remitter, ad["id"], key=f"reported_chat_order_{role}")
    _share_zelle(client, owner, order["id"], key=f"reported_chat_share_{role}")
    _report_payment(client, remitter, order, key=f"reported_chat_payment_{role}")
    internal_user = _login(client, telegram_id, f"reported_chat_{role}")
    client.app.state.user_repository.set_user_role(internal_user["user"]["id"], role)

    response = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(internal_user, f"req_reported_chat_{role}"),
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["items"]


def test_slice_50a_business_share_zelle_is_owner_only_deduped_and_safe() -> None:
    client = _client()
    owner = _login(client, 7811, "slice50a_share_owner")
    business, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="slice50a_share_ad")
    remitter = _login(client, 7812, "slice50a_share_client")
    other_owner = _login(client, 7813, "slice50a_other_owner")
    _approved_business_with_method(client, other_owner, credits=0)
    order = _create_order(client, remitter, ad["id"], key="slice50a_share_order")

    client_attempt = client.post(
        f"/api/v1/orders/{order['id']}/share-zelle",
        headers=_headers(remitter, "slice50a_share_client_attempt"),
    )
    foreign_attempt = client.post(
        f"/api/v1/orders/{order['id']}/share-zelle",
        headers=_headers(other_owner, "slice50a_share_foreign_attempt"),
    )
    first = client.post(
        f"/api/v1/orders/{order['id']}/share-zelle",
        headers=_headers(owner, "slice50a_share_once"),
    )
    replay = client.post(
        f"/api/v1/orders/{order['id']}/share-zelle",
        headers=_headers(owner, "slice50a_share_once"),
    )
    second_key = client.post(
        f"/api/v1/orders/{order['id']}/share-zelle",
        headers=_headers(owner, "slice50a_share_second_key"),
    )
    client_chat = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_slice50a_shared_chat"),
    )

    assert client_attempt.status_code == 404
    assert foreign_attempt.status_code == 404
    assert first.status_code == 201, first.text
    assert replay.status_code == 201, replay.text
    assert second_key.status_code == 201, second_key.text
    message_id = first.json()["data"]["message"]["id"]
    assert replay.json()["data"]["message"]["id"] == message_id
    assert second_key.json()["data"]["message"]["id"] == message_id
    assert "owner@example.com" in first.json()["data"]["message"]["body"]
    actual_messages = [
        message
        for message in client.app.state.chat_repository.messages.values()
        if message.order_id == order["id"]
    ]
    assert len(actual_messages) == 1
    capabilities = client_chat.json()["data"]["capabilities"]
    assert capabilities["payment_details_shared"] is True
    assert capabilities["can_report_payment"] is True
    assert _admin_notifications(client) == []
    audit_text = json.dumps(
        [event.__dict__ for event in client.app.state.audit_writer.events],
        default=str,
    )
    assert "owner@example.com" not in audit_text
    assert business["id"] in audit_text


def test_usdt_wallet_requires_explicit_business_share_and_replay_is_deduped() -> None:
    client = _client()
    owner = _login(client, 7814, "payment_details_usdt_owner")
    business, method_id = _approved_business_with_method(
        client,
        owner,
        credits=1,
        method="usdt_trc20",
    )
    ad = _create_ad(
        client,
        owner,
        method_id,
        key="payment_details_usdt_ad",
        method="usdt_trc20",
    )
    remitter = _login(client, 7815, "payment_details_usdt_client")
    order = _create_order(client, remitter, ad["id"], key="payment_details_usdt_order")

    chat = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_payment_details_usdt_before"),
    )
    reveal = client.get(
        f"/api/v1/orders/{order['id']}/payment-instructions",
        headers=_bearer(remitter, "req_payment_details_usdt_reveal_before"),
    )
    first_share = client.post(
        f"/api/v1/orders/{order['id']}/share-payment-details",
        headers=_headers(owner, "payment_details_usdt_share"),
    )
    replay_share = client.post(
        f"/api/v1/orders/{order['id']}/share-payment-details",
        headers=_headers(owner, "payment_details_usdt_share"),
    )
    chat_after = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_payment_details_usdt_after"),
    )
    reveal_after = client.get(
        f"/api/v1/orders/{order['id']}/payment-instructions",
        headers=_bearer(remitter, "req_payment_details_usdt_reveal_after"),
    )

    assert chat.status_code == 200, chat.text
    assert chat.json()["data"]["capabilities"]["can_report_payment"] is False
    assert chat.json()["data"]["capabilities"]["can_share_zelle"] is False
    assert "TFullWalletValue123456789" not in chat.text
    assert reveal.status_code == 409, reveal.text
    assert reveal.json()["error"]["code"] == "ORDER_PAYMENT_DETAILS_NOT_SHARED"
    assert first_share.status_code == 201, first_share.text
    assert replay_share.status_code == 201, replay_share.text
    assert first_share.json()["data"]["message"]["id"] == replay_share.json()["data"]["message"]["id"]
    assert "TFullWalletValue123456789" in first_share.json()["data"]["message"]["body"]
    assert "Confirma con el negocio la red exacta antes de enviar." in first_share.json()["data"]["message"]["body"]
    assert chat_after.json()["data"]["capabilities"]["can_report_payment"] is True
    assert reveal_after.status_code == 200, reveal_after.text
    assert reveal_after.json()["data"]["payment_instructions"]["account_value"] == "TFullWalletValue123456789"
    assert reveal_after.json()["data"]["payment_instructions"]["network"] == "TRC20"
    audit_text = json.dumps(
        [event.__dict__ for event in client.app.state.audit_writer.events],
        default=str,
    )
    assert "TFullWalletValue123456789" not in audit_text
    assert business["id"] in audit_text


def test_slice_50a_active_chat_lists_latest_window_with_shared_zelle_visible() -> None:
    client = _client()
    owner = _login(client, 7814, "slice50a_latest_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="slice50a_latest_ad")
    remitter = _login(client, 7815, "slice50a_latest_client")
    order = _create_order(client, remitter, ad["id"], key="slice50a_latest_order")

    repository = client.app.state.chat_repository
    created_ids: list[str] = []
    for index in range(51):
        sender = remitter if index % 2 == 0 else owner
        message = repository.create_message(
            order_id=order["id"],
            sender_user_id=sender["user"]["id"],
            sender_role="remitter" if index % 2 == 0 else "business_owner",
            body=f"Mensaje previo {index + 1}",
            idempotency_key=f"slice50a_latest_message_{index + 1}",
        )
        created_ids.append(message.id)

    shared = _share_zelle(
        client,
        owner,
        order["id"],
        key="slice50a_latest_share_zelle",
    )
    shared_message_id = shared["message"]["id"]
    client_chat = client.get(
        f"/api/v1/orders/{order['id']}/messages?limit=25",
        headers=_bearer(remitter, "req_slice50a_latest_client"),
    )
    business_chat = client.get(
        f"/api/v1/orders/{order['id']}/messages?limit=50",
        headers=_bearer(owner, "req_slice50a_latest_business"),
    )

    assert client_chat.status_code == 200, client_chat.text
    assert business_chat.status_code == 200, business_chat.text
    client_data = client_chat.json()["data"]
    business_data = business_chat.json()["data"]
    assert len(client_data["items"]) == 25
    assert len(business_data["items"]) == 50
    assert client_data["items"][-1]["id"] == shared_message_id
    assert business_data["items"][-1]["id"] == shared_message_id
    assert shared_message_id in {item["id"] for item in client_data["items"]}
    assert shared_message_id in {item["id"] for item in business_data["items"]}
    assert client_data["capabilities"]["can_report_payment"] is True
    assert client_data["next_cursor"] is not None
    assert [item["created_at"] for item in client_data["items"]] == sorted(
        item["created_at"] for item in client_data["items"]
    )

    older_chat = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        params={"limit": 25, "cursor": client_data["next_cursor"]},
        headers=_bearer(remitter, "req_slice50a_older_client"),
    )
    assert older_chat.status_code == 200, older_chat.text
    older_ids = {item["id"] for item in older_chat.json()["data"]["items"]}
    assert shared_message_id not in older_ids
    assert created_ids[-1] not in older_ids


def test_chat_cursor_does_not_lose_messages_with_tied_created_at() -> None:
    client = _client()
    owner = _login(client, 7816, "tied_chat_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="tied_chat_ad")
    remitter = _login(client, 7817, "tied_chat_client")
    order = _create_order(client, remitter, ad["id"], key="tied_chat_order")
    repository = client.app.state.chat_repository
    tied_at = utc_now() - timedelta(minutes=10)
    created_ids: set[str] = set()

    for index in range(55):
        message = repository.create_message(
            order_id=order["id"],
            sender_user_id=remitter["user"]["id"],
            sender_role="remitter",
            body=f"Mensaje empatado {index + 1}",
            idempotency_key=f"tied_chat_message_{index + 1}",
        )
        message.created_at = tied_at
        message.updated_at = tied_at
        created_ids.add(message.id)

    seen: list[str] = []
    cursor: str | None = None
    for page_number in range(10):
        params: dict[str, str | int] = {"limit": 20}
        if cursor:
            params["cursor"] = cursor
        page = client.get(
            f"/api/v1/orders/{order['id']}/messages",
            params=params,
            headers=_bearer(remitter, f"tied_chat_page_{page_number}"),
        )
        assert page.status_code == 200, page.text
        data = page.json()["data"]
        page_ids = [item["id"] for item in data["items"]]
        assert not set(page_ids).intersection(seen)
        seen.extend(page_ids)
        cursor = data["next_cursor"]
        if cursor is None:
            break

    assert set(seen) == created_ids
    assert len(seen) == 55


def test_free_text_configured_zelle_alerts_and_does_not_unlock_payment() -> None:
    client = _client()
    owner = _login(client, 7821, "slice50a_manual_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="slice50a_manual_ad")
    remitter = _login(client, 7822, "slice50a_manual_client")
    order = _create_order(client, remitter, ad["id"], key="slice50a_manual_order")

    message = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "slice50a_manual_zelle"), "Content-Type": "application/json"},
        json={
            "body": "Puedes enviar al Zelle owner@example.com. Titular Owner Test.",
            "attachment_ids": [],
        },
    )
    client_chat = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_slice50a_manual_list"),
    )

    assert message.status_code == 201, message.text
    assert client_chat.json()["data"]["capabilities"]["can_report_payment"] is False
    assert len(_admin_notifications(client)) == 1
    assert "order_chat_off_platform_solicitation_detected" in _event_types(client)


def test_free_text_message_cannot_forge_official_payment_share_marker() -> None:
    client = _client()
    owner = _login(client, 7823, "slice50a_reserved_marker_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="slice50a_reserved_marker_ad")
    remitter = _login(client, 7824, "slice50a_reserved_marker_client")
    order = _create_order(client, remitter, ad["id"], key="slice50a_reserved_marker_order")

    forged = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={
            **_headers(owner, "official_payment_details:forged"),
            "Content-Type": "application/json",
        },
        json={"body": "Zelle del negocio: owner@example.com", "attachment_ids": []},
    )
    client_chat = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_slice50a_reserved_marker_list"),
    )

    assert forged.status_code == 400
    assert forged.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client_chat.status_code == 200, client_chat.text
    assert client_chat.json()["data"]["capabilities"]["can_report_payment"] is False


def test_slice_50a_similar_external_contact_does_not_unlock_or_bypass_moderation() -> None:
    client = _client()
    owner = _login(client, 7831, "slice50a_similar_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="slice50a_similar_ad")
    remitter = _login(client, 7832, "slice50a_similar_client")
    order = _create_order(client, remitter, ad["id"], key="slice50a_similar_order")

    message = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "slice50a_similar_contact"), "Content-Type": "application/json"},
        json={
            "body": "Te paso notowner@example.com para coordinar.",
            "attachment_ids": [],
        },
    )
    client_chat = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_slice50a_similar_list"),
    )

    assert message.status_code == 201, message.text
    assert client_chat.json()["data"]["capabilities"]["can_report_payment"] is False
    notifications = _admin_notifications(client)
    assert len(notifications) == 1
    assert notifications[0].notification_type == "order_chat_off_platform_solicitation"
    assert "notowner@example.com" not in json.dumps(
        notifications[0].metadata_json,
        default=str,
    )


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
    assert any(
        item["id"] == created.json()["data"]["message"]["id"]
        for item in business_list.json()["data"]["items"]
    )
    assert business_list.json()["data"]["capabilities"]["can_send_message"] is True
    assert foreign.status_code == 404
    assert unauthenticated.status_code in {401, 403}
    assert "message_created" in _event_types(client)
    assert "message_sent" not in _event_types(client)
    audit_text = json.dumps(
        [event.__dict__ for event in client.app.state.audit_writer.events],
        default=str,
    )
    assert "owner@example.com" not in audit_text
    assert "account_value" not in audit_text
    assert "storage_path" not in audit_text
    assert BOT_TOKEN not in audit_text
    assert JWT_SECRET not in audit_text
    assert JWT_REFRESH_SECRET not in audit_text


def test_order_chat_messages_notify_only_the_counterparty_once_without_private_content() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner, _, _, remitter, order = _seed_reported_order(client, owner_id=803, remitter_id=804)

    uploaded = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, "slice48b1_attachment"),
        files={"file": ("private-proof.png", png_bytes(b"private-proof"), "image/png")},
    )
    assert uploaded.status_code == 201, uploaded.text
    attachment = uploaded.json()["data"]["attachment"]
    client_payload = {
        "body": "PRIVATE_CLIENT_CHAT_BODY_48B1",
        "attachment_ids": [attachment["id"]],
    }
    client_headers = {**_headers(remitter, "slice48b1_client_message"), "Content-Type": "application/json"}

    created = client.post(f"/api/v1/orders/{order['id']}/messages", headers=client_headers, json=client_payload)
    replay = client.post(f"/api/v1/orders/{order['id']}/messages", headers=client_headers, json=client_payload)

    assert created.status_code == 201, created.text
    assert replay.status_code == 201, replay.text
    business_jobs = [
        job
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.notification_type == "order_message_created_business"
    ]
    assert len(business_jobs) == 1
    business_job = business_jobs[0]
    assert business_job.recipient_user_id == owner["user"]["id"]
    assert business_job.metadata_json["target_surface"] == "business_mini_app"
    assert business_job.metadata_json["action_url"].endswith(
        f"/business/?view=business-chat&order_id={order['id']}"
    )
    serialized_business_job = json.dumps(business_job.__dict__, default=str)
    assert "PRIVATE_CLIENT_CHAT_BODY_48B1" not in serialized_business_job
    assert attachment["id"] not in serialized_business_job
    assert attachment["file_asset_id"] not in serialized_business_job
    assert "storage_path" not in serialized_business_job
    assert "signed_url" not in serialized_business_job

    business_payload = {"body": "PRIVATE_BUSINESS_CHAT_BODY_48B1", "attachment_ids": []}
    business_headers = {**_headers(owner, "slice48b1_business_message"), "Content-Type": "application/json"}
    business_created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers=business_headers,
        json=business_payload,
    )
    business_replay = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers=business_headers,
        json=business_payload,
    )

    assert business_created.status_code == 201, business_created.text
    assert business_replay.status_code == 201, business_replay.text
    client_jobs = [
        job
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.notification_type == "order_message_created_client"
        and job.metadata_json.get("request_id") == "req_slice48b1_business_message"
    ]
    assert len(client_jobs) == 1
    client_job = client_jobs[0]
    assert client_job.recipient_user_id == remitter["user"]["id"]
    assert client_job.metadata_json["target_surface"] == "client_mini_app"
    assert client_job.metadata_json["action_url"].endswith(
        f"/?view=order-chat&order_id={order['id']}"
    )
    assert "PRIVATE_BUSINESS_CHAT_BODY_48B1" not in json.dumps(client_job.__dict__, default=str)


def test_business_chat_off_platform_phrase_is_allowed_but_alerts_admin_without_leaking_body() -> None:
    client = _client()
    owner, business, _, remitter, order = _seed_reported_order(client, owner_id=804, remitter_id=805)

    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "off_platform_msg"), "Content-Type": "application/json"},
        json={"body": "La proxima vez por fuera te doy mejor tasa fuera de la app.", "attachment_ids": []},
    )
    replay = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "off_platform_msg"), "Content-Type": "application/json"},
        json={"body": "La proxima vez por fuera te doy mejor tasa fuera de la app.", "attachment_ids": []},
    )
    remitter_list = client.get(f"/api/v1/orders/{order['id']}/messages", headers=_bearer(remitter, "req_messages_remitter_off_platform"))
    notifications = _admin_notifications(client)
    audit_events = client.app.state.audit_writer.events

    assert created.status_code == 201, created.text
    assert created.json()["data"]["message"]["body"] == "La proxima vez por fuera te doy mejor tasa fuera de la app."
    assert replay.status_code == 201
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.notification_type == "order_chat_off_platform_solicitation"
    assert notification.priority == "high"
    assert notification.resource_type == "order_chat_message"
    assert notification.resource_id == created.json()["data"]["message"]["id"]
    assert notification.business_id == business["id"]
    assert notification.actor_user_id == owner["user"]["id"]
    assert notification.action_route == f"admin://order/{order['id']}"
    assert notification.metadata_json["order_id"] == order["id"]
    assert notification.metadata_json["message_id"] == created.json()["data"]["message"]["id"]
    assert notification.metadata_json["rule_id"] == "off_platform_platform_bypass"
    assert notification.metadata_json["severity"] == "high"
    assert "fuera de la app" in notification.metadata_json["matched_phrase"]
    assert remitter_list.status_code == 200
    assert any(
        item["body"] == "La proxima vez por fuera te doy mejor tasa fuera de la app."
        for item in remitter_list.json()["data"]["items"]
    )
    assert "order_chat_off_platform_solicitation_detected" in _event_types(client)
    detection_events = [event for event in audit_events if event.event_type == "order_chat_off_platform_solicitation_detected"]
    assert detection_events
    assert detection_events[0].metadata_json["order_id"] == order["id"]
    assert detection_events[0].metadata_json["rule_id"] == "off_platform_platform_bypass"
    combined_audit = json.dumps([event.__dict__ for event in audit_events], default=str)
    assert "La proxima vez" not in combined_audit
    assert "fuera de la app" not in combined_audit
    combined_notification = notification.summary + json.dumps(notification.metadata_json, default=str)
    assert "account_value" not in combined_notification
    assert "storage_path" not in combined_notification
    assert BOT_TOKEN not in combined_notification
    assert JWT_SECRET not in combined_notification


def test_remitter_off_platform_phrase_does_not_create_business_solicitation_alert() -> None:
    client = _client()
    _, _, _, remitter, order = _seed_reported_order(client, owner_id=806, remitter_id=807)

    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "remitter_off_platform_msg"), "Content-Type": "application/json"},
        json={"body": "La proxima vez por fuera te doy mejor tasa fuera de la app.", "attachment_ids": []},
    )

    assert created.status_code == 201, created.text
    assert _admin_notifications(client) == []
    assert "order_chat_off_platform_solicitation_detected" not in _event_types(client)


def test_business_chat_neutral_outside_phrase_does_not_create_alert() -> None:
    client = _client()
    owner, _, _, _, order = _seed_reported_order(client, owner_id=816, remitter_id=817)

    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "neutral_outside_msg"), "Content-Type": "application/json"},
        json={"body": "El comprobante quedo por fuera del borde de la foto; lo vuelvo a subir.", "attachment_ids": []},
    )

    assert created.status_code == 201, created.text
    assert _admin_notifications(client) == []
    assert "order_chat_off_platform_solicitation_detected" not in _event_types(client)


def test_business_chat_whatsapp_phone_alert_redacts_contact_value() -> None:
    client = _client()
    owner, _, _, _, order = _seed_reported_order(client, owner_id=808, remitter_id=809)

    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "whatsapp_msg"), "Content-Type": "application/json"},
        json={"body": "Escribeme por WhatsApp al +58 412 123 4567 para coordinar.", "attachment_ids": []},
    )
    notifications = _admin_notifications(client)

    assert created.status_code == 201, created.text
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.notification_type == "order_chat_off_platform_solicitation"
    assert notification.priority == "attention"
    assert notification.metadata_json["rule_id"] == "off_platform_external_contact"
    assert notification.metadata_json["severity"] == "attention"
    assert "WhatsApp" in notification.metadata_json["matched_phrase"]
    assert "412 123 4567" not in notification.metadata_json["matched_phrase"]
    assert "4121234567" not in notification.metadata_json["matched_phrase"].replace(" ", "")
    assert "412 123 4567" not in notification.summary


@pytest.mark.parametrize(
    "body",
    [
        "Wasap 04141234567",
        "WhatsApp +584141234567",
        "IG @usuario",
    ],
)
def test_business_chat_external_channel_and_contact_alert_without_invitation_phrase(body: str) -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(client, owner_id=818, remitter_id=819)

    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, f"external_contact_{body[:2]}"), "Content-Type": "application/json"},
        json={"body": body, "attachment_ids": []},
    )
    listed = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_external_contact_list"),
    )
    notifications = _admin_notifications(client)

    assert created.status_code == 201, created.text
    assert listed.status_code == 200, listed.text
    assert any(item["body"] == body for item in listed.json()["data"]["items"])
    assert len(notifications) == 1
    assert notifications[0].metadata_json["rule_id"] == "off_platform_external_contact"
    serialized_alert = notifications[0].summary + json.dumps(notifications[0].metadata_json, default=str)
    assert "04141234567" not in serialized_alert
    assert "+584141234567" not in serialized_alert
    assert "@usuario" not in serialized_alert


def test_stale_per_process_auth_cache_cannot_authorize_chat_or_payment_evidence() -> None:
    from app.shared.cache import InMemoryTTLCache

    client = _client(AUTH_USER_CACHE_TTL_SECONDS="300")
    owner = _login(client, 832, "blocked_cache_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="blocked_cache_ad")
    remitter = _login(client, 833, "blocked_cache_remitter")
    order = _create_order(client, remitter, ad["id"], key="blocked_cache_order")
    cache = InMemoryTTLCache()
    client.app.state.auth_user_cache = cache
    cache.set_json(
        f"auth:user:{remitter['user']['id']}",
        {"id": remitter["user"]["id"], "role": "remitter", "status": "active"},
        300,
    )

    primed = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(remitter, "req_prime_stale_auth_cache"),
    )
    assert primed.status_code == 200, primed.text
    assert cache.get_json(f"auth:user:{remitter['user']['id']}")["status"] == "active"

    client.app.state.user_repository.set_user_status(remitter["user"]["id"], "blocked")
    message = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "blocked_cached_message"), "Content-Type": "application/json"},
        json={"body": "Este mensaje no debe guardarse", "attachment_ids": []},
    )
    evidence = client.post(
        f"/api/v1/orders/{order['id']}/payment-evidence",
        headers=_headers(remitter, "blocked_cached_evidence"),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", b"proof", "image/png")},
    )

    assert message.status_code == 403
    assert message.json()["error"]["code"] == "USER_SUSPENDED"
    assert evidence.status_code == 403
    assert evidence.json()["error"]["code"] == "USER_SUSPENDED"


def test_chat_attachment_rejects_disguised_html_and_pdf_with_calm_error() -> None:
    client = _client()
    _, _, _, remitter, order = _seed_reported_order(client, owner_id=834, remitter_id=835)

    disguised = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, "disguised_chat_image"),
        files={"file": ("photo.jpg", b"<html><script>alert(1)</script></html>", "image/jpeg")},
    )
    pdf = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, "chat_pdf_not_allowed"),
        files={"file": ("document.pdf", b"%PDF-1.7", "application/pdf")},
    )

    assert disguised.status_code == 400
    assert disguised.json()["error"]["code"] == "MESSAGE_ATTACHMENT_INVALID"
    assert disguised.json()["error"]["message"] == "No pudimos aceptar ese archivo. Usa una imagen valida."
    assert pdf.status_code == 400
    assert pdf.json()["error"]["code"] == "MESSAGE_ATTACHMENT_TYPE_NOT_ALLOWED"
    assert pdf.json()["error"]["message"] == "No pudimos aceptar ese archivo. Usa una imagen valida."


@pytest.mark.parametrize(
    ("image_format", "mime_type"),
    [
        ("JPEG", "image/jpeg"),
        ("PNG", "image/png"),
        ("WEBP", "image/webp"),
    ],
)
def test_chat_attachment_accepts_only_decodable_supported_photos(
    image_format: str,
    mime_type: str,
) -> None:
    client = _client()
    _, _, _, remitter, order = _seed_reported_order(client, owner_id=836, remitter_id=837)

    accepted = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, f"valid_{image_format.lower()}_chat_photo"),
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


def test_chat_attachment_rejects_declared_mime_that_does_not_match_content() -> None:
    client = _client()
    _, _, _, remitter, order = _seed_reported_order(client, owner_id=838, remitter_id=839)

    response = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, "mismatched_chat_photo"),
        files={"file": ("photo.jpg", png_bytes(b"mismatched-chat-photo"), "image/jpeg")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MESSAGE_ATTACHMENT_INVALID"
    assert response.json()["error"]["message"] == "No pudimos aceptar ese archivo. Usa una imagen valida."


def test_business_chat_alert_keeps_only_safe_detection_signal() -> None:
    client = _client()
    owner, _, _, _, order = _seed_reported_order(client, owner_id=812, remitter_id=813)
    sensitive_tail = "PIN 4931 wallet 0x3333333333333333333333333333333333333333"

    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "sensitive_off_platform_msg"), "Content-Type": "application/json"},
        json={"body": f"Hagamos directo conmigo. {sensitive_tail}", "attachment_ids": []},
    )
    notifications = _admin_notifications(client)

    assert created.status_code == 201, created.text
    assert len(notifications) == 1
    notification = notifications[0]
    serialized_alert = notification.summary + json.dumps(notification.metadata_json, default=str)
    assert "directo conmigo" in notification.metadata_json["matched_phrase"]
    assert sensitive_tail not in serialized_alert
    assert "4931" not in serialized_alert
    assert "0x3333333333333333333333333333333333333333" not in serialized_alert


def test_business_chat_alert_failure_does_not_block_saved_message(monkeypatch, caplog) -> None:  # type: ignore[no-untyped-def]
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(client, owner_id=814, remitter_id=815)

    def fail_alert(**_kwargs) -> None:  # type: ignore[no-untyped-def]
        raise RuntimeError("simulated admin notification outage")

    monkeypatch.setattr(client.app.state.admin_notification_service, "order_chat_off_platform_solicitation", fail_alert)
    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(owner, "alert_outage_msg"), "Content-Type": "application/json"},
        json={"body": "Hagamos directo conmigo.", "attachment_ids": []},
    )
    listed = client.get(f"/api/v1/orders/{order['id']}/messages", headers=_bearer(remitter, "req_alert_outage_list"))

    assert created.status_code == 201, created.text
    assert listed.status_code == 200, listed.text
    assert any(
        item["body"] == "Hagamos directo conmigo."
        for item in listed.json()["data"]["items"]
    )
    assert _admin_notifications(client) == []
    failure_record = next(record for record in caplog.records if record.message == "order_chat_off_platform_alert_failed")
    assert failure_record.order_id == order["id"]
    assert failure_record.message_id == created.json()["data"]["message"]["id"]
    assert failure_record.rule_id == "off_platform_platform_bypass"
    assert failure_record.error_code == "RuntimeError"
    assert failure_record.request_id == "req_alert_outage_msg"
    assert "Hagamos directo conmigo" not in caplog.text


def test_message_validation_and_state_rules_are_safe() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(client, owner_id=810, remitter_id=811)
    empty = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "empty_msg"), "Content-Type": "application/json"},
        json={"body": "", "attachment_ids": []},
    )
    stored = client.app.state.order_repository.get_by_id(order["id"])
    client.app.state.order_repository.update_order(stored, status="cancelled")
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
        files={"file": ("chat-proof.png", png_bytes(b"chat-proof"), "image/png")},
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


def test_message_attachment_view_url_is_participant_only_and_does_not_expose_storage() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_reported_order(client, owner_id=822, remitter_id=823)
    other = _login(client, 824, "message_attachment_other")
    admin = _login(client, 825, "message_attachment_admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    uploaded = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, "attach_view_url"),
        files={"file": ("chat-proof.png", png_bytes(b"chat-view-proof"), "image/png")},
    )
    attachment_id = uploaded.json()["data"]["attachment"]["id"]
    created = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "msg_attach_view_url"), "Content-Type": "application/json"},
        json={"body": "", "attachment_ids": [attachment_id]},
    )

    business_view = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments/{attachment_id}/view-url",
        headers=_bearer(owner, "req_business_attachment_view"),
    )
    client_view = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments/{attachment_id}/view-url",
        headers=_bearer(remitter, "req_client_attachment_view"),
    )
    other_view = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments/{attachment_id}/view-url",
        headers=_bearer(other, "req_other_attachment_view"),
    )
    admin_view = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments/{attachment_id}/view-url",
        headers=_bearer(admin, "req_admin_attachment_view"),
    )

    assert uploaded.status_code == 201, uploaded.text
    assert created.status_code == 201, created.text
    assert business_view.status_code == 200, business_view.text
    assert client_view.status_code == 200, client_view.text
    assert other_view.status_code == 404
    assert admin_view.status_code == 404
    assert business_view.headers["Cache-Control"] == "private, no-store"
    payload = business_view.json()["data"]
    assert payload["url"]
    assert payload["expires_in_seconds"] <= 300
    assert payload["download_filename"].endswith(".png")
    serialized = business_view.text + client_view.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "storage_path" not in serialized
    assert "private/message_attachments" not in serialized
    assert "signed_url" not in serialized
    assert "message_attachment_viewed" in _event_types(client)


def test_slice_50c_payment_report_appears_in_order_chat_with_proof_for_business() -> None:
    client = _client()
    owner = _login(client, 826, "owner_826")
    _, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key="slice50c_chat_ad")
    remitter = _login(client, 827, "remitter_827")
    order = _create_order(client, remitter, ad["id"], key="slice50c_chat_order")
    _share_zelle(client, owner, order["id"], key="slice50c_chat_share_zelle")
    evidence = client.post(
        f"/api/v1/orders/{order['id']}/payment-evidence",
        headers=_headers(remitter, "slice50c_chat_payment_evidence"),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", png_bytes(b"slice50c-proof"), "image/png")},
    )
    assert evidence.status_code == 201, evidence.text
    evidence_data = evidence.json()["data"]
    report = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={**_headers(remitter, "slice50c_chat_payment_report"), "Content-Type": "application/json"},
        json={
            "payment_type": "zelle",
            "payment_amount": "50.00",
            "proof_file_id": evidence_data["file"]["id"],
            "pending_payment_report_id": evidence_data["pending_payment_report_id"],
        },
    )
    assert report.status_code == 201, report.text

    thread = client.get(
        f"/api/v1/orders/{order['id']}/messages",
        headers=_bearer(owner, "req_slice50c_business_chat_after_report"),
    )

    assert thread.status_code == 200, thread.text
    data = thread.json()["data"]
    assert data["order"]["id"] == order["id"]
    assert data["order"]["status"] == "payment_reported"
    assert data["capabilities"]["can_confirm_payment"] is True
    report_messages = [
        message
        for message in data["system_messages"]
        if message["id"].startswith("system:payment-reported:")
    ]
    assert len(report_messages) == 1
    assert "Cliente marco Pago enviado" in report_messages[0]["body"]
    assert report_messages[0]["attachments"][0]["id"] == evidence_data["file"]["id"]
    assert report_messages[0]["attachments"][0]["mime_type"] == "image/png"

    view = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments/{evidence_data['file']['id']}/view-url",
        headers=_headers(owner, "slice50c_business_view_payment_proof"),
    )
    assert view.status_code == 200, view.text
    assert view.headers["Cache-Control"] == "private, no-store"
    assert view.json()["data"]["download_filename"].endswith(".png")
    serialized = thread.text + view.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "storage_path" not in serialized
    assert "private/payment_evidence" not in serialized
    assert "payment_evidence_viewed_from_chat" in _event_types(client)


def test_open_dispute_from_payment_reported_keeps_credits_and_ad_state_and_enables_dispute_messages() -> None:
    client = _client()
    owner, business, ad, remitter, order = _seed_reported_order(client, owner_id=830, remitter_id=831)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before = wallet_before.blocked_credits
    consumed_before = wallet_before.consumed_credits

    evidence = client.post(
        f"/api/v1/orders/{order['id']}/message-attachments",
        headers=_headers(remitter, "dispute_evidence"),
        files={"file": ("dispute-proof.png", png_bytes(b"dispute-proof"), "image/png")},
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


def test_business_reports_payment_problem_with_exact_reason_and_idempotency() -> None:
    client = _client()
    owner, business, ad, _, order = _seed_reported_order(client, owner_id=832, remitter_id=833)
    other_owner = _login(client, 834, "other_business_owner")
    _approved_business_with_method(client, other_owner, credits=1)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    report_before = client.app.state.order_repository.get_submitted_payment_report_for_order(order["id"])
    reservation_before = client.app.state.capacity_repository.get_reservation(order["id"])
    payload = {
        "reason": "payment_not_received_or_incomplete",
        "description": "El pago reportado no aparece completo.",
        "evidence_file_ids": [],
    }

    invalid_reason = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(owner, "business_payment_problem_invalid"), "Content-Type": "application/json"},
        json={**payload, "reason": "amount_incorrect"},
    )
    foreign = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(other_owner, "business_payment_problem_foreign"), "Content-Type": "application/json"},
        json=payload,
    )
    assert invalid_reason.status_code == 400
    assert invalid_reason.json()["error"]["code"] == "DISPUTE_REASON_REQUIRED"
    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "ORDER_NOT_FOUND"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "payment_reported"
    assert client.app.state.dispute_repository.disputes == {}

    opened = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(owner, "business_payment_problem"), "Content-Type": "application/json"},
        json=payload,
    )
    replay = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(owner, "business_payment_problem"), "Content-Type": "application/json"},
        json=payload,
    )
    mismatch = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(owner, "business_payment_problem"), "Content-Type": "application/json"},
        json={**payload, "description": "Una carga distinta."},
    )

    assert opened.status_code == 201, opened.text
    assert opened.json()["data"]["dispute"]["reason"] == "payment_not_received_or_incomplete"
    assert opened.json()["data"]["dispute"]["previous_order_status"] == "payment_reported"
    assert replay.status_code == 201
    assert replay.json()["data"]["dispute"]["id"] == opened.json()["data"]["dispute"]["id"]
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "disputed"
    assert client.app.state.order_repository.get_submitted_payment_report_for_order(order["id"]).status == report_before.status == "submitted"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    assert client.app.state.capacity_repository.get_reservation(order["id"]).status == reservation_before.status == "reserved"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.blocked_credits == wallet_before.blocked_credits
    assert wallet_after.consumed_credits == wallet_before.consumed_credits
    assert len(client.app.state.dispute_repository.disputes) == 1
    assert len([event for event in client.app.state.dispute_repository.events if event.event_type == "dispute_opened"]) == 1
    dispute_jobs = [
        job
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.notification_type == "order_disputed_parties_admin" and job.order_id == order["id"]
    ]
    assert len(dispute_jobs) == 4
    serialized_jobs = json.dumps([job.__dict__ for job in dispute_jobs], default=str)
    assert payload["description"] not in serialized_jobs
    assert payload["reason"] not in serialized_jobs
    assert "account_value" not in serialized_jobs
    assert "storage_path" not in serialized_jobs


def test_business_payment_problem_requires_submitted_payment_report() -> None:
    client = _client()
    owner, _, _, _, order = _seed_reported_order(client, owner_id=835, remitter_id=836)
    report = client.app.state.order_repository.get_submitted_payment_report_for_order(order["id"])
    assert report is not None
    client.app.state.order_repository.payment_reports.pop(report.id)

    response = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(owner, "business_payment_problem_missing_report"), "Content-Type": "application/json"},
        json={
            "reason": "payment_not_received_or_incomplete",
            "description": "El pago reportado no aparece completo.",
            "evidence_file_ids": [],
        },
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "PAYMENT_REPORT_NOT_FOUND"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "payment_reported"
    assert client.app.state.dispute_repository.disputes == {}


def test_open_dispute_effects_for_rejected_confirmed_and_delivered_states_are_contract_safe() -> None:
    client = _client()

    owner_rejected, business_rejected, ad_rejected, remitter_rejected, order_rejected = _seed_reported_order(client, owner_id=840, remitter_id=841)
    _seed_historical_payment_rejected(client, order_rejected["id"])
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
    assert listing.headers["Cache-Control"] == "private, no-store"
    assert listing.json()["data"]["items"][0]["status"] == "open"
    assert detail.status_code == 200, detail.text
    assert detail.headers["Cache-Control"] == "private, no-store"
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
