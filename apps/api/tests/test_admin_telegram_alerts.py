from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-client-bot-token"
BUSINESS_INTAKE_BOT_TOKEN = "123456:test-business-intake-bot-token"
ADMIN_BOT_TOKEN = "123456:test-admin-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-admin-telegram-alerts",
        "NODO_BUILD_ID": "pytest-admin-telegram-alerts",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "BUSINESS_INTAKE_BOT_TOKEN": BUSINESS_INTAKE_BOT_TOKEN,
        "NODO_ADMIN_TELEGRAM_BOT_TOKEN": ADMIN_BOT_TOKEN,
        "JWT_SECRET": JWT_SECRET,
        "JWT_REFRESH_SECRET": JWT_REFRESH_SECRET,
        "AUTH_INIT_DATA_MAX_AGE_SECONDS": "86400",
        "ACCESS_TOKEN_TTL_SECONDS": "900",
        "REFRESH_TOKEN_TTL_SECONDS": "2592000",
        "AUTH_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "AUTH_RATE_LIMIT_WINDOW_SECONDS": "60",
        "BUSINESS_RATE_LIMIT_MAX_ATTEMPTS": "100",
        "BUSINESS_RATE_LIMIT_WINDOW_SECONDS": "60",
        "TELEGRAM_WEB_APP_URL": "https://nodo-staging.pages.dev",
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.core.config import load_settings, redact_env_value  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.admin_notifications.memory_repository import InMemoryAdminNotificationRepository  # noqa: E402
from app.modules.admin_notifications.service import AdminNotificationService  # noqa: E402
from app.modules.jobs.memory_repository import InMemoryJobRepository  # noqa: E402
from app.modules.notifications.order_notifications import OrderNotificationService  # noqa: E402
from app.modules.notifications.telegram_sender import NotificationSenderWorker  # noqa: E402
from app.modules.users.memory_repository import InMemoryUserRepository  # noqa: E402


class FakeTelegramAdapter:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def send_message(self, *, bot_token: str, chat_id: int, text: str, reply_markup: dict | None = None) -> None:
        self.calls.append(
            {
                "bot_token": bot_token,
                "chat_id": chat_id,
                "text": text,
                "reply_markup": reply_markup,
            }
        )


class EmptyBusinessRepository:
    def get_business(self, business_id: str):  # type: ignore[no-untyped-def]
        return None


def _admin_user(users: InMemoryUserRepository, *, telegram_id: int, role: str = "admin", status: str = "active"):
    user, _ = users.upsert_telegram_user(
        telegram_id=telegram_id,
        username=f"{role}_{telegram_id}",
        first_name="Admin",
        last_name=None,
    )
    users.set_user_role(user.id, role)
    if status != "active":
        users.set_user_status(user.id, status)
    return users.get_user_by_id(user.id)


def test_admin_telegram_bot_token_is_secret_configuration() -> None:
    settings = load_settings(
        {
            "APP_ENV": "test",
            "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
            "REDIS_URL": "redis://127.0.0.1:1/0",
            "NODO_ADMIN_TELEGRAM_BOT_TOKEN": ADMIN_BOT_TOKEN,
        }
    )

    assert settings.nodo_admin_telegram_bot_token == ADMIN_BOT_TOKEN
    assert redact_env_value("NODO_ADMIN_TELEGRAM_BOT_TOKEN", ADMIN_BOT_TOKEN) == "[REDACTED]"


def test_business_intake_notification_enqueues_admin_telegram_alerts_only_for_active_admins() -> None:
    users = InMemoryUserRepository()
    admin = _admin_user(users, telegram_id=101, role="admin")
    super_admin = _admin_user(users, telegram_id=202, role="super_admin")
    _admin_user(users, telegram_id=303, role="support")
    _admin_user(users, telegram_id=404, role="admin", status="blocked")
    jobs = InMemoryJobRepository()
    service = AdminNotificationService(
        repository=InMemoryAdminNotificationRepository(),
        job_repository=jobs,
        user_repository=users,
        admin_telegram_alerts_enabled=True,
        admin_app_url="https://nodo-staging.pages.dev",
    )

    intake = SimpleNamespace(id=str(uuid4()), business_name="Envios Zulia", status="submitted", city="Maracaibo")
    service.business_intake_submitted(intake=intake, request_id="req_admin_telegram_intake")

    alert_jobs = [
        job
        for job in jobs.notification_jobs.values()
        if job.notification_type == "admin_alert_business_intake_submitted"
    ]
    assert {job.recipient_user_id for job in alert_jobs} == {admin.id, super_admin.id}
    for job in alert_jobs:
        metadata = job.metadata_json or {}
        assert metadata["channel"] == "telegram"
        assert metadata["target_surface"] == "admin_alerts"
        assert metadata["action_url"] == "https://nodo-staging.pages.dev/?surface=admin"
        assert "Envios Zulia" in metadata["message_text"]
        assert "token" not in str(metadata).lower()
        assert "101" not in str(metadata)
        assert "202" not in str(metadata)


def test_notification_sender_uses_admin_bot_and_url_button_for_admin_alerts() -> None:
    settings = load_settings(
        {
            "APP_ENV": "test",
            "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
            "REDIS_URL": "redis://127.0.0.1:1/0",
            "BOT_TOKEN": BOT_TOKEN,
            "BUSINESS_INTAKE_BOT_TOKEN": BUSINESS_INTAKE_BOT_TOKEN,
            "NODO_ADMIN_TELEGRAM_BOT_TOKEN": ADMIN_BOT_TOKEN,
        }
    )
    users = InMemoryUserRepository()
    admin = _admin_user(users, telegram_id=909, role="super_admin")
    jobs = InMemoryJobRepository()
    jobs.enqueue_notification(
        notification_type="admin_alert_business_intake_submitted",
        recipient_user_id=admin.id,
        scheduled_for=datetime.now(timezone.utc),
        dedupe_key="admin-alert-business-intake-1",
        metadata_json={
            "channel": "telegram",
            "target_surface": "admin_alerts",
            "message_text": "NODO: llego una solicitud de negocio.",
            "action_text": "Abrir Admin",
            "action_url": "https://nodo-staging.pages.dev/?surface=admin",
        },
    )
    adapter = FakeTelegramAdapter()
    worker = NotificationSenderWorker(settings=settings, job_repository=jobs, user_repository=users, adapter=adapter)

    result = worker.run(now=datetime.now(timezone.utc), request_id="req_admin_telegram_sender")

    assert result["counters"]["sent"] == 1
    assert adapter.calls == [
        {
            "bot_token": ADMIN_BOT_TOKEN,
            "chat_id": 909,
            "text": "NODO: llego una solicitud de negocio.",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "Abrir Admin",
                            "url": "https://nodo-staging.pages.dev/?surface=admin",
                        }
                    ]
                ]
            },
        }
    ]


def test_admin_telegram_start_confirms_only_linked_admin() -> None:
    client = TestClient(create_app())
    admin = _admin_user(client.app.state.user_repository, telegram_id=777, role="admin")
    assert admin is not None
    adapter = FakeTelegramAdapter()
    client.app.state.admin_telegram_adapter = adapter
    secret = hashlib.sha256(ADMIN_BOT_TOKEN.encode("utf-8")).hexdigest()[:40]

    response = client.post(
        "/api/v1/admin-telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        json={"message": {"from": {"id": 777}, "chat": {"id": 777}, "text": "/start"}},
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["action"] == "admin_alerts_ready"
    assert adapter.calls[0]["bot_token"] == ADMIN_BOT_TOKEN
    assert adapter.calls[0]["chat_id"] == 777
    assert "puede recibir alertas Admin" in adapter.calls[0]["text"]


def test_dispute_opened_enqueues_admin_telegram_alerts_without_private_details() -> None:
    settings = load_settings(
        {
            "APP_ENV": "test",
            "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
            "REDIS_URL": "redis://127.0.0.1:1/0",
            "BOT_TOKEN": BOT_TOKEN,
            "BUSINESS_INTAKE_BOT_TOKEN": BUSINESS_INTAKE_BOT_TOKEN,
            "NODO_ADMIN_TELEGRAM_BOT_TOKEN": ADMIN_BOT_TOKEN,
            "TELEGRAM_WEB_APP_URL": "https://nodo-staging.pages.dev",
        }
    )
    users = InMemoryUserRepository()
    admin = _admin_user(users, telegram_id=818, role="admin")
    _admin_user(users, telegram_id=819, role="support")
    jobs = InMemoryJobRepository()
    service = OrderNotificationService(
        settings=settings,
        job_repository=jobs,
        business_repository=EmptyBusinessRepository(),
        user_repository=users,
        admin_telegram_alerts_enabled=True,
    )
    order = SimpleNamespace(
        id=str(uuid4()),
        business_id=str(uuid4()),
        remitter_user_id=str(uuid4()),
        public_order_code="NODO-ABC12345",
        status="disputed",
    )

    service.order_disputed_parties_admin(order=order, dispute_id=str(uuid4()), request_id="req_admin_dispute_alert")

    alert_jobs = [
        job
        for job in jobs.notification_jobs.values()
        if job.notification_type == "admin_alert_dispute_opened"
    ]
    assert {job.recipient_user_id for job in alert_jobs} == {admin.id}
    metadata = alert_jobs[0].metadata_json or {}
    assert metadata["target_surface"] == "admin_alerts"
    assert metadata["action_url"] == "https://nodo-staging.pages.dev/?surface=admin"
    assert "NODO-ABC12345" in metadata["message_text"]
    forbidden = str(metadata).lower()
    assert "reason" not in forbidden
    assert "storage_path" not in forbidden
    assert "account_value" not in forbidden
    assert "token" not in forbidden


def test_admin_telegram_webhook_rejects_wrong_secret() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/api/v1/admin-telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        json={"message": {"from": {"id": 777}, "chat": {"id": 777}, "text": "/start"}},
    )

    assert response.status_code == 403
