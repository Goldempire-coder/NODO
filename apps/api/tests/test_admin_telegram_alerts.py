from __future__ import annotations

import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote
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
from app.modules.admin_notifications.memory_repository import (
    InMemoryAdminNotificationRepository,  # noqa: E402
)
from app.modules.admin_notifications.service import (
    AdminNotificationService,  # noqa: E402
)
from app.modules.jobs.memory_repository import InMemoryJobRepository  # noqa: E402
from app.modules.notifications.order_notifications import (
    OrderNotificationService,  # noqa: E402
)
from app.modules.notifications.telegram_sender import (
    NotificationSenderWorker,  # noqa: E402
)
from app.modules.users.admin_telegram_links import (
    hash_admin_telegram_link_code,  # noqa: E402
)
from app.modules.users.memory_repository import InMemoryUserRepository  # noqa: E402


def _client() -> TestClient:
    _set_env()
    return TestClient(create_app())


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


def _signed_init_data(telegram_id: int, username: str) -> str:
    payload = {
        "auth_date": "1893456000",
        "query_id": f"query_{telegram_id}",
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": username}, separators=(",", ":"), sort_keys=True),
    }
    data_check = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret, data_check.encode("utf-8"), hashlib.sha256).hexdigest()
    return "&".join(f"{key}={quote(str(value), safe='')}" for key, value in payload.items())


def _login(client: TestClient, telegram_id: int, username: str) -> dict:
    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": f"req_login_{telegram_id}", "X-NODO-Surface": "admin_web"},
        json={"init_data": _signed_init_data(telegram_id, username)},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _bearer(login: dict, request_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": request_id}


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


def test_admin_telegram_linking_migration_is_reversible_and_separate_from_primary_telegram() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0055_admin_telegram_alert_linking.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0055_admin_telegram_alert_linking.down.sql").read_text(encoding="utf-8")

    assert "admin_alert_telegram_id bigint" in up
    assert "admin_telegram_link_codes" in up
    assert "code_hash text not null unique" in up
    assert "users_admin_alert_telegram_id_unique" in up
    assert "telegram_id" in up
    assert "drop table if exists admin_telegram_link_codes" in down
    assert "drop column if exists admin_alert_telegram_id" in down


def test_admin_telegram_test_alert_migration_is_reversible_and_sender_scoped() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0056_admin_telegram_test_alert.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0056_admin_telegram_test_alert.down.sql").read_text(encoding="utf-8")
    notification_types = (root / "apps" / "api" / "app" / "modules" / "notifications" / "notification_types.py").read_text(encoding="utf-8")

    assert "admin_alert_test" in up
    assert "admin_alert_test" not in down
    assert "admin_alert_test" in notification_types
    assert "ADMIN_ALERT_NOTIFICATION_TYPES" in notification_types
    assert "drop constraint if exists notification_jobs_type_check" in up
    assert "drop constraint if exists notification_jobs_type_check" in down


def test_admin_dashboard_exposes_temporary_telegram_alert_link_code_action() -> None:
    root = Path(__file__).resolve().parents[3]
    dashboard = (root / "apps" / "web" / "src" / "screens" / "admin-web" / "AdminDashboardScreen.tsx").read_text(encoding="utf-8")
    model = (root / "apps" / "web" / "src" / "hooks" / "useAdminWebModel.ts").read_text(encoding="utf-8")
    api = (root / "apps" / "web" / "src" / "api" / "admin.ts").read_text(encoding="utf-8")

    assert "Alertas Telegram Admin" in dashboard
    assert "requestAdminTelegramAlertLinkCode" in dashboard
    assert "adminTelegramAlertLinkCode" in dashboard
    assert "createAdminTelegramAlertLinkCode" in model
    assert "/api/v1/admin/telegram-alerts/link-code" in api
    assert "Enviar prueba" in dashboard
    assert "requestAdminTelegramAlertTest" in dashboard
    assert "requestAdminTelegramAlertTest" in model
    assert "sendAdminTelegramAlertTest" in api
    assert "/api/v1/admin/telegram-alerts/test" in api


def test_admin_telegram_credit_alert_type_migration_is_reversible() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0063_admin_telegram_credit_alerts.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0063_admin_telegram_credit_alerts.down.sql").read_text(encoding="utf-8")
    notification_types = (root / "apps" / "api" / "app" / "modules" / "notifications" / "notification_types.py").read_text(encoding="utf-8")

    assert "admin_alert_credit_purchase_attention" in up
    assert "admin_alert_credit_purchase_attention" not in down
    assert "admin_alert_credit_purchase_attention" in notification_types
    assert "drop constraint if exists notification_jobs_type_check" in up
    assert "drop constraint if exists notification_jobs_type_check" in down


def test_admin_telegram_emergency_alert_type_migration_is_reversible() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0064_admin_telegram_emergency_alerts.up.sql").read_text(
        encoding="utf-8"
    )
    down = (root / "database" / "migrations" / "0064_admin_telegram_emergency_alerts.down.sql").read_text(
        encoding="utf-8"
    )
    notification_types = (
        root / "apps" / "api" / "app" / "modules" / "notifications" / "notification_types.py"
    ).read_text(encoding="utf-8")

    assert "admin_alert_platform_emergency_mode" in up
    assert "admin_alert_platform_emergency_mode" not in down
    assert "admin_alert_platform_emergency_mode" in notification_types
    assert "drop constraint if exists notification_jobs_type_check" in up
    assert "drop constraint if exists notification_jobs_type_check" in down


def test_admin_telegram_alert_test_endpoint_sends_safe_message_to_linked_admin() -> None:
    client = _client()
    admin_login = _login(client, 700888, "admin_alert_test")
    admin_id = admin_login["user"]["id"]
    client.app.state.user_repository.set_user_role(admin_id, "super_admin")
    admin = client.app.state.user_repository.get_user_by_id(admin_id)
    assert admin is not None
    admin.admin_alert_telegram_id = 700999
    adapter = FakeTelegramAdapter()
    client.app.state.notification_sender_worker = NotificationSenderWorker(
        settings=client.app.state.settings,
        job_repository=client.app.state.job_repository,
        user_repository=client.app.state.user_repository,
        adapter=adapter,
        admin_notifications=client.app.state.admin_notification_service,
    )

    response = client.post(
        "/api/v1/admin/telegram-alerts/test",
        headers=_bearer(admin_login, "req_admin_telegram_alert_test"),
    )

    assert response.status_code == 200, response.text
    payload = response.json()["data"]
    assert payload["notification"]["notification_type"] == "admin_telegram_alert_test"
    assert payload["sender_result"]["counters"]["sent"] == 1
    assert payload["sender_result"]["counters"]["processed"] == 1
    assert adapter.calls == [
        {
            "bot_token": ADMIN_BOT_TOKEN,
            "chat_id": 700999,
            "text": (
                "NODO alerta Admin\n\n"
                "Prueba recibida. El canal esta activo.\n\n"
                "No tienes que hacer nada."
            ),
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "Abrir panel Admin",
                            "url": "https://nodo-staging.pages.dev/?surface=admin",
                        }
                    ]
                ]
            },
        }
    ]
    serialized = json.dumps(payload).lower()
    assert ADMIN_BOT_TOKEN.lower() not in serialized
    assert "700999" not in serialized


def test_admin_telegram_alert_test_endpoint_rejects_support() -> None:
    client = _client()
    support_login = _login(client, 700889, "support_alert_test")
    client.app.state.user_repository.set_user_role(support_login["user"]["id"], "support")

    response = client.post(
        "/api/v1/admin/telegram-alerts/test",
        headers=_bearer(support_login, "req_support_admin_telegram_alert_test"),
    )

    assert response.status_code == 403


def test_emergency_mode_changes_enqueue_admin_telegram_alerts_without_sensitive_details() -> None:
    client = _client()
    admin_login = _login(client, 700890, "admin_emergency_alert")
    admin_id = admin_login["user"]["id"]
    client.app.state.user_repository.set_user_role(admin_id, "super_admin")
    admin = client.app.state.user_repository.get_user_by_id(admin_id)
    assert admin is not None
    admin.admin_alert_telegram_id = 700990
    adapter = FakeTelegramAdapter()
    client.app.state.notification_sender_worker = NotificationSenderWorker(
        settings=client.app.state.settings,
        job_repository=client.app.state.job_repository,
        user_repository=client.app.state.user_repository,
        adapter=adapter,
        admin_notifications=client.app.state.admin_notification_service,
    )

    activated = client.post(
        "/api/v1/admin/emergency-mode/activate",
        headers={
            **_bearer(admin_login, "req_admin_emergency_activate"),
            "Idempotency-Key": "admin-emergency-alert-activate",
        },
        json={
            "reason": "Incidente con private_key 0x3333333333333333333333333333333333333333",
            "message": "Estamos revisando NODO.",
        },
    )
    sent_activate = client.app.state.notification_sender_worker.run(request_id="req_admin_emergency_activate_sender")
    deactivated = client.post(
        "/api/v1/admin/emergency-mode/deactivate",
        headers={
            **_bearer(admin_login, "req_admin_emergency_deactivate"),
            "Idempotency-Key": "admin-emergency-alert-deactivate",
        },
        json={"reason": "Incidente resuelto"},
    )
    sent_deactivate = client.app.state.notification_sender_worker.run(
        request_id="req_admin_emergency_deactivate_sender"
    )

    assert activated.status_code == 200, activated.text
    assert deactivated.status_code == 200, deactivated.text
    assert sent_activate["counters"]["sent"] == 1
    assert sent_deactivate["counters"]["sent"] == 1
    assert [call["chat_id"] for call in adapter.calls] == [700990, 700990]
    assert "Modo emergencia ACTIVADO" in adapter.calls[0]["text"]
    assert "Modo emergencia desactivado" in adapter.calls[1]["text"]
    assert "Admin > Dashboard" in adapter.calls[0]["text"]
    assert "private_key" not in json.dumps(adapter.calls).lower()
    assert "0x3333333333333333333333333333333333333333" not in json.dumps(adapter.calls)
    assert ADMIN_BOT_TOKEN.lower() not in json.dumps(activated.json()).lower()
    assert ADMIN_BOT_TOKEN.lower() not in json.dumps(deactivated.json()).lower()


def test_emergency_mode_change_does_not_fail_when_admin_telegram_alert_enqueue_fails() -> None:
    client = _client()
    admin_login = _login(client, 700891, "admin_emergency_alert_fallback")
    admin_id = admin_login["user"]["id"]
    client.app.state.user_repository.set_user_role(admin_id, "super_admin")

    class FailingAdminNotifications:
        def platform_emergency_mode_changed(self, **_: object) -> None:
            raise RuntimeError("notification job unavailable")

    client.app.state.admin_notification_service = FailingAdminNotifications()

    response = client.post(
        "/api/v1/admin/emergency-mode/activate",
        headers={
            **_bearer(admin_login, "req_admin_emergency_activate_no_alert"),
            "Idempotency-Key": "admin-emergency-alert-fallback",
        },
        json={"reason": "Incidente operativo", "message": "Estamos revisando NODO."},
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["emergency_mode"]["enabled"] is True
    assert "notification job unavailable" not in response.text


def test_business_intake_notification_enqueues_admin_telegram_alerts_only_for_active_admins() -> None:
    users = InMemoryUserRepository()
    admin = _admin_user(users, telegram_id=101, role="admin")
    admin.admin_alert_telegram_id = 1001
    super_admin = _admin_user(users, telegram_id=202, role="super_admin")
    super_admin.admin_alert_telegram_id = 2002
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
        assert "Admin > Intake" in metadata["message_text"]
        assert "antes de aprobar o rechazar" in metadata["message_text"]
        assert metadata["action_text"] == "Abrir panel Admin"
        assert "token" not in str(metadata).lower()
        assert "101" not in str(metadata)
        assert "202" not in str(metadata)


def test_credit_purchase_attention_enqueues_admin_telegram_alert_without_sensitive_details() -> None:
    users = InMemoryUserRepository()
    admin = _admin_user(users, telegram_id=501, role="super_admin")
    admin.admin_alert_telegram_id = 1501
    jobs = InMemoryJobRepository()
    service = AdminNotificationService(
        repository=InMemoryAdminNotificationRepository(),
        job_repository=jobs,
        user_repository=users,
        admin_telegram_alerts_enabled=True,
        admin_app_url="https://nodo-staging.pages.dev",
    )

    purchase = SimpleNamespace(
        id=str(uuid4()),
        business_id=str(uuid4()),
        status="under_review",
        package_code="starter",
    )
    service.credit_purchase_attention(
        purchase=purchase,
        reason="under_review",
        request_id="req_admin_telegram_credit_attention",
        error_code="TX_REQUIRES_REVIEW",
    )

    alert_jobs = [
        job
        for job in jobs.notification_jobs.values()
        if job.notification_type == "admin_alert_credit_purchase_attention"
    ]
    assert {job.recipient_user_id for job in alert_jobs} == {admin.id}
    metadata = alert_jobs[0].metadata_json or {}
    assert metadata["channel"] == "telegram"
    assert metadata["target_surface"] == "admin_alerts"
    assert metadata["action_url"] == "https://nodo-staging.pages.dev/?surface=admin"
    assert "Compra USDC requiere revision" in metadata["message_text"]
    assert "Revision creditos" in metadata["message_text"]
    assert metadata["action_text"] == "Abrir panel Admin"
    message_text = metadata["message_text"].lower()
    assert "tx_hash" not in message_text
    assert "private" not in message_text
    assert "secret" not in message_text
    assert purchase.id.lower() not in message_text
    assert purchase.business_id.lower() not in message_text


def test_admin_telegram_alerts_do_not_enqueue_primary_telegram_fallbacks() -> None:
    users = InMemoryUserRepository()
    linked_admin = _admin_user(users, telegram_id=101, role="admin")
    linked_admin.admin_alert_telegram_id = 1001
    unlinked_admin = _admin_user(users, telegram_id=202, role="admin")
    assert unlinked_admin.admin_alert_telegram_id is None
    _admin_user(users, telegram_id=303, role="super_admin")
    jobs = InMemoryJobRepository()
    service = AdminNotificationService(
        repository=InMemoryAdminNotificationRepository(),
        job_repository=jobs,
        user_repository=users,
        admin_telegram_alerts_enabled=True,
        admin_app_url="https://nodo-staging.pages.dev",
    )

    intake = SimpleNamespace(id=str(uuid4()), business_name="Envios Zulia", status="submitted", city="Maracaibo")
    service.business_intake_submitted(intake=intake, request_id="req_admin_telegram_intake_linked_only")

    alert_jobs = [
        job
        for job in jobs.notification_jobs.values()
        if job.notification_type == "admin_alert_business_intake_submitted"
    ]
    assert {job.recipient_user_id for job in alert_jobs} == {linked_admin.id}


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
    admin.admin_alert_telegram_id = 1909
    jobs = InMemoryJobRepository()
    jobs.enqueue_notification(
        notification_type="admin_alert_business_intake_submitted",
        recipient_user_id=admin.id,
        scheduled_for=datetime.now(timezone.utc),
        dedupe_key="admin-alert-business-intake-1",
        metadata_json={
            "channel": "telegram",
            "target_surface": "admin_alerts",
            "message_text": "NODO alerta\n\nNueva solicitud de negocio.\n\nAccion sugerida: abre Admin > Intake.",
            "action_text": "Abrir panel Admin",
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
            "chat_id": 1909,
            "text": "NODO alerta\n\nNueva solicitud de negocio.\n\nAccion sugerida: abre Admin > Intake.",
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": "Abrir panel Admin",
                            "url": "https://nodo-staging.pages.dev/?surface=admin",
                        }
                    ]
                ]
            },
        }
    ]


def test_admin_telegram_alerts_can_link_business_owner_telegram_with_admin_code() -> None:
    client = _client()
    admin_login = _login(client, 700777, "admin_alert_owner")
    admin_id = admin_login["user"]["id"]
    client.app.state.user_repository.set_user_role(admin_id, "super_admin")
    business_owner, _ = client.app.state.user_repository.upsert_telegram_user(
        telegram_id=6808095582,
        username="business_owner_alerts",
        first_name="Owner",
        last_name=None,
    )
    client.app.state.user_repository.set_user_role(business_owner.id, "business_owner")
    adapter = FakeTelegramAdapter()
    client.app.state.admin_telegram_adapter = adapter
    secret = hashlib.sha256(ADMIN_BOT_TOKEN.encode("utf-8")).hexdigest()[:40]

    code_response = client.post(
        "/api/v1/admin/telegram-alerts/link-code",
        headers=_bearer(admin_login, "req_admin_telegram_link_code"),
    )
    assert code_response.status_code == 200, code_response.text
    code = code_response.json()["data"]["code"]
    assert code and code not in str(client.app.state.audit_writer.events)

    linked = client.post(
        "/api/v1/admin-telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        json={"message": {"from": {"id": 6808095582}, "chat": {"id": 6808095582}, "text": f"/start {code.lower()}" }},
    )

    assert linked.status_code == 200, linked.text
    assert linked.json()["data"]["action"] == "admin_alerts_linked"
    admin = client.app.state.user_repository.get_user_by_id(admin_id)
    owner = client.app.state.user_repository.get_user_by_id(business_owner.id)
    assert admin.admin_alert_telegram_id == 6808095582
    assert owner.role == "business_owner"
    assert owner.telegram_id == 6808095582
    assert adapter.calls[-1]["chat_id"] == 6808095582
    assert "recibira alertas Admin" in adapter.calls[-1]["text"]


def test_notification_sender_prefers_admin_alert_chat_without_changing_regular_telegram() -> None:
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
    admin = _admin_user(users, telegram_id=111, role="admin")
    admin.admin_alert_telegram_id = 222
    jobs = InMemoryJobRepository()
    jobs.enqueue_notification(
        notification_type="admin_alert_business_intake_submitted",
        recipient_user_id=admin.id,
        scheduled_for=datetime.now(timezone.utc),
        dedupe_key="admin-alert-prefers-linked-chat",
        metadata_json={
            "channel": "telegram",
            "target_surface": "admin_alerts",
            "message_text": "NODO: alerta Admin.",
        },
    )
    adapter = FakeTelegramAdapter()
    worker = NotificationSenderWorker(settings=settings, job_repository=jobs, user_repository=users, adapter=adapter)

    result = worker.run(now=datetime.now(timezone.utc), request_id="req_admin_telegram_alert_chat")

    assert result["counters"]["sent"] == 1
    assert adapter.calls[0]["bot_token"] == ADMIN_BOT_TOKEN
    assert adapter.calls[0]["chat_id"] == 222


def test_notification_sender_rejects_admin_alert_without_linked_admin_chat() -> None:
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
    admin = _admin_user(users, telegram_id=111, role="admin")
    assert admin.admin_alert_telegram_id is None
    jobs = InMemoryJobRepository()
    jobs.enqueue_notification(
        notification_type="admin_alert_business_intake_submitted",
        recipient_user_id=admin.id,
        scheduled_for=datetime.now(timezone.utc),
        dedupe_key="admin-alert-requires-linked-chat",
        metadata_json={
            "channel": "telegram",
            "target_surface": "admin_alerts",
            "message_text": "NODO: alerta Admin.",
        },
    )
    adapter = FakeTelegramAdapter()
    worker = NotificationSenderWorker(settings=settings, job_repository=jobs, user_repository=users, adapter=adapter)

    result = worker.run(now=datetime.now(timezone.utc), request_id="req_admin_telegram_requires_linked_chat")

    assert result["counters"]["sent"] == 0
    assert result["counters"]["failed_permanent"] == 1
    assert not adapter.calls


def test_admin_telegram_start_confirms_only_linked_admin() -> None:
    client = _client()
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


def test_admin_telegram_start_rejects_expired_or_unknown_link_code() -> None:
    client = _client()
    admin = _admin_user(client.app.state.user_repository, telegram_id=778, role="admin")
    assert admin is not None
    code_hash = hash_admin_telegram_link_code("EXPIREDCODE1")
    client.app.state.user_repository.create_admin_telegram_link_code(
        user_id=admin.id,
        code_hash=code_hash,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )
    adapter = FakeTelegramAdapter()
    client.app.state.admin_telegram_adapter = adapter
    secret = hashlib.sha256(ADMIN_BOT_TOKEN.encode("utf-8")).hexdigest()[:40]

    expired = client.post(
        "/api/v1/admin-telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        json={"message": {"from": {"id": 778}, "chat": {"id": 778}, "text": "/start EXPIREDCODE1"}},
    )
    unknown = client.post(
        "/api/v1/admin-telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        json={"message": {"from": {"id": 778}, "chat": {"id": 778}, "text": "/start UNKNOWNCODE1"}},
    )

    assert expired.status_code == 200, expired.text
    assert expired.json()["data"]["action"] == "admin_alerts_code_expired"
    assert unknown.status_code == 200, unknown.text
    assert unknown.json()["data"]["action"] == "admin_alerts_code_invalid"
    assert client.app.state.user_repository.get_user_by_id(admin.id).admin_alert_telegram_id is None


def test_admin_telegram_link_code_requires_private_chat() -> None:
    client = _client()
    admin = _admin_user(client.app.state.user_repository, telegram_id=779, role="admin")
    assert admin is not None
    code_hash = hash_admin_telegram_link_code("ABCDEFG23456")
    client.app.state.user_repository.create_admin_telegram_link_code(
        user_id=admin.id,
        code_hash=code_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
    )
    adapter = FakeTelegramAdapter()
    client.app.state.admin_telegram_adapter = adapter
    secret = hashlib.sha256(ADMIN_BOT_TOKEN.encode("utf-8")).hexdigest()[:40]

    response = client.post(
        "/api/v1/admin-telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        json={
            "message": {
                "from": {"id": 779},
                "chat": {"id": -100779, "type": "supergroup"},
                "text": "/start ABCDEFG23456",
            }
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["data"]["action"] == "admin_alerts_private_chat_required"
    assert client.app.state.user_repository.get_user_by_id(admin.id).admin_alert_telegram_id is None
    assert "chat privado" in adapter.calls[-1]["text"]


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
    admin.admin_alert_telegram_id = 1818
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
    assert "Admin > Disputas" in metadata["message_text"]
    assert "revisar el caso" in metadata["message_text"].lower()
    assert metadata["action_text"] == "Abrir panel Admin"
    forbidden = str(metadata).lower()
    assert "reason" not in forbidden
    assert "storage_path" not in forbidden
    assert "account_value" not in forbidden
    assert "token" not in forbidden


def test_admin_telegram_webhook_rejects_wrong_secret() -> None:
    client = _client()
    response = client.post(
        "/api/v1/admin-telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "wrong"},
        json={"message": {"from": {"id": 777}, "chat": {"id": 777}, "text": "/start"}},
    )

    assert response.status_code == 403
