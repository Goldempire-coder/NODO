from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.modules.orders.models import utc_now


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-10",
        "NODO_BUILD_ID": "pytest-jobs-notifications-build",
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
from app.modules.businesses.pin_security import hash_pin  # noqa: E402
from app.modules.notifications.telegram_sender import NotificationSenderWorker, TelegramNotificationError  # noqa: E402
from app.modules.orders.receiver_details import receiver_payload_hash  # noqa: E402


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
    content = f"proof:{order_id}:{key}".encode("utf-8")
    response = client.post(
        f"/api/v1/orders/{order_id}/payment-evidence",
        headers=_headers(remitter, key),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", content, "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _report_payment(client: TestClient, remitter: dict, order: dict, *, key: str = "report") -> dict:
    if not client.app.state.chat_repository.has_business_message_containing(
        order_id=order["id"],
        text="owner@example.com",
    ):
        stored_order = client.app.state.order_repository.get_by_id(order["id"])
        business = client.app.state.business_repository.get_business(
            stored_order.business_id
        )
        client.app.state.chat_repository.create_message(
            order_id=order["id"],
            sender_user_id=business.owner_user_id,
            sender_role="business_owner",
            body="Zelle del negocio: owner@example.com",
            idempotency_key=f"fixture_share_{order['id']}",
        )
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


def _seed_order(client: TestClient, *, owner_id: int, remitter_id: int) -> tuple[dict, dict, dict, dict, dict]:
    owner = _login(client, owner_id, f"owner_{owner_id}")
    business, method_id = _approved_business_with_method(client, owner, credits=3)
    ad = _create_ad(client, owner, method_id, key=f"ad_{owner_id}")
    remitter = _login(client, remitter_id, f"remitter_{remitter_id}")
    order = _create_order(client, remitter, ad["id"], key=f"order_{remitter_id}")
    return owner, business, ad, remitter, order


def _confirm_payment(client: TestClient, owner: dict, order_id: str, key: str) -> None:
    response = client.post(
        f"/api/v1/business/orders/{order_id}/confirm-payment",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )
    assert response.status_code == 200, response.text


def _mark_delivered(client: TestClient, owner: dict, order_id: str, key: str) -> None:
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


def _run_job(client: TestClient, now) -> dict:  # type: ignore[no-untyped-def]
    return client.app.state.expire_and_escalate_orders_worker.run(current_time=now, batch_size=100, dry_run=False, request_id="req_job_test")


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def _notifications_by_type(client: TestClient, notification_type: str) -> list:
    return [
        notification
        for notification in client.app.state.job_repository.notification_jobs.values()
        if notification.notification_type == notification_type
    ]


def _notification_snapshot(notification) -> dict:  # type: ignore[no-untyped-def]
    return {
        "status": notification.status,
        "attempts": notification.attempts,
        "scheduled_for": notification.scheduled_for,
        "last_error_code": notification.last_error_code,
        "metadata_json": dict(notification.metadata_json or {}),
    }


class _FakeTelegramAdapter:
    def __init__(self, *failures: TelegramNotificationError) -> None:
        self.failures = list(failures)
        self.sent: list[dict] = []

    def send_message(self, *, bot_token: str, chat_id: int, text: str, reply_markup: dict | None = None) -> None:
        if self.failures:
            raise self.failures.pop(0)
        self.sent.append({"bot_token": bot_token, "chat_id": chat_id, "text": text, "reply_markup": reply_markup})


def test_slice_36_immediate_order_notifications_are_enqueued_deduped_and_private() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner, business, ad, remitter, order = _seed_order(client, owner_id=1100, remitter_id=1101)
    business_owner_id = client.app.state.business_repository.get_business(business["id"]).owner_user_id

    created_notifications = _notifications_by_type(client, "order_created_business")
    assert len(created_notifications) == 1
    assert created_notifications[0].recipient_user_id == business_owner_id
    assert created_notifications[0].metadata_json["target_surface"] == "business_mini_app"
    assert created_notifications[0].metadata_json["action_url"].endswith(f"/business/?view=business-order-detail&order_id={order['id']}")

    replay = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "order_1101"), "Content-Type": "application/json"},
        json={
            "ad_id": ad["id"],
            "amount_usd": "50.00",
            "receiver_data": {"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Receptor Test"},
        },
    )
    assert replay.status_code == 201, replay.text
    assert len(_notifications_by_type(client, "order_created_business")) == 1

    _report_payment(client, remitter, order, key="slice36_reported")
    assert len(_notifications_by_type(client, "payment_reported_business")) == 1
    _confirm_payment(client, owner, order["id"], "slice36_confirm")
    assert len(_notifications_by_type(client, "payment_confirmed_client")) == 1
    _mark_delivered(client, owner, order["id"], "slice36_deliver")
    assert len(_notifications_by_type(client, "order_delivered_client")) == 1

    owner2, _, _, remitter2, order2 = _seed_order(client, owner_id=1102, remitter_id=1103)
    _report_payment(client, remitter2, order2, key="slice36_reject_reported")
    rejected = client.post(
        f"/api/v1/business/orders/{order2['id']}/reject-payment-report",
        headers={**_headers(owner2, "slice36_reject"), "Content-Type": "application/json"},
        json={"reason": "No reconozco el pago"},
    )
    assert rejected.status_code == 200, rejected.text
    assert len(_notifications_by_type(client, "payment_rejected_client")) == 1

    combined = json.dumps([n.__dict__ for n in client.app.state.job_repository.notification_jobs.values()], default=str)
    assert "owner@example.com" not in combined
    assert "account_value" not in combined
    assert "storage_path" not in combined
    assert "signed_url" not in combined
    assert BOT_TOKEN not in combined


def test_slice_48a_manual_cancel_notifies_business_once_with_safe_metadata() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    _, business, _, remitter, order = _seed_order(client, owner_id=1110, remitter_id=1111)
    business_owner_id = client.app.state.business_repository.get_business(business["id"]).owner_user_id
    payload = {"reason": "business_unavailable", "payment_not_sent_confirmed": True}
    headers = {**_headers(remitter, "slice48a_cancel"), "Content-Type": "application/json"}

    first = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=headers, json=payload)
    replay = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=headers, json=payload)

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    notifications = _notifications_by_type(client, "order_cancelled_payment_not_reported")
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.recipient_user_id == business_owner_id
    assert notification.metadata_json["channel"] == "telegram"
    assert notification.metadata_json["target_surface"] == "business_mini_app"
    assert "antes de reportar pago" in notification.metadata_json["message_text"]
    assert notification.metadata_json["order_status"] == "cancelled"
    combined = json.dumps(notification.__dict__, default=str)
    for forbidden in [
        "owner@example.com",
        "+584121234567",
        "V12345678",
        "account_value",
        "storage_path",
        "signed_url",
    ]:
        assert forbidden not in combined


def test_slice_49a_business_cannot_attend_cancels_releases_and_notifies_client_once() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner, business, ad, remitter, order = _seed_order(
        client,
        owner_id=1112,
        remitter_id=1113,
    )
    headers = {
        **_headers(owner, "slice49a_cannot_attend"),
        "Content-Type": "application/json",
    }

    first = client.post(
        f"/api/v1/business/orders/{order['id']}/cannot-attend",
        headers=headers,
    )
    replay = client.post(
        f"/api/v1/business/orders/{order['id']}/cannot-attend",
        headers=headers,
    )

    assert first.status_code == 200, first.text
    assert replay.status_code == 200, replay.text
    assert first.json()["data"]["order"]["status"] == "cancelled"
    assert first.json()["data"]["order"]["cancel_reason"] == "business_unavailable"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "active"
    reservation = client.app.state.capacity_repository.get_reservation(order["id"])
    assert reservation.status == "released"
    notifications = _notifications_by_type(
        client,
        "order_cancelled_business_unavailable",
    )
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification.recipient_user_id == remitter["user"]["id"]
    assert notification.metadata_json["target_surface"] == "client_mini_app"
    assert notification.metadata_json["order_status"] == "cancelled"
    combined = json.dumps(notification.__dict__, default=str)
    for forbidden in [
        "owner@example.com",
        "+584121234567",
        "V12345678",
        "account_value",
        "storage_path",
        "signed_url",
        "reason_text",
    ]:
        assert forbidden not in combined
    assert client.app.state.capacity_repository.get_snapshot(
        business=client.app.state.business_repository.get_business(business["id"])
    ).reserved_capacity_usd == Decimal("0.00")


def test_slice_49a_business_cannot_attend_rejects_after_payment_report() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner, _, _, remitter, order = _seed_order(
        client,
        owner_id=1114,
        remitter_id=1115,
    )
    _report_payment(client, remitter, order, key="slice49a_report_before_decline")

    response = client.post(
        f"/api/v1/business/orders/{order['id']}/cannot-attend",
        headers=_headers(owner, "slice49a_decline_after_report"),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_STATE_CONFLICT"
    assert _notifications_by_type(
        client,
        "order_cancelled_business_unavailable",
    ) == []


def test_slice_36_notification_enqueue_logging_does_not_break_success_response(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level(logging.INFO, logger="app.modules.notifications.order_notifications")
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    _, _, _, _, order = _seed_order(client, owner_id=1104, remitter_id=1105)

    assert order["public_order_code"].startswith("NODO-")
    assert any(
        record.name == "app.modules.notifications.order_notifications"
        and record.getMessage() == "notification_job_enqueued"
        and getattr(record, "notification_created", None) is True
        for record in caplog.records
    )


def test_slice_36_dispute_enqueues_parties_and_admin_support_without_resolving() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    _, business, _, remitter, order = _seed_order(client, owner_id=1110, remitter_id=1111)
    _report_payment(client, remitter, order, key="slice36_dispute_report")
    response = client.post(
        f"/api/v1/orders/{order['id']}/disputes",
        headers={**_headers(remitter, "slice36_dispute"), "Content-Type": "application/json"},
        json={"reason": "amount_incorrect", "description": "Monto incorrecto", "evidence_file_ids": []},
    )
    assert response.status_code == 201, response.text
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "disputed"

    jobs = _notifications_by_type(client, "order_disputed_parties_admin")
    assert len(jobs) == 4
    assert {job.recipient_role for job in jobs if job.recipient_role} == {"admin", "support"}
    assert {job.recipient_user_id for job in jobs if job.recipient_user_id} == {
        remitter["user"]["id"],
        client.app.state.business_repository.get_business(business["id"]).owner_user_id,
    }


def test_slice_36_sender_success_retryable_and_permanent_failures_are_stateful() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    _, _, _, _, _ = _seed_order(client, owner_id=1120, remitter_id=1121)
    notification = _notifications_by_type(client, "order_created_business")[0]

    success_adapter = _FakeTelegramAdapter()
    success_worker = NotificationSenderWorker(
        settings=client.app.state.settings,
        job_repository=client.app.state.job_repository,
        user_repository=client.app.state.user_repository,
        adapter=success_adapter,
    )
    result = success_worker.run(now=utc_now(), request_id="req_slice36_sender_success")
    assert result["counters"]["sent"] == 1
    assert notification.status == "sent"
    assert notification.attempts == 1
    assert notification.metadata_json["delivery_state"] == "sent"
    assert success_adapter.sent[0]["reply_markup"]["inline_keyboard"][0][0]["text"] == "Abrir orden"

    client_retry = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    _, _, _, _, _ = _seed_order(client_retry, owner_id=1122, remitter_id=1123)
    retry_notification = _notifications_by_type(client_retry, "order_created_business")[0]
    retry_worker = NotificationSenderWorker(
        settings=client_retry.app.state.settings,
        job_repository=client_retry.app.state.job_repository,
        user_repository=client_retry.app.state.user_repository,
        adapter=_FakeTelegramAdapter(TelegramNotificationError("TELEGRAM_BOT_SEND_FAILED", retryable=True)),
    )
    retry_result = retry_worker.run(now=utc_now(), request_id="req_slice36_sender_retry")
    assert retry_result["counters"]["retryable_failed"] == 1
    assert retry_notification.status == "pending"
    assert retry_notification.attempts == 1
    assert retry_notification.last_error_code == "TELEGRAM_BOT_SEND_FAILED"
    assert retry_notification.metadata_json["delivery_state"] == "retryable_failed"

    client_permanent = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    _, _, _, _, _ = _seed_order(client_permanent, owner_id=1124, remitter_id=1125)
    permanent_notification = _notifications_by_type(client_permanent, "order_created_business")[0]
    permanent_worker = NotificationSenderWorker(
        settings=client_permanent.app.state.settings,
        job_repository=client_permanent.app.state.job_repository,
        user_repository=client_permanent.app.state.user_repository,
        adapter=_FakeTelegramAdapter(TelegramNotificationError("TELEGRAM_CHAT_UNAVAILABLE", retryable=False)),
    )
    permanent_result = permanent_worker.run(now=utc_now(), request_id="req_slice36_sender_permanent")
    assert permanent_result["counters"]["failed_permanent"] == 1
    assert permanent_notification.status == "failed"
    assert permanent_notification.failed_at is not None
    assert permanent_notification.last_error_code == "TELEGRAM_CHAT_UNAVAILABLE"
    assert permanent_notification.metadata_json["delivery_state"] == "failed_permanent"


def test_slice_36a_sender_scope_guard_only_claims_supported_immediate_telegram_jobs() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner, business, _, remitter, order = _seed_order(client, owner_id=1126, remitter_id=1127)
    valid_notification = _notifications_by_type(client, "order_created_business")[0]
    now = utc_now()

    def enqueue_non_processable(notification_type: str, *, recipient_user_id: str | None, recipient_role: str | None, metadata_json: dict) -> object:
        notification, _ = client.app.state.job_repository.enqueue_notification(
            notification_type=notification_type,
            recipient_user_id=recipient_user_id,
            recipient_role=recipient_role,
            order_id=order["id"],
            business_id=business["id"],
            dispute_id=None,
            scheduled_for=now - timedelta(seconds=1),
            dedupe_key=f"slice36a:{notification_type}:{recipient_user_id or recipient_role}:{len(client.app.state.job_repository.notification_jobs)}",
            metadata_json=metadata_json,
        )
        return notification

    business_status_notification, _ = client.app.state.job_repository.enqueue_notification(
        notification_type="business_suspended_owner",
        recipient_user_id=owner["user"]["id"],
        recipient_role=None,
        order_id=None,
        business_id=business["id"],
        dispute_id=None,
        scheduled_for=now - timedelta(seconds=1),
        dedupe_key=f"slice36a:business_suspended_owner:{business['id']}",
        metadata_json={
            "channel": "telegram",
            "target_surface": "business_mini_app",
            "message_text": "Tu negocio fue suspendido temporalmente.",
            "action_text": "Abrir NODO Negocio",
            "action_url": "https://app.example.test/business/",
        },
    )
    non_processable = [
        enqueue_non_processable(
            "order_business_response_warning",
            recipient_user_id=owner["user"]["id"],
            recipient_role=None,
            metadata_json={"channel": "telegram", "target_surface": "business_mini_app", "message_text": "legacy warning"},
        ),
        enqueue_non_processable(
            "order_cancelled_payment_not_reported",
            recipient_user_id=remitter["user"]["id"],
            recipient_role=None,
            metadata_json={},
        ),
        enqueue_non_processable(
            "delivered_reminder_12h",
            recipient_user_id=remitter["user"]["id"],
            recipient_role=None,
            metadata_json={"channel": "telegram", "target_surface": "client_mini_app", "message_text": "legacy reminder"},
        ),
        enqueue_non_processable(
            "order_disputed_parties_admin",
            recipient_user_id=None,
            recipient_role="admin",
            metadata_json={"channel": "telegram", "target_surface": "admin_web", "message_text": "admin role job"},
        ),
        enqueue_non_processable(
            "order_created_business",
            recipient_user_id=owner["user"]["id"],
            recipient_role=None,
            metadata_json={"channel": "internal", "target_surface": "business_mini_app", "message_text": "wrong channel"},
        ),
        enqueue_non_processable(
            "payment_reported_business",
            recipient_user_id=owner["user"]["id"],
            recipient_role=None,
            metadata_json={"channel": "telegram", "target_surface": "business_mini_app"},
        ),
        enqueue_non_processable(
            "payment_confirmed_client",
            recipient_user_id=remitter["user"]["id"],
            recipient_role=None,
            metadata_json={"channel": "telegram", "target_surface": "client_mini_app", "message_text": "   "},
        ),
    ]
    before = {notification.id: _notification_snapshot(notification) for notification in non_processable}

    adapter = _FakeTelegramAdapter()
    worker = NotificationSenderWorker(
        settings=client.app.state.settings,
        job_repository=client.app.state.job_repository,
        user_repository=client.app.state.user_repository,
        adapter=adapter,
    )
    result = worker.run(now=now, request_id="req_slice36a_sender_scope_guard")

    assert result["counters"]["processed"] == 2
    assert result["counters"]["sent"] == 2
    assert valid_notification.status == "sent"
    assert business_status_notification.status == "sent"
    assert len(adapter.sent) == 2
    assert {item["reply_markup"]["inline_keyboard"][0][0]["text"] for item in adapter.sent} == {
        "Abrir orden",
        "Abrir NODO Negocio",
    }
    for notification in non_processable:
        assert _notification_snapshot(notification) == before[notification.id]


def test_slice_48b1_sender_claims_chat_and_support_participant_notifications() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner, business, _, remitter, order = _seed_order(client, owner_id=1128, remitter_id=1129)
    now = utc_now()
    expected_types = {
        "order_message_created_business": (owner["user"]["id"], "business_mini_app"),
        "order_message_created_client": (remitter["user"]["id"], "client_mini_app"),
        "support_message_created_participant": (remitter["user"]["id"], "client_mini_app"),
    }
    for notification_type, (recipient_user_id, target_surface) in expected_types.items():
        client.app.state.job_repository.enqueue_notification(
            notification_type=notification_type,
            recipient_user_id=recipient_user_id,
            recipient_role=None,
            order_id=order["id"] if notification_type.startswith("order_") else None,
            business_id=business["id"],
            dispute_id=None,
            scheduled_for=now - timedelta(seconds=1),
            dedupe_key=f"slice48b1:{notification_type}:{recipient_user_id}",
            metadata_json={
                "channel": "telegram",
                "target_surface": target_surface,
                "message_text": "Tienes una actualizacion segura en NODO.",
                "action_text": "Abrir",
                "action_url": "https://app.example.test/",
            },
        )

    adapter = _FakeTelegramAdapter()
    worker = NotificationSenderWorker(
        settings=client.app.state.settings,
        job_repository=client.app.state.job_repository,
        user_repository=client.app.state.user_repository,
        adapter=adapter,
    )
    result = worker.run(now=now, request_id="req_slice48b1_sender")

    assert result["counters"]["processed"] == 4
    assert result["counters"]["sent"] == 4
    assert len(adapter.sent) == 4
    assert {
        job.notification_type
        for job in client.app.state.job_repository.notification_jobs.values()
        if job.status == "sent"
    }.issuperset(expected_types)


def test_slice_36a_postgres_claim_filters_telegram_scope_before_update() -> None:
    root = Path(__file__).resolve().parents[3]
    postgres_source = (root / "apps" / "api" / "app" / "modules" / "jobs" / "postgres_repository.py").read_text(encoding="utf-8")
    sender_source = (root / "apps" / "api" / "app" / "modules" / "notifications" / "telegram_sender.py").read_text(encoding="utf-8")

    claim_method = postgres_source.split("def list_due_telegram_notifications", 1)[1].split("def update_notification", 1)[0]
    assert "recipient_user_id is not null" in claim_method
    assert "notification_type in" in claim_method
    assert "metadata_json->>'channel' = 'telegram'" in claim_method
    assert "metadata_json->>'target_surface' in ('business_mini_app', 'client_mini_app')" in claim_method
    assert "nullif(trim(metadata_json->>'message_text'), '') is not null" in claim_method
    assert "update notification_jobs" in claim_method
    assert sender_source.count("list_due_telegram_notifications") == 1
    assert "list_due_notifications(" not in sender_source


def test_slice_36b_order_notification_sender_runs_from_lifespan_with_safe_defaults() -> None:
    root = Path(__file__).resolve().parents[3]
    main_source = (root / "apps" / "api" / "app" / "main.py").read_text(encoding="utf-8")
    config_source = (root / "apps" / "api" / "app" / "core" / "config.py").read_text(encoding="utf-8")

    assert "order_notification_sender_enabled" in config_source
    assert 'ORDER_NOTIFICATION_SENDER_ENABLED", source.get("APP_ENV") != "test"' in config_source
    assert "ORDER_NOTIFICATION_SENDER_INTERVAL_SECONDS" in config_source
    assert "ORDER_NOTIFICATION_SENDER_BATCH_SIZE" in config_source
    assert "order_notification_sender_enabled" in main_source
    assert "_order_notification_sender_loop" in main_source
    assert "task_group.start_soon(_order_notification_sender_loop" in main_source
    assert "notification_sender_worker.run" in main_source
    assert "scheduler_order_notification_sender" in main_source
    assert "order_notification_sender_finished" in main_source
    assert "order_notification_sender_failed" in main_source
    assert "bot_token" not in main_source.split("async def _order_notification_sender_loop", 1)[1]


def test_slice_37_business_status_notification_sender_uses_business_bot_and_safe_button() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner = _login(client, 1128, "owner_1128")
    business, _ = _approved_business_with_method(client, owner, credits=0)
    now = utc_now()
    notification, _ = client.app.state.job_repository.enqueue_notification(
        notification_type="business_reactivated_owner",
        recipient_user_id=owner["user"]["id"],
        recipient_role=None,
        order_id=None,
        business_id=business["id"],
        dispute_id=None,
        scheduled_for=now - timedelta(seconds=1),
        dedupe_key=f"slice37:business_reactivated_owner:{business['id']}",
        metadata_json={
            "channel": "telegram",
            "target_surface": "business_mini_app",
            "message_text": "Tu negocio fue reactivado. Ya puedes operar en NODO.",
            "action_text": "Abrir NODO Negocio",
            "action_url": "https://app.example.test/business/",
        },
    )

    adapter = _FakeTelegramAdapter()
    worker = NotificationSenderWorker(
        settings=client.app.state.settings,
        job_repository=client.app.state.job_repository,
        user_repository=client.app.state.user_repository,
        adapter=adapter,
    )
    result = worker.run(now=now, request_id="req_slice37_business_status_sender")

    assert result["counters"]["sent"] == 1
    assert notification.status == "sent"
    assert adapter.sent[0]["bot_token"] == "456:test-business-token"
    assert adapter.sent[0]["text"] == "Tu negocio fue reactivado. Ya puedes operar en NODO."
    assert adapter.sent[0]["reply_markup"]["inline_keyboard"][0][0] == {
        "text": "Abrir NODO Negocio",
        "web_app": {"url": "https://app.example.test/business/"},
    }


def test_slice_38_user_status_notification_sender_reaches_suspended_business_owner() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner = _login(client, 1129, "owner_1129")
    business, _ = _approved_business_with_method(client, owner, credits=0)
    client.app.state.user_repository.set_user_status(owner["user"]["id"], "restricted")
    now = utc_now()
    notification, _ = client.app.state.job_repository.enqueue_notification(
        notification_type="user_suspended_account",
        recipient_user_id=owner["user"]["id"],
        recipient_role=None,
        order_id=None,
        business_id=business["id"],
        dispute_id=None,
        scheduled_for=now - timedelta(seconds=1),
        dedupe_key=f"slice38:user_suspended_account:{owner['user']['id']}",
        metadata_json={
            "channel": "telegram",
            "target_surface": "business_mini_app",
            "message_text": "Tu cuenta fue suspendida temporalmente. No podras operar en NODO mientras revisamos el caso.",
            "action_text": "Abrir NODO Negocio",
            "action_url": "https://app.example.test/business/",
        },
    )

    adapter = _FakeTelegramAdapter()
    worker = NotificationSenderWorker(
        settings=client.app.state.settings,
        job_repository=client.app.state.job_repository,
        user_repository=client.app.state.user_repository,
        adapter=adapter,
    )
    result = worker.run(now=now, request_id="req_slice38_user_status_sender")

    assert result["counters"]["sent"] == 1
    assert notification.status == "sent"
    assert adapter.sent[0]["bot_token"] == "456:test-business-token"
    assert adapter.sent[0]["chat_id"] == 1129
    assert adapter.sent[0]["reply_markup"]["inline_keyboard"][0][0] == {
        "text": "Abrir NODO Negocio",
        "web_app": {"url": "https://app.example.test/business/"},
    }


def test_slice_39_business_access_notification_sender_uses_business_bot_and_safe_message() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner = _login(client, 1130, "owner_1130")
    business, _ = _approved_business_with_method(client, owner, credits=0)
    now = utc_now()
    notification, _ = client.app.state.job_repository.enqueue_notification(
        notification_type="business_access_suspended_owner",
        recipient_user_id=owner["user"]["id"],
        recipient_role=None,
        order_id=None,
        business_id=business["id"],
        dispute_id=None,
        scheduled_for=now - timedelta(seconds=1),
        dedupe_key=f"slice39:business_access_suspended_owner:{business['id']}",
        metadata_json={
            "channel": "telegram",
            "target_surface": "business_mini_app",
            "message_text": "Tu acceso a NODO Negocio fue suspendido temporalmente. No podras operar ese negocio mientras revisamos el caso.",
            "action_text": "Abrir NODO Negocio",
            "action_url": "https://app.example.test/business/",
        },
    )

    adapter = _FakeTelegramAdapter()
    worker = NotificationSenderWorker(
        settings=client.app.state.settings,
        job_repository=client.app.state.job_repository,
        user_repository=client.app.state.user_repository,
        adapter=adapter,
    )
    result = worker.run(now=now, request_id="req_slice39_business_access_sender")

    assert result["counters"]["sent"] == 1
    assert notification.status == "sent"
    assert adapter.sent[0]["bot_token"] == "456:test-business-token"
    assert adapter.sent[0]["chat_id"] == 1130
    assert "suspendido" in adapter.sent[0]["text"]
    assert adapter.sent[0]["reply_markup"]["inline_keyboard"][0][0] == {
        "text": "Abrir NODO Negocio",
        "web_app": {"url": "https://app.example.test/business/"},
    }


def test_slice_36_business_offline_blocks_order_and_notification() -> None:
    client = _client(BUSINESS_INTAKE_BOT_TOKEN="456:test-business-token")
    owner = _login(client, 1130, "owner_1130")
    business, method_id = _approved_business_with_method(client, owner, credits=3)
    ad = _create_ad(client, owner, method_id, key="slice36_offline_ad")
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.is_accepting_orders = False
    remitter = _login(client, 1131, "remitter_1131")

    response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "slice36_offline_order"), "Content-Type": "application/json"},
        json={
            "ad_id": ad["id"],
            "amount_usd": "50.00",
            "receiver_data": {"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Receptor Test"},
        },
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_OFFLINE"
    assert _notifications_by_type(client, "order_created_business") == []


def test_waiting_payment_expiry_dry_run_is_non_mutating_then_cancels_and_keeps_ad_hold() -> None:
    client = _client()
    _, business, ad, remitter, order = _seed_order(client, owner_id=1000, remitter_id=1001)
    admin = _login(client, 1002, "admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    past = utc_now() - timedelta(minutes=5)
    client.app.state.order_repository.update_order(stored, payment_report_deadline_at=past, expires_at=past)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before = wallet_before.blocked_credits
    available_before = wallet_before.available_credits

    dry = client.post(
        "/api/v1/admin/jobs/expire-and-escalate-orders/dry-run",
        headers=_headers(admin, "dry_waiting"),
        params={"current_time": utc_now().isoformat()},
    )
    assert dry.status_code == 200, dry.text
    missing_idempotency = client.post(
        "/api/v1/admin/jobs/expire-and-escalate-orders/dry-run",
        headers=_bearer(admin, "req_dry_missing_idempotency"),
        params={"current_time": utc_now().isoformat()},
    )
    assert missing_idempotency.status_code == 400
    assert missing_idempotency.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "waiting_payment"
    assert client.app.state.ad_repository.get_wallet(business["id"]).blocked_credits == wallet_before.blocked_credits
    assert not [
        n
        for n in client.app.state.job_repository.notification_jobs.values()
        if n.notification_type == "order_cancelled_payment_not_reported"
    ]

    result = _run_job(client, utc_now())
    assert result["job_run"]["status"] == "finished"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "cancelled"
    assert client.app.state.order_repository.get_by_id(order["id"]).cancel_reason == "payment_not_reported_in_time"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "active"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.blocked_credits == blocked_before
    assert wallet_after.available_credits == available_before
    assert "order_cancelled_payment_not_reported" in _event_types(client)
    cancelled_notifications = [
        n for n in client.app.state.job_repository.notification_jobs.values() if n.notification_type == "order_cancelled_payment_not_reported"
    ]
    business_owner_id = client.app.state.business_repository.get_business(business["id"]).owner_user_id
    assert len(cancelled_notifications) == 2
    assert {n.recipient_user_id for n in cancelled_notifications} == {remitter["user"]["id"], business_owner_id}
    combined = json.dumps([n.__dict__ for n in client.app.state.job_repository.notification_jobs.values()], default=str)
    assert "order_cancelled_payment_not_reported" in combined
    assert "owner@example.com" not in combined
    assert "storage_path" not in combined


def test_payment_reported_deadline_opens_dispute_and_keeps_credits_blocked_and_ad_in_order() -> None:
    client = _client()
    _, business, ad, remitter, order = _seed_order(client, owner_id=1010, remitter_id=1011)
    _report_payment(client, remitter, order, key="reported_deadline")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    past = utc_now() - timedelta(hours=7)
    client.app.state.order_repository.update_order(stored, business_response_deadline_at=past)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])

    _run_job(client, utc_now())

    updated = client.app.state.order_repository.get_by_id(order["id"])
    assert updated.status == "disputed"
    assert updated.dispute_reason == "business_no_payment_confirmation"
    assert client.app.state.dispute_repository.get_open_for_order(order["id"]) is not None
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    assert client.app.state.ad_repository.get_wallet(business["id"]).blocked_credits == wallet_before.blocked_credits
    assert "order_disputed_business_no_payment_confirmation" in _event_types(client)
    dispute_notifications = [
        n for n in client.app.state.job_repository.notification_jobs.values() if n.notification_type == "order_disputed_business_no_payment_confirmation"
    ]
    assert len(dispute_notifications) == 4
    assert {n.recipient_role for n in dispute_notifications if n.recipient_role} == {"admin", "support"}
    assert {n.recipient_user_id for n in dispute_notifications if n.recipient_user_id} == {
        remitter["user"]["id"],
        client.app.state.business_repository.get_business(business["id"]).owner_user_id,
    }


def test_business_response_and_delivery_warnings_are_deduped_with_canonical_audit_events() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_order(client, owner_id=1015, remitter_id=1016)
    _report_payment(client, remitter, order, key="reported_warning")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    now = utc_now()
    client.app.state.order_repository.update_order(
        stored,
        business_response_warning_at=now - timedelta(minutes=1),
        business_response_deadline_at=now + timedelta(hours=1),
    )

    _run_job(client, now)
    _run_job(client, now)

    assert client.app.state.order_repository.get_by_id(order["id"]).status == "payment_reported"
    response_warnings = [
        n for n in client.app.state.job_repository.notification_jobs.values() if n.notification_type == "order_business_response_warning"
    ]
    assert len(response_warnings) == 1
    assert _event_types(client).count("order_business_response_warning_sent") == 1

    _confirm_payment(client, owner, order["id"], "confirm_warning")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    client.app.state.order_repository.update_order(
        stored,
        delivery_warning_at=now - timedelta(minutes=1),
        delivery_deadline_at=now + timedelta(hours=1),
    )

    _run_job(client, now)
    _run_job(client, now)

    delivery_warnings = [n for n in client.app.state.job_repository.notification_jobs.values() if n.notification_type == "order_delivery_warning"]
    assert len(delivery_warnings) == 1
    assert _event_types(client).count("order_delivery_warning_sent") == 1


def test_payment_confirmed_delivery_deadline_opens_dispute_after_credits_consumed() -> None:
    client = _client()
    owner, business, ad, remitter, order = _seed_order(client, owner_id=1020, remitter_id=1021)
    _report_payment(client, remitter, order, key="confirmed_deadline")
    _confirm_payment(client, owner, order["id"], "confirm_deadline")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    past = utc_now() - timedelta(hours=3)
    client.app.state.order_repository.update_order(stored, delivery_deadline_at=past)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])

    _run_job(client, utc_now())

    updated = client.app.state.order_repository.get_by_id(order["id"])
    assert updated.status == "disputed"
    assert updated.dispute_reason == "business_confirmed_payment_but_not_delivered"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "archived"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.consumed_credits == wallet_before.consumed_credits
    assert wallet_after.blocked_credits == wallet_before.blocked_credits
    assert "order_disputed_business_confirmed_payment_but_not_delivered" in _event_types(client)
    dispute_notifications = [
        n
        for n in client.app.state.job_repository.notification_jobs.values()
        if n.notification_type == "order_disputed_business_confirmed_payment_but_not_delivered"
    ]
    assert len(dispute_notifications) == 4
    assert {n.recipient_role for n in dispute_notifications if n.recipient_role} == {"admin", "support"}


def test_delivered_reminders_are_deduped_and_auto_complete_skips_open_dispute() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_order(client, owner_id=1030, remitter_id=1031)
    _report_payment(client, remitter, order, key="delivered_reminder")
    _confirm_payment(client, owner, order["id"], "confirm_delivered")
    _mark_delivered(client, owner, order["id"], "mark_delivered")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    now = utc_now()
    client.app.state.order_repository.update_order(
        stored,
        delivered_at=now - timedelta(minutes=5),
        auto_complete_warning_12h_at=now + timedelta(hours=1),
        auto_complete_warning_23h_at=now + timedelta(hours=2),
        auto_complete_at=now + timedelta(hours=3),
    )

    _run_job(client, now)
    _run_job(client, now)
    reminders = [item for item in client.app.state.job_repository.notification_jobs.values() if item.notification_type.startswith("delivered_reminder")]
    assert len(reminders) == 1
    assert reminders[0].dedupe_key.endswith(":immediate")
    assert reminders[0].notification_type == "delivered_reminder_immediate"
    assert _event_types(client).count("delivered_reminder_sent") == 1

    client.app.state.order_repository.update_order(stored, auto_complete_warning_12h_at=now - timedelta(minutes=1))
    _run_job(client, now)
    client.app.state.order_repository.update_order(stored, auto_complete_warning_23h_at=now - timedelta(minutes=1))
    _run_job(client, now)
    reminder_types = {item.notification_type for item in client.app.state.job_repository.notification_jobs.values() if item.notification_type.startswith("delivered_reminder")}
    assert {"delivered_reminder_immediate", "delivered_reminder_12h", "delivered_reminder_23h"}.issubset(reminder_types)
    assert _event_types(client).count("delivered_reminder_sent") == 3

    client.app.state.order_repository.update_order(stored, auto_complete_at=now - timedelta(minutes=1))
    _run_job(client, now)
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "completed"
    assert client.app.state.order_repository.get_by_id(order["id"]).completion_reason == "auto_completed_after_24h"
    assert "order_auto_completed_after_24h" in _event_types(client)

    owner2, _, _, remitter2, order2 = _seed_order(client, owner_id=1032, remitter_id=1033)
    _report_payment(client, remitter2, order2, key="delivered_disputed")
    _confirm_payment(client, owner2, order2["id"], "confirm_disputed")
    _mark_delivered(client, owner2, order2["id"], "mark_disputed")
    stored2 = client.app.state.order_repository.get_by_id(order2["id"])
    client.app.state.dispute_repository.create_dispute(
        order_id=order2["id"],
        opened_by_user_id=remitter2["user"]["id"],
        opened_by_role="remitter",
        previous_order_status="delivered",
        reason="payment_mobile_not_received",
        description="No recibido",
    )
    client.app.state.order_repository.update_order(stored2, auto_complete_at=now - timedelta(minutes=1))
    _run_job(client, now)
    assert client.app.state.order_repository.get_by_id(order2["id"]).status == "delivered"


def test_ad_and_founder_expiration_admin_job_endpoints_and_lock_rbac() -> None:
    client = _client()
    owner, business, ad, _, _ = _seed_order(client, owner_id=1040, remitter_id=1041)
    active_ad = client.app.state.ad_repository.get_ad(ad["id"])
    client.app.state.ad_repository.set_status(active_ad, "active")
    active_ad.expires_at = utc_now() - timedelta(days=1)
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.founder_status = "active"
    stored_business.founder_expires_at = utc_now() - timedelta(days=1)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before = wallet_before.blocked_credits
    consumed_before = wallet_before.consumed_credits

    _run_job(client, utc_now())

    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "archived"
    assert client.app.state.business_repository.get_business(business["id"]).founder_status == "expired"
    assert client.app.state.ad_repository.get_wallet(business["id"]).blocked_credits == blocked_before - 1
    assert client.app.state.ad_repository.get_wallet(business["id"]).consumed_credits == consumed_before + 1
    assert {"ad_expired", "credits_consumed", "founder_access_expired"}.issubset(set(_event_types(client)))
    notification_types = {item.notification_type for item in client.app.state.job_repository.notification_jobs.values()}
    assert {"ad_expired", "founder_access_expired"}.issubset(notification_types)
    assert {"job_started", "job_finished"}.issubset(set(_event_types(client)))

    admin = _login(client, 1042, "admin")
    support = _login(client, 1043, "support")
    business_owner = _login(client, 1044, "business_owner")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")
    client.app.state.user_repository.set_user_role(business_owner["user"]["id"], "business_owner")
    listing = client.get("/api/v1/admin/jobs/runs?limit=10", headers=_bearer(support, "req_jobs_support"))
    assert listing.status_code == 200, listing.text
    run_id = listing.json()["data"]["items"][0]["id"]
    detail = client.get(f"/api/v1/admin/jobs/runs/{run_id}", headers=_bearer(admin, "req_jobs_admin_detail"))
    forbidden = client.post("/api/v1/admin/jobs/expire-and-escalate-orders/dry-run", headers=_headers(support, "dry_support"))
    owner_forbidden = client.get("/api/v1/admin/jobs/runs", headers=_bearer(business_owner, "req_jobs_owner"))
    assert detail.status_code == 200, detail.text
    assert forbidden.status_code == 403
    assert owner_forbidden.status_code == 403
    combined = listing.text + detail.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined

    client.app.state.job_lock_manager.acquire("jobs:expire_and_escalate_orders", "external", 300)
    locked = client.app.state.expire_and_escalate_orders_worker.run(current_time=utc_now(), dry_run=False, request_id="req_locked")
    assert locked["job_run"]["status"] == "lock_not_acquired"
    assert locked["job_run"]["error_code"] == "JOB_LOCK_NOT_ACQUIRED"
    assert "job_failed" in _event_types(client)


def test_slice_10_migration_contract_closes_indexes_constraints_and_canonical_names() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0011_slice_10_jobs_notifications.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0011_slice_10_jobs_notifications.down.sql").read_text(encoding="utf-8")

    for required in [
        "job_runs_attempts_non_negative_check",
        "job_runs_terminal_finished_at_check",
        "job_runs_failed_error_check",
        "notification_jobs_type_check",
        "notification_jobs_terminal_timestamp_check",
        "job_runs_job_type_status_created_idx",
        "job_runs_lock_key_idx",
        "notification_jobs_order_type_created_idx",
        "notification_jobs_business_type_created_idx",
        "notification_jobs_dispute_type_created_idx",
        "delivered_reminder_immediate",
        "delivered_reminder_12h",
        "delivered_reminder_23h",
    ]:
        assert required in up

    assert "job_name" not in up
    assert "event_type" not in up

    for reversible in [
        "drop index if exists job_runs_lock_key_idx",
        "drop index if exists notification_jobs_dispute_type_created_idx",
        "drop constraint if exists notification_jobs_type_check",
        "drop constraint if exists job_runs_failed_error_check",
    ]:
        assert reversible in down


def test_slice_36_migration_adds_order_notification_types_reversibly() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0024_slice_36_business_order_notifications.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0024_slice_36_business_order_notifications.down.sql").read_text(encoding="utf-8")

    for notification_type in [
        "order_created_business",
        "payment_reported_business",
        "payment_confirmed_client",
        "payment_rejected_client",
        "order_delivered_client",
        "order_disputed_parties_admin",
    ]:
        assert notification_type in up
        assert notification_type not in down


def test_slice_37_migration_adds_business_status_notification_types_reversibly() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0029_business_status_notifications.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0029_business_status_notifications.down.sql").read_text(encoding="utf-8")

    for notification_type in [
        "business_suspended_owner",
        "business_reactivated_owner",
        "business_blocked_owner",
    ]:
        assert notification_type in up
        assert notification_type not in down
    for notification_type in [
        "order_created_business",
        "payment_reported_business",
        "payment_confirmed_client",
        "payment_rejected_client",
        "order_delivered_client",
        "order_disputed_parties_admin",
    ]:
        assert notification_type in up
        assert notification_type in down
    assert "drop constraint if exists notification_jobs_type_check" in up
    assert "drop constraint if exists notification_jobs_type_check" in down
    assert "event_type" not in up
    assert "telegram_chat_id" not in up


def test_slice_38_migration_adds_admin_user_status_notification_types_reversibly() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0030_admin_user_status_notifications.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0030_admin_user_status_notifications.down.sql").read_text(encoding="utf-8")

    for notification_type in [
        "user_suspended_account",
        "user_reactivated_account",
        "user_blocked_account",
    ]:
        assert notification_type in up
        assert notification_type not in down
    for notification_type in [
        "business_suspended_owner",
        "business_reactivated_owner",
        "business_blocked_owner",
    ]:
        assert notification_type in up
        assert notification_type in down
    assert "drop constraint if exists notification_jobs_type_check" in up
    assert "drop constraint if exists notification_jobs_type_check" in down


def test_slice_39_migration_adds_business_access_status_notification_types_reversibly() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0031_business_access_status_notifications.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0031_business_access_status_notifications.down.sql").read_text(encoding="utf-8")

    for notification_type in [
        "business_access_suspended_owner",
        "business_access_reactivated_owner",
        "business_access_blocked_owner",
        "business_access_revoked_owner",
    ]:
        assert notification_type in up
        assert notification_type not in down
    for notification_type in [
        "user_suspended_account",
        "user_reactivated_account",
        "user_blocked_account",
    ]:
        assert notification_type in up
        assert notification_type in down
    assert "drop constraint if exists notification_jobs_type_check" in up
    assert "drop constraint if exists notification_jobs_type_check" in down


def test_support_status_notification_migration_is_reversible_and_sender_scoped() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0034_support_status_notifications.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0034_support_status_notifications.down.sql").read_text(encoding="utf-8")
    notification_types = (root / "apps" / "api" / "app" / "modules" / "notifications" / "notification_types.py").read_text(encoding="utf-8")

    for notification_type in [
        "support_ticket_resolved_participant",
        "support_ticket_closed_participant",
    ]:
        assert notification_type in up
        assert notification_type not in down
        assert notification_type in notification_types
    for existing_type in [
        "business_access_suspended_owner",
        "business_access_reactivated_owner",
        "business_access_blocked_owner",
        "business_access_revoked_owner",
    ]:
        assert existing_type in up
        assert existing_type in down
    assert "SUPPORT_NOTIFICATION_TYPES" in notification_types
    assert "| SUPPORT_NOTIFICATION_TYPES" in notification_types
    assert "drop constraint if exists notification_jobs_type_check" in up
    assert "drop constraint if exists notification_jobs_type_check" in down


def test_slice_48b1_notification_type_migration_is_reversible_and_sender_scoped() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0037_business_client_message_notifications.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0037_business_client_message_notifications.down.sql").read_text(encoding="utf-8")
    notification_types = (root / "apps" / "api" / "app" / "modules" / "notifications" / "notification_types.py").read_text(encoding="utf-8")

    for notification_type in [
        "order_message_created_business",
        "order_message_created_client",
        "support_message_created_participant",
    ]:
        assert notification_type in up
        assert notification_type not in down
        assert notification_type in notification_types
    for existing_type in [
        "support_ticket_resolved_participant",
        "support_ticket_closed_participant",
        "order_cancelled_payment_not_reported",
    ]:
        assert existing_type in up
        assert existing_type in down
    assert "CHAT_NOTIFICATION_TYPES" in notification_types
    assert "| CHAT_NOTIFICATION_TYPES" in notification_types
    assert "drop constraint if exists notification_jobs_type_check" in up
    assert "drop constraint if exists notification_jobs_type_check" in down
