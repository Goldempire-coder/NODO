from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

from fastapi.testclient import TestClient
from psycopg.types.json import Jsonb

from app.modules.credits.onchain import OnchainVerificationResult

BOT_TOKEN = "123456:test-bot-token"
BUSINESS_INTAKE_BOT_TOKEN = "123456:test-business-intake-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"
BASE_WALLET = "0x1111111111111111111111111111111111111111"
BASE_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-admin-operational-notifications",
        "NODO_BUILD_ID": "pytest-admin-operational-notifications",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "BUSINESS_INTAKE_BOT_TOKEN": BUSINESS_INTAKE_BOT_TOKEN,
        "JWT_SECRET": JWT_SECRET,
        "JWT_REFRESH_SECRET": JWT_REFRESH_SECRET,
        "AUTH_INIT_DATA_MAX_AGE_SECONDS": "86400",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "2592000",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
        "BUSINESS_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "BUSINESS_RATE_LIMIT_WINDOW_SECONDS": "60",
        "NODO_CREDIT_RECEIVING_WALLET_BASE": BASE_WALLET,
        "ONCHAIN_CREDIT_MIN_CONFIRMATIONS": "3",
        "ONCHAIN_CREDIT_PURCHASE_TTL_MINUTES": "30",
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.modules.admin_notifications.memory_repository import InMemoryAdminNotificationRepository  # noqa: E402
from app.modules.admin_notifications.service import AdminNotificationService  # noqa: E402
from app.modules.businesses.models import utc_now  # noqa: E402
from app.modules.businesses.pin_security import hash_pin  # noqa: E402
from app.modules.support.postgres_repository import PostgresSupportRepository  # noqa: E402
from app.routes.telegram_bot import telegram_webhook_secret  # noqa: E402


class FakeBaseUsdcVerifier:
    def __init__(self) -> None:
        self.results: dict[str, OnchainVerificationResult] = {}

    def set_result(self, tx_hash: str, result: OnchainVerificationResult) -> None:
        self.results[tx_hash.lower()] = result

    def verify(
        self,
        *,
        tx_hash: str,
        expected_amount_units: int,
        destination_wallet_address: str,
        min_confirmations: int,
        latest_block_number: int | None = None,
    ) -> OnchainVerificationResult:
        return self.results[tx_hash.lower()]


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    client = TestClient(create_app())
    client.app.state.onchain_credit_verifier = FakeBaseUsdcVerifier()
    client.app.state.verify_base_usdc_credit_purchases_worker._verifier = client.app.state.onchain_credit_verifier
    return client


def test_postgres_support_events_adapt_metadata_as_jsonb(monkeypatch) -> None:
    event_id = str(uuid4())
    ticket_id = str(uuid4())
    user_id = str(uuid4())
    metadata = {"scope": "business_general", "category": "technical_issue"}
    captured: dict = {}

    class FakeCursor:
        def fetchone(self) -> dict:
            return {
                "id": event_id,
                "ticket_id": ticket_id,
                "actor_user_id": user_id,
                "actor_role": "business_owner",
                "event_type": "support_ticket_created",
                "from_status": None,
                "to_status": "open",
                "reason": None,
                "metadata_json": metadata,
                "created_at": utc_now(),
            }

    class FakeConnection:
        def execute(self, sql: str, params: tuple) -> FakeCursor:
            captured["params"] = params
            return FakeCursor()

        def commit(self) -> None:
            captured["committed"] = True

    class FakeConnectionContext:
        def __enter__(self) -> FakeConnection:
            return FakeConnection()

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

    repository = PostgresSupportRepository("postgresql://unused")
    monkeypatch.setattr(repository, "_connect", lambda: FakeConnectionContext())

    repository.create_event(
        ticket_id=ticket_id,
        actor_user_id=user_id,
        actor_role="business_owner",
        event_type="support_ticket_created",
        to_status="open",
        metadata_json=metadata,
    )

    assert isinstance(captured["params"][-1], Jsonb)
    assert captured["params"][-1].obj == metadata
    assert captured["committed"] is True


def test_admin_notification_enqueue_logging_avoids_reserved_fields(caplog) -> None:
    service = AdminNotificationService(repository=InMemoryAdminNotificationRepository())
    caplog.set_level(logging.INFO, logger="app.modules.admin_notifications.service")

    notification, created = service.enqueue(
        notification_type="business_support_ticket_created",
        priority="attention",
        source_surface="business_mini_app",
        resource_type="support_ticket",
        resource_id=str(uuid4()),
        title="Nuevo ticket de negocio",
        summary="Nuevo ticket de negocio requiere revision.",
        action_route="admin://support-ticket/test",
        dedupe_key=f"support_ticket:{uuid4()}:business_created",
        metadata={"scope": "business_general"},
        request_id="req_support_notification_logging",
    )

    assert created is True
    assert notification.status == "unread"
    record = next(record for record in caplog.records if record.getMessage() == "admin_notification_enqueued")
    assert record.notification_created is True


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


def _make_admin(client: TestClient, telegram_id: int, role: str = "admin") -> dict:
    login = _login(client, telegram_id, f"{role}_{telegram_id}")
    client.app.state.user_repository.set_user_role(login["user"]["id"], role)
    login["user"]["role"] = role
    return login


def _create_business(client: TestClient, login: dict, key: str, *, approved: bool = True) -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, key), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": f"Casa {key}", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201, response.text
    business = response.json()["data"]["business"]
    if approved:
        stored = client.app.state.business_repository.get_business(business["id"])
        stored.verification_status = "approved"
        stored.approved_at = stored.updated_at
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
    return business


def _bot_headers(key: str = "bot") -> dict[str, str]:
    return {
        "X-NODO-Bot-Webhook-Secret": telegram_webhook_secret(BUSINESS_INTAKE_BOT_TOKEN),
        "X-Request-Id": f"req_{key}",
    }


def _start_intake(client: TestClient, *, telegram_id: int, chat_id: int, update_id: int) -> dict:
    response = client.post(
        "/api/v1/business-intake/start",
        headers=_bot_headers(f"start_{update_id}"),
        json={"telegram_user_id": telegram_id, "telegram_chat_id": chat_id, "telegram_update_id": update_id, "referral_code": "NODO-TEST"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _contact_intake(client: TestClient, intake_id: str, *, telegram_id: int, chat_id: int, update_id: int) -> None:
    response = client.post(
        f"/api/v1/business-intake/{intake_id}/contact",
        headers=_bot_headers(f"contact_{update_id}"),
        json={
            "telegram_update_id": update_id,
            "telegram_user_id": telegram_id,
            "telegram_chat_id": chat_id,
            "contact_user_id": telegram_id,
            "contact_phone": "+584121234567",
        },
    )
    assert response.status_code == 200, response.text


def _upload_intake_document(client: TestClient, intake_id: str, *, update_id: int) -> None:
    response = client.post(
        f"/api/v1/business-intake/{intake_id}/documents",
        headers=_bot_headers(f"doc_{update_id}"),
        data={"document_kind": "identity_document", "telegram_update_id": update_id},
        files={"file": ("doc.pdf", b"private-document", "application/pdf")},
    )
    assert response.status_code == 201, response.text


def _submit_intake(client: TestClient, intake_id: str, *, telegram_id: int, chat_id: int, update_id: int) -> None:
    response = client.post(
        f"/api/v1/business-intake/{intake_id}/submit",
        headers=_bot_headers(f"submit_{update_id}"),
        json={
            "telegram_update_id": update_id,
            "telegram_user_id": telegram_id,
            "telegram_chat_id": chat_id,
            "business_name": "Casa Operativa",
            "business_tax_id": "J-12345678-9",
            "responsible_name": "Persona Responsable",
            "responsible_id_number": "V-12345678",
            "city": "Caracas",
            "business_phone": "+582121234567",
            "operation": "both",
            "banks": ["Mercantil"],
            "methods": ["zelle", "usdt_trc20"],
            "min_amount_usd": "20.00",
            "max_amount_usd": "500.00",
            "daily_limit_usd": "1000.00",
            "schedule": "Lunes a viernes",
            "references": ["@casaoperativa"],
        },
    )
    assert response.status_code == 200, response.text


def _base_payment(client: TestClient, login: dict, package_code: str = "starter", key: str = "base") -> dict:
    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(login, key), "Content-Type": "application/json"},
        json={"package_code": package_code, "token_symbol": "USDC"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _tx_hash(seed: str) -> str:
    return "0x" + hashlib.sha256(seed.encode("utf-8")).hexdigest()


def _verification(tx_hash: str, *, status: str = "under_review") -> OnchainVerificationResult:
    return OnchainVerificationResult(
        chain_id=8453,
        token_contract_address=BASE_USDC,
        destination_wallet_address=BASE_WALLET,
        tx_hash=tx_hash.lower(),
        tx_from_address="0x2222222222222222222222222222222222222222",
        tx_to_address=BASE_WALLET,
        tx_amount_units=10_000_000,
        tx_block_number=123,
        tx_log_index=0,
        confirmations=6,
        verification_status=status,
        error_code=None,
    )


def _admin_notifications(client: TestClient, admin: dict) -> list[dict]:
    response = client.get("/api/v1/admin/notifications?limit=20", headers=_bearer(admin, "req_admin_notifications"))
    assert response.status_code == 200, response.text
    return response.json()["data"]["items"]


def test_admin_notifications_api_rbac_states_and_redaction() -> None:
    client = _client()
    admin = _make_admin(client, 31001, "admin")
    support = _make_admin(client, 31002, "support")
    remitter = _login(client, 31003, "remitter")
    service = client.app.state.admin_notification_service
    notification, _created = service.enqueue(
        notification_type="business_support_ticket_created",
        priority="attention",
        source_surface="business_mini_app",
        resource_type="support_ticket",
        title="Ticket privado",
        summary="Resumen seguro",
        dedupe_key="test:admin-notification:redaction",
        metadata={
            "scope": "business_credit",
            "storage_path": "private/file.pdf",
            "account_value": "owner@example.com",
            "tx_hash": _tx_hash("unsafe"),
            "safe_code": "VISIBLE",
        },
        request_id="req_admin_notification_test",
    )
    service.enqueue(
        notification_type="business_intake_submitted",
        priority="info",
        source_surface="business_intake_bot",
        resource_type="business_intake",
        resource_id=str(uuid4()),
        title="Solicitud enviada",
        summary="Solicitud de negocio pendiente.",
        dedupe_key="test:admin-notification:non-support",
        metadata={"status": "submitted"},
        request_id="req_admin_notification_test_non_support",
    )

    forbidden = client.get("/api/v1/admin/notifications", headers=_bearer(remitter, "req_forbidden_notifications"))
    listed = client.get("/api/v1/admin/notifications", headers=_bearer(admin, "req_list_notifications"))
    count = client.get("/api/v1/admin/notifications/unread-count", headers=_bearer(support, "req_count_notifications"))
    support_read = client.post(f"/api/v1/admin/notifications/{notification.id}/read", headers=_bearer(support, "req_support_read_notification"))
    admin_read = client.post(f"/api/v1/admin/notifications/{notification.id}/read", headers=_bearer(admin, "req_admin_read_notification"))
    support_dismiss = client.post(f"/api/v1/admin/notifications/{notification.id}/dismiss", headers=_bearer(support, "req_support_dismiss_notification"))
    admin_resolve = client.post(f"/api/v1/admin/notifications/{notification.id}/resolve", headers=_bearer(admin, "req_admin_resolve_notification"))

    assert forbidden.status_code == 403
    assert listed.status_code == 200
    payload = next(item for item in listed.json()["data"]["items"] if item["id"] == notification.id)
    assert payload["metadata"] == {"scope": "business_credit", "safe_code": "VISIBLE"}
    assert count.json()["data"]["unread_count"] == 2
    assert count.json()["data"]["support_unread_count"] == 1
    assert support_read.status_code == 403
    assert admin_read.status_code == 200
    assert admin_read.json()["data"]["notification"]["status"] == "read"
    assert support_dismiss.status_code == 403
    assert admin_resolve.status_code == 200
    assert admin_resolve.json()["data"]["notification"]["status"] == "resolved"


def test_duplicate_admin_notification_preserves_operator_state() -> None:
    client = _client()
    admin = _make_admin(client, 31011, "admin")
    service = client.app.state.admin_notification_service
    notification, created = service.enqueue(
        notification_type="base_usdc_credit_purchase_stuck",
        priority="high",
        source_surface="base_usdc_watcher",
        resource_type="credit_purchase",
        resource_id=str(uuid4()),
        title="Compra USDC requiere revision",
        summary="Compra starter quedo vencida.",
        dedupe_key="test:admin-notification:reopen",
        metadata={"status": "pending_payment"},
        request_id="req_reopen_first",
    )
    assert created is True

    read = client.post(f"/api/v1/admin/notifications/{notification.id}/read", headers=_bearer(admin, "req_read_before_reopen"))
    assert read.status_code == 200, read.text
    assert read.json()["data"]["notification"]["status"] == "read"

    repeated_after_read, created_after_read = service.enqueue(
        notification_type="base_usdc_credit_purchase_stuck",
        priority="high",
        source_surface="base_usdc_watcher",
        resource_type="credit_purchase",
        resource_id=notification.resource_id,
        title="Compra USDC requiere revision",
        summary="Compra starter sigue vencida.",
        dedupe_key="test:admin-notification:reopen",
        metadata={"status": "pending_payment"},
        request_id="req_reopen_second",
    )
    count_after_read = client.get("/api/v1/admin/notifications/unread-count", headers=_bearer(admin, "req_count_after_read_repeat"))
    unread_after_read = client.get("/api/v1/admin/notifications?status=unread", headers=_bearer(admin, "req_list_after_read_repeat"))

    assert created_after_read is False
    assert repeated_after_read.id == notification.id
    assert repeated_after_read.status == "read"
    assert repeated_after_read.read_at is not None
    assert repeated_after_read.read_by_user_id == admin["user"]["id"]
    assert count_after_read.json()["data"]["unread_count"] == 0
    assert all(item["id"] != notification.id for item in unread_after_read.json()["data"]["items"])

    resolved = client.post(f"/api/v1/admin/notifications/{notification.id}/resolve", headers=_bearer(admin, "req_resolve_before_repeat"))
    assert resolved.status_code == 200, resolved.text
    assert resolved.json()["data"]["notification"]["status"] == "resolved"

    repeated_after_resolve, created_after_resolve = service.enqueue(
        notification_type="base_usdc_credit_purchase_stuck",
        priority="high",
        source_surface="base_usdc_watcher",
        resource_type="credit_purchase",
        resource_id=notification.resource_id,
        title="Compra USDC requiere revision",
        summary="Compra starter sigue vencida.",
        dedupe_key="test:admin-notification:reopen",
        metadata={"status": "pending_payment"},
        request_id="req_reopen_third",
    )
    count_after_resolve = client.get("/api/v1/admin/notifications/unread-count", headers=_bearer(admin, "req_count_after_resolve_repeat"))
    unread_after_resolve = client.get("/api/v1/admin/notifications?status=unread", headers=_bearer(admin, "req_list_after_resolve_repeat"))

    assert created_after_resolve is False
    assert repeated_after_resolve.id == notification.id
    assert repeated_after_resolve.status == "resolved"
    assert repeated_after_resolve.resolved_at is not None
    assert repeated_after_resolve.resolved_by_user_id == admin["user"]["id"]
    assert count_after_resolve.json()["data"]["unread_count"] == 0
    assert all(item["id"] != notification.id for item in unread_after_resolve.json()["data"]["items"])


def test_business_intake_document_and_submit_create_admin_notifications() -> None:
    client = _client()
    admin = _make_admin(client, 31101, "admin")
    started = _start_intake(client, telegram_id=31102, chat_id=41102, update_id=100)
    _contact_intake(client, started["id"], telegram_id=31102, chat_id=41102, update_id=101)
    _upload_intake_document(client, started["id"], update_id=102)
    _submit_intake(client, started["id"], telegram_id=31102, chat_id=41102, update_id=103)

    notifications = _admin_notifications(client, admin)
    types = {item["notification_type"] for item in notifications}
    assert {"business_document_uploaded", "business_intake_submitted"}.issubset(types)
    serialized = json.dumps(notifications)
    assert "storage_path" not in serialized
    assert "private-document" not in serialized


def test_business_support_ticket_created_from_business_creates_admin_notification() -> None:
    client = _client()
    admin = _make_admin(client, 31201, "admin")
    owner = _login(client, 31202, "business_support_owner")
    _create_business(client, owner, "support_notify")

    response = client.post(
        "/api/v1/support/tickets",
        headers={**_headers(owner, "business_support_ticket"), "Content-Type": "application/json", "X-NODO-Surface": "business_mini_app"},
        json={"scope": "business_general", "category": "technical_issue", "subject": "No abre pantalla 0x3333333333333333333333333333333333333333", "message": "Mensaje privado que no debe ir a notificaciones."},
    )
    assert response.status_code == 201, response.text

    notifications = _admin_notifications(client, admin)
    support_notification = next(item for item in notifications if item["notification_type"] == "business_support_ticket_created")
    assert support_notification["resource_type"] == "support_ticket"
    assert support_notification["business_id"] is not None
    assert "No abre pantalla" not in json.dumps(support_notification)
    assert "0x3333333333333333333333333333333333333333" not in json.dumps(support_notification)
    assert "Mensaje privado" not in json.dumps(support_notification)


def test_business_support_message_created_from_business_creates_admin_notification() -> None:
    client = _client()
    admin = _make_admin(client, 31211, "admin")
    owner = _login(client, 31212, "business_support_message_owner")
    business = _create_business(client, owner, "support_msg_notify")

    ticket_response = client.post(
        "/api/v1/support/tickets",
        headers={**_headers(owner, "business_support_message_ticket"), "Content-Type": "application/json", "X-NODO-Surface": "business_mini_app"},
        json={"scope": "business_general", "category": "technical_issue", "subject": "Boton no responde", "message": "Mensaje inicial privado."},
    )
    assert ticket_response.status_code == 201, ticket_response.text
    ticket = ticket_response.json()["data"]

    initial_unread = client.get("/api/v1/admin/notifications?status=unread", headers=_bearer(admin, "req_support_message_initial_unread"))
    assert initial_unread.status_code == 200, initial_unread.text
    for notification in initial_unread.json()["data"]["items"]:
        if notification["resource_type"] == "support_ticket":
            read_response = client.post(f"/api/v1/admin/notifications/{notification['id']}/read", headers=_bearer(admin, f"req_support_message_read_{notification['id']}"))
            assert read_response.status_code == 200, read_response.text

    count_before_message = client.get("/api/v1/admin/notifications/unread-count", headers=_bearer(admin, "req_support_message_count_before"))
    assert count_before_message.status_code == 200, count_before_message.text
    assert count_before_message.json()["data"]["support_unread_count"] == 0

    message_response = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/messages",
        headers={**_headers(owner, "business_support_message_reply"), "Content-Type": "application/json", "X-NODO-Surface": "business_mini_app"},
        json={"body": "Hola soporte, mi wallet privada no debe salir en la campana 0x3333333333333333333333333333333333333333."},
    )
    assert message_response.status_code == 201, message_response.text
    message = message_response.json()["data"]["message"]

    count = client.get("/api/v1/admin/notifications/unread-count", headers=_bearer(admin, "req_support_message_unread_count"))
    unread = client.get("/api/v1/admin/notifications?status=unread", headers=_bearer(admin, "req_support_message_unread_list"))

    assert count.status_code == 200, count.text
    assert count.json()["data"]["support_unread_count"] == 1
    assert unread.status_code == 200, unread.text
    notifications = unread.json()["data"]["items"]
    message_notification = next(item for item in notifications if item["notification_type"] == "business_support_message_created")
    assert message_notification["resource_type"] == "support_ticket"
    assert message_notification["resource_id"] == ticket["id"]
    assert message_notification["business_id"] == business["id"]
    assert message_notification["actor_user_id"] == owner["user"]["id"]
    assert message_notification["action_route"] == f"admin://support-ticket/{ticket['id']}"
    assert message_notification["metadata"] == {
        "category": "technical_issue",
        "message_id": message["id"],
        "scope": "business_general",
        "status": "waiting_support",
    }
    serialized = json.dumps(message_notification)
    assert "wallet privada" not in serialized
    assert "0x3333333333333333333333333333333333333333" not in serialized


def test_client_support_ticket_created_from_client_creates_admin_notification() -> None:
    client = _client()
    admin = _make_admin(client, 31221, "admin")
    remitter = _login(client, 31222, "client_support_notify")

    response = client.post(
        "/api/v1/support/tickets",
        headers={**_headers(remitter, "client_support_ticket"), "Content-Type": "application/json", "X-NODO-Surface": "client_mini_app"},
        json={
            "scope": "client_general",
            "category": "technical_issue",
            "subject": "No puedo abrir soporte 0x3333333333333333333333333333333333333333",
            "message": "Mensaje del cliente que no debe ir a notificaciones.",
        },
    )
    assert response.status_code == 201, response.text
    ticket = response.json()["data"]

    notifications = _admin_notifications(client, admin)
    support_notification = next(item for item in notifications if item["notification_type"] == "client_support_ticket_created")
    assert support_notification["resource_type"] == "support_ticket"
    assert support_notification["resource_id"] == ticket["id"]
    assert support_notification["business_id"] is None
    assert support_notification["actor_user_id"] == remitter["user"]["id"]
    assert support_notification["action_route"] == f"admin://support-ticket/{ticket['id']}"
    assert support_notification["metadata"] == {
        "category": "technical_issue",
        "scope": "client_general",
        "status": "open",
    }
    serialized = json.dumps(support_notification)
    assert "No puedo abrir soporte" not in serialized
    assert "0x3333333333333333333333333333333333333333" not in serialized
    assert "Mensaje del cliente" not in serialized


def test_client_support_message_created_from_client_creates_admin_notification() -> None:
    client = _client()
    admin = _make_admin(client, 31231, "admin")
    remitter = _login(client, 31232, "client_support_message_notify")

    ticket_response = client.post(
        "/api/v1/support/tickets",
        headers={**_headers(remitter, "client_support_message_ticket"), "Content-Type": "application/json", "X-NODO-Surface": "client_mini_app"},
        json={"scope": "client_general", "category": "technical_issue", "subject": "Boton de ayuda no responde", "message": "Mensaje inicial privado."},
    )
    assert ticket_response.status_code == 201, ticket_response.text
    ticket = ticket_response.json()["data"]

    initial_unread = client.get("/api/v1/admin/notifications?status=unread", headers=_bearer(admin, "req_client_support_message_initial_unread"))
    assert initial_unread.status_code == 200, initial_unread.text
    for notification in initial_unread.json()["data"]["items"]:
        if notification["resource_type"] == "support_ticket":
            read_response = client.post(f"/api/v1/admin/notifications/{notification['id']}/read", headers=_bearer(admin, f"req_client_support_message_read_{notification['id']}"))
            assert read_response.status_code == 200, read_response.text

    count_before_message = client.get("/api/v1/admin/notifications/unread-count", headers=_bearer(admin, "req_client_support_message_count_before"))
    assert count_before_message.status_code == 200, count_before_message.text
    assert count_before_message.json()["data"]["support_unread_count"] == 0

    message_response = client.post(
        f"/api/v1/support/tickets/{ticket['id']}/messages",
        headers={**_headers(remitter, "client_support_message_reply"), "Content-Type": "application/json", "X-NODO-Surface": "client_mini_app"},
        json={"body": "Hola soporte, mi token privado no debe salir en la campana 0x3333333333333333333333333333333333333333."},
    )
    assert message_response.status_code == 201, message_response.text
    message = message_response.json()["data"]["message"]

    count = client.get("/api/v1/admin/notifications/unread-count", headers=_bearer(admin, "req_client_support_message_unread_count"))
    unread = client.get("/api/v1/admin/notifications?status=unread", headers=_bearer(admin, "req_client_support_message_unread_list"))

    assert count.status_code == 200, count.text
    assert count.json()["data"]["support_unread_count"] == 1
    assert unread.status_code == 200, unread.text
    notifications = unread.json()["data"]["items"]
    message_notification = next(item for item in notifications if item["notification_type"] == "client_support_message_created")
    assert message_notification["resource_type"] == "support_ticket"
    assert message_notification["resource_id"] == ticket["id"]
    assert message_notification["business_id"] is None
    assert message_notification["actor_user_id"] == remitter["user"]["id"]
    assert message_notification["action_route"] == f"admin://support-ticket/{ticket['id']}"
    assert message_notification["metadata"] == {
        "category": "technical_issue",
        "message_id": message["id"],
        "scope": "client_general",
        "status": "waiting_support",
    }
    serialized = json.dumps(message_notification)
    assert "token privado" not in serialized
    assert "0x3333333333333333333333333333333333333333" not in serialized


def test_base_usdc_under_review_and_telegram_failed_permanent_notify_admin() -> None:
    client = _client()
    admin = _make_admin(client, 31301, "admin")
    owner = _login(client, 31302, "credit_notify_owner")
    _create_business(client, owner, "credit_notify")
    payment = _base_payment(client, owner, key="base_under_review")
    tx_hash = _tx_hash("admin-operational-under-review")
    client.app.state.onchain_credit_verifier.set_result(tx_hash, _verification(tx_hash, status="under_review"))

    tx_response = client.post(
        f"/api/v1/business/credits/purchases/{payment['purchase']['id']}/tx-hash",
        headers={**_headers(owner, "base_under_review_tx"), "Content-Type": "application/json"},
        json={"tx_hash": tx_hash},
    )
    assert tx_response.status_code == 200, tx_response.text
    stuck_payment = _base_payment(client, owner, key="base_stuck")
    stuck_purchase = client.app.state.credit_repository.get_purchase(stuck_payment["purchase"]["id"])
    stuck_purchase.expires_at = utc_now() - timedelta(minutes=1)
    watcher_result = client.app.state.verify_base_usdc_credit_purchases_worker.run_once(request_id="req_stuck_credit_watcher")

    client.app.state.job_repository.enqueue_notification(
        notification_type="order_created_business",
        recipient_user_id=str(uuid4()),
        recipient_role=None,
        order_id=None,
        business_id=None,
        dispute_id=None,
        scheduled_for=utc_now(),
        attempts=0,
        max_attempts=1,
        dedupe_key="admin-operational:missing-recipient",
        metadata_json={"channel": "telegram", "target_surface": "business_mini_app", "message_text": "Abrir orden", "payload": {"secret": "do-not-emit"}},
    )
    sender_result = client.app.state.notification_sender_worker.run(now=utc_now(), request_id="req_sender_failed_permanent")

    notifications = _admin_notifications(client, admin)
    types = {item["notification_type"] for item in notifications}
    assert "base_usdc_credit_purchase_under_review" in types
    assert "base_usdc_credit_purchase_stuck" in types
    assert "telegram_notification_failed_permanent" in types
    assert sender_result["counters"]["failed_permanent"] == 1
    assert watcher_result["stuck_or_expired"] == 1
    assert "payload" not in json.dumps(notifications).lower()
    assert tx_hash not in json.dumps(notifications)


def test_base_usdc_watcher_notifies_all_paginated_stuck_purchases() -> None:
    client = _client(ONCHAIN_CREDIT_WATCHER_BATCH_SIZE="2")
    admin = _make_admin(client, 31311, "admin")
    owner = _login(client, 31312, "credit_notify_paginated_owner")
    _create_business(client, owner, "credit_notify_paginated")

    payments = [_base_payment(client, owner, key=f"base_paginated_stuck_{index}") for index in range(3)]
    for payment in payments:
        purchase = client.app.state.credit_repository.get_purchase(payment["purchase"]["id"])
        purchase.expires_at = utc_now() - timedelta(minutes=1)

    watcher_result = client.app.state.verify_base_usdc_credit_purchases_worker.run_once(request_id="req_paginated_stuck_credit_watcher")
    notifications = _admin_notifications(client, admin)
    stuck_notifications = [item for item in notifications if item["notification_type"] == "base_usdc_credit_purchase_stuck"]

    assert watcher_result["stuck_or_expired"] == 3
    assert len(stuck_notifications) == 3


def test_admin_operational_notifications_frontend_and_migration_contracts() -> None:
    root = Path(__file__).resolve().parents[3]
    admin_api = (root / "apps" / "web" / "src" / "api" / "admin.ts").read_text(encoding="utf-8")
    shell = (root / "apps" / "web" / "src" / "screens" / "admin-web" / "AdminWebShell.tsx").read_text(encoding="utf-8")
    hook = (root / "apps" / "web" / "src" / "hooks" / "admin-web" / "useAdminNotificationsModel.ts").read_text(encoding="utf-8")
    up = (root / "database" / "migrations" / "0032_admin_operational_notifications.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0032_admin_operational_notifications.down.sql").read_text(encoding="utf-8")

    assert "/api/v1/admin/notifications" in admin_api
    assert "adminNotificationsUnreadCount" in shell
    assert "admin://business-intake/" in hook
    assert "admin://order/" in hook
    assert "openOrder" in hook
    assert "applyUnreadCount(0, 0)" not in hook
    assert 'setUnreadCountState("stale")' in hook
    assert "Contador sin actualizar" in shell
    assert "notification_jobs" not in up
    assert "create table if not exists admin_notifications" in up
    assert "drop table if exists admin_notifications" in down
    assert "storage_path" not in shell
    assert "account_value" not in shell
