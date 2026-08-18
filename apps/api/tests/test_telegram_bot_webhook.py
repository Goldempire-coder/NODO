from __future__ import annotations

import os
from typing import Any

from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-bot-token"
BUSINESS_INTAKE_BOT_TOKEN = "123456:test-business-intake-bot-token"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-telegram-bot",
        "NODO_BUILD_ID": "pytest-telegram-bot-build",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "BUSINESS_INTAKE_BOT_TOKEN": BUSINESS_INTAKE_BOT_TOKEN,
        "JWT_SECRET": "test-access-secret",
        "JWT_REFRESH_SECRET": "test-refresh-secret",
        "TELEGRAM_WEB_APP_URL": "https://nodo-staging.pages.dev",
        "TELEGRAM_WELCOME_IMAGE_URL": "https://nodo-staging.pages.dev/telegram-welcome.jpg?v=test",
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.routes import telegram_bot  # noqa: E402


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    return TestClient(create_app())


class _FakeTelegramResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return {"ok": True, "result": {"message_id": 1}}


class _FakeAsyncClient:
    calls: list[dict[str, Any]] = []

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        return None

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        return None

    async def post(self, url: str, json: dict[str, Any]) -> _FakeTelegramResponse:
        self.calls.append({"url": url, "json": json})
        return _FakeTelegramResponse()


def test_start_webhook_sends_welcome_photo_without_inline_button(monkeypatch) -> None:
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(telegram_bot.httpx, "AsyncClient", _FakeAsyncClient)
    client = _client()
    secret = telegram_bot.telegram_webhook_secret(BOT_TOKEN)

    response = client.post(
        f"/api/v1/telegram/webhook/{secret}",
        headers={"X-Request-Id": "req_telegram_start"},
        json={"message": {"chat": {"id": 777}, "text": "/start"}},
    )

    assert response.status_code == 200
    assert response.json()["data"]["action"] == "welcome_sent"
    assert len(_FakeAsyncClient.calls) == 1
    call = _FakeAsyncClient.calls[0]
    assert call["url"].endswith("/sendPhoto")
    assert BOT_TOKEN in call["url"]
    payload = call["json"]
    assert payload["chat_id"] == 777
    assert payload["photo"] == "https://nodo-staging.pages.dev/telegram-welcome.jpg?v=test"
    assert payload["caption"] == "Abre NODO desde el menu de Telegram para comenzar."
    assert "reply_markup" not in payload


def test_fixed_webhook_authenticates_with_header_and_never_requires_secret_in_url(monkeypatch) -> None:
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(telegram_bot.httpx, "AsyncClient", _FakeAsyncClient)
    client = _client()
    secret = telegram_bot.telegram_webhook_secret(BOT_TOKEN)

    accepted = client.post(
        "/api/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": secret},
        json={"callback_query": {"id": "ignored"}},
    )
    accepted_alias = client.post(
        "/api/v1/telegram/webhook",
        headers={"X-NODO-Bot-Webhook-Secret": secret},
        json={"callback_query": {"id": "ignored"}},
    )
    rejected = client.post(
        "/api/v1/telegram/webhook",
        headers={"X-Telegram-Bot-Api-Secret-Token": "invalid"},
        json={"callback_query": {"id": "ignored"}},
    )
    missing = client.post(
        "/api/v1/telegram/webhook",
        json={"callback_query": {"id": "ignored"}},
    )

    assert accepted.status_code == 200
    assert accepted.headers["Cache-Control"] == "private, no-store"
    assert accepted_alias.status_code == 200
    assert accepted_alias.headers["Cache-Control"] == "private, no-store"
    assert rejected.status_code == 403
    assert rejected.headers["Cache-Control"] == "private, no-store"
    assert missing.status_code == 403
    assert missing.headers["Cache-Control"] == "private, no-store"


def test_webhook_rejects_invalid_secret_without_calling_telegram(monkeypatch) -> None:
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(telegram_bot.httpx, "AsyncClient", _FakeAsyncClient)
    client = _client()

    response = client.post(
        "/api/v1/telegram/webhook/bad-secret",
        headers={"X-Request-Id": "req_bad_secret"},
        json={"message": {"chat": {"id": 777}, "text": "/start"}},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert _FakeAsyncClient.calls == []


def test_client_webhook_rejects_business_intake_bot_secret(monkeypatch) -> None:
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(telegram_bot.httpx, "AsyncClient", _FakeAsyncClient)
    client = _client()
    business_secret = telegram_bot.telegram_webhook_secret(BUSINESS_INTAKE_BOT_TOKEN)

    response = client.post(
        f"/api/v1/telegram/webhook/{business_secret}",
        headers={"X-Request-Id": "req_business_secret_on_client_bot"},
        json={"message": {"chat": {"id": 777}, "text": "/start"}},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "FORBIDDEN"
    assert _FakeAsyncClient.calls == []


def test_non_message_update_is_acknowledged_without_telegram_call(monkeypatch) -> None:
    _FakeAsyncClient.calls = []
    monkeypatch.setattr(telegram_bot.httpx, "AsyncClient", _FakeAsyncClient)
    client = _client()
    secret = telegram_bot.telegram_webhook_secret(BOT_TOKEN)

    response = client.post(
        f"/api/v1/telegram/webhook/{secret}",
        headers={"X-Request-Id": "req_non_message"},
        json={"callback_query": {"id": "ignored"}},
    )

    assert response.status_code == 200
    assert response.json()["data"] == {"ok": True, "handled": False}
    assert _FakeAsyncClient.calls == []
