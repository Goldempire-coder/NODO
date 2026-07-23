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


TEST_BOT_CREDENTIAL = "123456:test-bot-credential"


def _set_env() -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-44b",
        "NODO_BUILD_ID": "pytest-admin-chat-evidence",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": TEST_BOT_CREDENTIAL,
        "JWT_SECRET": "test-access-credential",
        "JWT_REFRESH_SECRET": "test-refresh-credential",
        "AUTH_INIT_DATA_MAX_AGE_SECONDS": "86400",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "2592000",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
        "BUSINESS_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "BUSINESS_RATE_LIMIT_WINDOW_SECONDS": "60",
    }
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.modules.businesses.models import utc_now  # noqa: E402
from app.modules.businesses.pin_security import hash_pin  # noqa: E402


def _client() -> TestClient:
    _set_env()
    return TestClient(create_app())


def _signed_init_data(telegram_id: int, username: str) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": username}, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", TEST_BOT_CREDENTIAL.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def _login(client: TestClient, telegram_id: int, username: str, role: str = "remitter") -> dict:
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
    if role != "remitter":
        client.app.state.user_repository.set_user_role(login["user"]["id"], role)
    return login


def _headers(login: dict, key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _bearer(login: dict, request_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": request_id}


def _seed_reported_order(client: TestClient, *, owner_id: int, remitter_id: int) -> tuple[dict, dict, dict]:
    owner = _login(client, owner_id, f"owner_{owner_id}")
    created_business = client.post(
        "/api/v1/businesses",
        headers={**_headers(owner, f"business_{owner_id}"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": f"Casa {owner_id}", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert created_business.status_code == 201, created_business.text
    business = created_business.json()["data"]["business"]
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.verification_status = "approved"
    stored_business.approved_at = stored_business.updated_at
    stored_business.max_order_amount_usd *= 20
    stored_owner = client.app.state.user_repository.get_user_by_id(owner["user"]["id"])
    link = client.app.state.business_repository.create_access_link(
        business_id=business["id"],
        user_id=owner["user"]["id"],
        telegram_id_snapshot=stored_owner.telegram_id,
        role_in_business="owner",
        linked_by_admin_id=owner["user"]["id"],
        reason="test_admin_chat_evidence",
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
    client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=2, created_by=owner["user"]["id"])
    ad_response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, f"ad_{owner_id}"), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment.id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )
    assert ad_response.status_code == 201, ad_response.text
    remitter = _login(client, remitter_id, f"remitter_{remitter_id}")
    order_response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, f"order_{remitter_id}"), "Content-Type": "application/json"},
        json={
            "ad_id": ad_response.json()["data"]["ad"]["id"],
            "amount_usd": "50.00",
            "receiver_data": {"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Receptor Test"},
        },
    )
    assert order_response.status_code == 201, order_response.text
    order = order_response.json()["data"]["order"]
    client.app.state.order_repository.get_by_id(order["id"]).status = "payment_reported"
    return owner, remitter, order


def _create_message(client: TestClient, login: dict, order_id: str, body: str, key: str) -> dict:
    response = client.post(
        f"/api/v1/orders/{order_id}/messages",
        headers={**_headers(login, key), "Content-Type": "application/json"},
        json={"body": body, "attachment_ids": []},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["message"]


@pytest.mark.parametrize("terminal_status", ["completed", "cancelled"])
def test_admin_can_read_terminal_order_chat_evidence_with_safe_highlight_and_audit(terminal_status: str) -> None:
    client = _client()
    owner, remitter, order = _seed_reported_order(client, owner_id=4501, remitter_id=4502)
    _create_message(client, remitter, order["id"], "Cliente reporta contexto de la orden.", "client_context")
    highlighted = _create_message(client, owner, order["id"], "Negocio propone continuar fuera de la plataforma.", "business_context")
    attachment_id = str(uuid4())
    file_id = str(uuid4())
    client.app.state.chat_repository.create_attachment_file(
        file_id=file_id,
        attachment_id=attachment_id,
        owner_user_id=owner["user"]["id"],
        order_id=order["id"],
        storage_path=f"private/order-chat/{attachment_id}/evidence.png",
        mime_type="image/png",
        size_bytes=128,
    )
    client.app.state.chat_repository.attach_to_message(attachment_ids=[attachment_id], message_id=highlighted["id"])
    client.app.state.order_repository.get_by_id(order["id"]).status = terminal_status
    admin = _login(client, 4503, "admin_4503", role="admin")

    response = client.get(
        f"/api/v1/admin/orders/{order['id']}/chat-evidence?highlight_message_id={highlighted['id']}&limit=50",
        headers=_bearer(admin, "req_admin_chat_evidence"),
    )

    assert response.status_code == 200, response.text
    assert response.headers["cache-control"] == "private, no-store"
    payload = response.json()["data"]
    assert payload["order_id"] == order["id"]
    assert payload["highlight_message_id"] == highlighted["id"]
    assert payload["highlight_found"] is True
    highlighted_payload = next(item for item in payload["items"] if item["message_id"] == highlighted["id"])
    assert highlighted_payload["highlighted"] is True
    assert highlighted_payload["body"] == "Negocio propone continuar fuera de la plataforma."
    assert highlighted_payload["attachments"] == [
        {
            "attachment_id": attachment_id,
            "mime_type": "image/png",
            "size_bytes": 128,
            "download_available": False,
        }
    ]
    serialized = json.dumps(payload).lower()
    for forbidden_key in ("file_asset_id", "storage_path", "signed_url", "account_value", "access_token", "refresh_token", "pin"):
        assert forbidden_key not in serialized
    audit = [event for event in client.app.state.audit_writer.events if event.event_type == "admin_order_chat_viewed"]
    assert len(audit) == 1
    assert audit[0].resource_id == order["id"]
    assert audit[0].metadata_json == {
        "message_count": 2,
        "highlight_requested": True,
        "highlight_found": True,
        "page_direction": "initial",
    }
    assert highlighted_payload["body"] not in json.dumps(audit[0].__dict__, default=str)


def test_admin_chat_evidence_rejects_non_admin_actors_and_foreign_highlight() -> None:
    client = _client()
    owner, remitter, order = _seed_reported_order(client, owner_id=4511, remitter_id=4512)
    message = _create_message(client, owner, order["id"], "Contexto visible solo en evidencia autorizada.", "business_message")
    admin = _login(client, 4513, "admin_4513", role="admin")
    foreign_message = client.app.state.chat_repository.create_message(
        order_id=str(uuid4()),
        sender_user_id=owner["user"]["id"],
        sender_role="business_owner",
        body="Mensaje de otra orden",
        idempotency_key="foreign_message",
    )

    owner_response = client.get(
        f"/api/v1/admin/orders/{order['id']}/chat-evidence",
        headers=_bearer(owner, "req_owner_admin_chat"),
    )
    remitter_response = client.get(
        f"/api/v1/admin/orders/{order['id']}/chat-evidence",
        headers=_bearer(remitter, "req_remitter_admin_chat"),
    )
    foreign_highlight = client.get(
        f"/api/v1/admin/orders/{order['id']}/chat-evidence?highlight_message_id={foreign_message.id}",
        headers=_bearer(admin, "req_foreign_highlight"),
    )
    valid_highlight = client.get(
        f"/api/v1/admin/orders/{order['id']}/chat-evidence?highlight_message_id={message['id']}",
        headers=_bearer(admin, "req_valid_highlight"),
    )

    assert owner_response.status_code == 403
    assert remitter_response.status_code == 403
    assert foreign_highlight.status_code == 404
    assert foreign_highlight.json()["error"]["code"] == "MESSAGE_NOT_FOUND"
    assert valid_highlight.status_code == 200


def test_admin_chat_evidence_includes_highlight_outside_latest_page() -> None:
    client = _client()
    owner, _, order = _seed_reported_order(client, owner_id=4521, remitter_id=4522)
    messages = [
        client.app.state.chat_repository.create_message(
            order_id=order["id"],
            sender_user_id=owner["user"]["id"],
            sender_role="business_owner",
            body=f"Mensaje de contexto {index}",
            idempotency_key=f"evidence_page_{index}",
        )
        for index in range(55)
    ]
    admin = _login(client, 4523, "admin_4523", role="admin")

    response = client.get(
        f"/api/v1/admin/orders/{order['id']}/chat-evidence?highlight_message_id={messages[0].id}&limit=50",
        headers=_bearer(admin, "req_old_highlight"),
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert len(payload["items"]) <= 50
    assert payload["highlight_found"] is True
    assert any(item["message_id"] == messages[0].id and item["highlighted"] for item in payload["items"])
    assert payload["newer_cursor"] is not None


def test_admin_chat_evidence_frontend_contract_is_read_only_and_preserves_highlight() -> None:
    root = Path(__file__).resolve().parents[3]
    admin_api = (root / "apps/web/src/api/admin.ts").read_text(encoding="utf-8")
    notifications_hook = (root / "apps/web/src/hooks/admin-web/useAdminNotificationsModel.ts").read_text(encoding="utf-8")
    orders_hook = (root / "apps/web/src/hooks/admin-web/useAdminOrdersModel.ts").read_text(encoding="utf-8")
    evidence_hook = (root / "apps/web/src/hooks/admin-web/useAdminOrderChatEvidenceModel.ts").read_text(encoding="utf-8")
    panel = (root / "apps/web/src/screens/admin-web/AdminOrderChatEvidencePanel.tsx").read_text(encoding="utf-8")
    styles = (root / "apps/web/src/app/admin-web.css").read_text(encoding="utf-8")

    assert "/chat-evidence" in admin_api
    assert "notification.metadata.message_id" in notifications_hook
    assert "highlightMessageId" in notifications_hook
    assert "loadOrderChatEvidence" in orders_hook
    assert "void chatEvidence.loadOrderChatEvidence" in orders_hook
    assert "admin_order_chat_evidence_load" in evidence_hook
    assert "activeOrder.current?.orderId !== orderId" in evidence_hook
    assert "current?.order_id === active.orderId" in evidence_hook
    assert "currentRequest.current !== requestSequence" in evidence_hook
    assert "AdminOrderChatEvidencePanel" in panel
    assert "textarea" not in panel
    assert "Enviar" not in panel
    assert "dangerouslySetInnerHTML" not in panel
    assert "overflow-y: auto" in styles
    for forbidden_key in ("storage_path", "file_asset_id", "signed_url", "account_value"):
        assert forbidden_key not in panel
