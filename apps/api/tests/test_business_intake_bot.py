from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from typing import Any
from urllib.parse import urlencode

from fastapi.testclient import TestClient

BOT_TOKEN = "123456:test-bot-token"
BUSINESS_INTAKE_BOT_TOKEN = "123456:test-business-intake-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-14D",
        "NODO_BUILD_ID": "pytest-business-intake-bot-build",
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
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.modules.business_intake import admin_delete as intake_admin_delete  # noqa: E402
from app.modules.business_intake import business_creation as intake_business_creation  # noqa: E402
from app.modules.business_intake import conversation as intake_conversation  # noqa: E402
from app.modules.business_intake import routes as intake_routes  # noqa: E402
from app.modules.business_intake import service as intake_service  # noqa: E402
from app.modules.business_intake.models import utc_now  # noqa: E402
from app.routes import telegram_bot  # noqa: E402
from app.routes.telegram_bot import telegram_webhook_secret  # noqa: E402


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    return TestClient(create_app())


def _signed_init_data(telegram_id: int, username: str, *, bot_token: str = BOT_TOKEN) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": username}, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def _login(client: TestClient, telegram_id: int, username: str) -> dict:
    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": f"req_login_{telegram_id}"},
        json={"init_data": _signed_init_data(telegram_id, username)},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _bot_headers(key: str = "bot") -> dict[str, str]:
    return {
        "X-NODO-Bot-Webhook-Secret": telegram_webhook_secret(BUSINESS_INTAKE_BOT_TOKEN),
        "X-Request-Id": f"req_{key}",
    }


def _bearer(login: dict, key: str = "req") -> dict[str, str]:
    return {"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": key}


def _admin_headers(login: dict, key: str) -> dict[str, str]:
    return {**_bearer(login, f"req_{key}"), "Idempotency-Key": key}


def _start(client: TestClient, *, update_id: int = 100, telegram_id: int = 7001, chat_id: int = 8001, referral_code: str | None = "NODO-TEST") -> dict:
    response = client.post(
        "/api/v1/business-intake/start",
        headers=_bot_headers(f"start_{update_id}"),
        json={"telegram_user_id": telegram_id, "telegram_chat_id": chat_id, "telegram_update_id": update_id, "referral_code": referral_code},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _contact(client: TestClient, intake_id: str, *, update_id: int = 101, telegram_id: int = 7001, chat_id: int = 8001, contact_user_id: int | None = None) -> dict:
    response = client.post(
        f"/api/v1/business-intake/{intake_id}/contact",
        headers=_bot_headers(f"contact_{update_id}"),
        json={
            "telegram_update_id": update_id,
            "telegram_user_id": telegram_id,
            "telegram_chat_id": chat_id,
            "contact_user_id": contact_user_id or telegram_id,
            "contact_phone": "+584121234567",
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _upload_intake_doc(client: TestClient, intake_id: str, *, update_id: int, request_id: str = "intake_doc") -> dict:
    response = client.post(
        f"/api/v1/business-intake/{intake_id}/documents",
        headers=_bot_headers(request_id),
        data={"document_kind": "identity_document", "telegram_update_id": update_id},
        files={"file": ("doc.pdf", b"private-document", "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _submit(client: TestClient, intake_id: str, *, update_id: int = 102, telegram_id: int = 7001, chat_id: int = 8001) -> dict:
    submit_update_id = update_id
    if not client.app.state.business_intake_repository.list_documents(intake_id):
        _upload_intake_doc(client, intake_id, update_id=update_id, request_id=f"submit_doc_{update_id}")
        submit_update_id = update_id + 1
    response = client.post(
        f"/api/v1/business-intake/{intake_id}/submit",
        headers=_bot_headers(f"submit_{submit_update_id}"),
        json={
            "telegram_update_id": submit_update_id,
            "telegram_user_id": telegram_id,
            "telegram_chat_id": chat_id,
            "business_name": "Casa Intake",
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
            "references": ["@casaintake"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def _business_webhook_secret() -> str:
    return telegram_webhook_secret(BUSINESS_INTAKE_BOT_TOKEN)


def _business_webhook(client: TestClient, update: dict[str, Any], *, secret: str | None = None) -> Any:
    webhook_secret = secret or _business_webhook_secret()
    return client.post(
        "/api/v1/business-intake/telegram/webhook",
        headers={
            "X-Telegram-Bot-Api-Secret-Token": webhook_secret,
            "X-Request-Id": f"req_business_intake_update_{update.get('update_id', 'missing')}",
        },
        json=update,
    )


def _telegram_message(
    update_id: int,
    *,
    telegram_id: int = 7301,
    chat_id: int = 8301,
    text: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "message_id": update_id,
        "from": {"id": telegram_id, "first_name": "Negocio"},
        "chat": {"id": chat_id, "type": "private"},
    }
    if text is not None:
        message["text"] = text
    if extra:
        message.update(extra)
    return {"update_id": update_id, "message": message}


def _drive_conversation_to_documents(
    client: TestClient,
    monkeypatch: Any,
    *,
    telegram_id: int = 7301,
    chat_id: int = 8301,
    start_update: int = 1000,
) -> tuple[str, list[dict[str, Any]]]:
    sent_messages: list[dict[str, Any]] = []

    async def fake_send(bot_token: str, sent_chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        sent_messages.append({"bot_token": bot_token, "chat_id": sent_chat_id, "text": text, "reply_markup": reply_markup})

    monkeypatch.setattr(intake_service, "telegram_send_message", fake_send)
    monkeypatch.setattr(intake_routes, "telegram_send_message", fake_send)

    start = _business_webhook(client, _telegram_message(start_update, telegram_id=telegram_id, chat_id=chat_id, text="/start"))
    assert start.status_code == 200, start.text
    intake_id = start.json()["data"]["intake_id"]

    answers = [
        "REF-CARLOS-01",
        "+584121234567",
        "Casa Cambio Centro",
        "J-12345678-9",
        "Carlo Responsable",
        "V-12345678",
        "Caracas",
        "+582121234567",
        "both",
        "Mercantil, Banesco",
        "zelle, usdt_trc20",
        "@referenciauno, @referenciados",
    ]
    for offset, answer in enumerate(answers, start=1):
        response = _business_webhook(
            client,
            _telegram_message(start_update + offset, telegram_id=telegram_id, chat_id=chat_id, text=answer),
        )
        assert response.status_code == 200, response.text
    return intake_id, sent_messages


def test_business_intake_flow_does_not_create_business_role_or_access_link() -> None:
    client = _client()

    started = _start(client)
    _contact(client, started["id"])
    submitted = _submit(client, started["id"])

    assert submitted["status"] == "submitted"
    assert submitted["message"] == "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso."
    assert client.app.state.business_repository.businesses == {}
    assert client.app.state.business_repository.access_links == {}
    user = client.app.state.user_repository.get_user_by_telegram_id(7001)
    assert user is not None
    assert user.role == "remitter"
    assert {"business_intake_started", "business_intake_contact_shared", "business_intake_submitted"}.issubset(set(_event_types(client)))


def test_client_telegram_webhook_does_not_process_business_intake(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client()
    sent_messages: list[dict[str, Any]] = []

    async def fake_telegram_post(_settings, method: str, payload: dict[str, Any]) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        sent_messages.append({"method": method, "payload": payload})
        return {"ok": True, "result": {}}

    monkeypatch.setattr(telegram_bot, "_telegram_post", fake_telegram_post)

    secret = telegram_webhook_secret(BOT_TOKEN)
    start = client.post(
        f"/api/v1/telegram/webhook/{secret}",
        json={
            "update_id": 1200,
            "message": {
                "message_id": 1,
                "from": {"id": 7101, "first_name": "Negocio"},
                "chat": {"id": 8101, "type": "private"},
                "text": "/start negocio",
            },
        },
    )
    assert start.status_code == 200, start.text
    assert start.json()["data"]["action"] == "welcome_sent"
    assert len(client.app.state.business_intake_repository.intakes) == 0
    assert client.app.state.business_repository.businesses == {}
    assert client.app.state.business_repository.access_links == {}

    contact = client.post(
        f"/api/v1/telegram/webhook/{secret}",
        json={
            "update_id": 1201,
            "message": {
                "message_id": 2,
                "from": {"id": 7101, "first_name": "Negocio"},
                "chat": {"id": 8101, "type": "private"},
                "contact": {"user_id": 7101, "phone_number": "+584121234567"},
            },
        },
    )
    assert contact.status_code == 200, contact.text
    assert contact.json()["data"]["action"] == "open_hint_sent"
    assert len(client.app.state.business_intake_repository.intakes) == 0
    assert client.app.state.business_repository.businesses == {}
    assert client.app.state.business_repository.access_links == {}
    user = client.app.state.user_repository.get_user_by_telegram_id(7101)
    assert user is None


def test_contact_is_required_and_must_belong_to_same_telegram_user() -> None:
    client = _client()
    started = _start(client, telegram_id=7011, chat_id=8011)

    no_contact_submit = client.post(
        f"/api/v1/business-intake/{started['id']}/submit",
        headers=_bot_headers("submit_no_contact"),
        json={
            "telegram_update_id": 202,
            "telegram_user_id": 7011,
            "telegram_chat_id": 8011,
            "business_name": "Casa Sin Contacto",
            "responsible_name": "Responsable",
            "city": "Caracas",
            "business_phone": "+582121234567",
            "operation": "both",
            "banks": [],
            "methods": ["zelle"],
            "min_amount_usd": "20.00",
            "max_amount_usd": "500.00",
            "schedule": "Lunes",
            "references": [],
        },
    )
    assert no_contact_submit.status_code == 400
    assert no_contact_submit.json()["error"]["code"] == "BOT_CONTACT_REQUIRED"

    bad_contact = client.post(
        f"/api/v1/business-intake/{started['id']}/contact",
        headers=_bot_headers("bad_contact"),
        json={
            "telegram_update_id": 203,
            "telegram_user_id": 7011,
            "telegram_chat_id": 8011,
            "contact_user_id": 9999,
            "contact_phone": "+584121234567",
        },
    )
    assert bad_contact.status_code == 400
    assert bad_contact.json()["error"]["code"] == "BOT_CONTACT_REQUIRED"


def test_public_submit_uses_backend_default_limits_even_if_payload_amounts_are_invalid() -> None:
    client = _client()
    started = _start(client, update_id=250, telegram_id=7015, chat_id=8015)
    _contact(client, started["id"], update_id=251, telegram_id=7015, chat_id=8015)
    _upload_intake_doc(client, started["id"], update_id=252, request_id="default_limits_doc")

    response = client.post(
        f"/api/v1/business-intake/{started['id']}/submit",
        headers=_bot_headers("invalid_amount_range"),
        json={
            "telegram_update_id": 253,
            "telegram_user_id": 7015,
            "telegram_chat_id": 8015,
            "business_name": "Casa Monto Invalido",
            "business_tax_id": "J-12345678-9",
            "responsible_name": "Responsable",
            "responsible_id_number": "V-12345678",
            "city": "Caracas",
            "business_phone": "+582121234567",
            "operation": "both",
            "banks": [],
            "methods": ["zelle"],
            "min_amount_usd": "500.00",
            "max_amount_usd": "20.00",
            "daily_limit_usd": "999999.00",
            "schedule": "Lunes",
            "references": ["@casa_monto"],
        },
    )

    assert response.status_code == 200, response.text
    intake = client.app.state.business_intake_repository.get(started["id"])
    assert intake is not None
    assert intake.status == "submitted"
    assert intake.min_amount_usd == "20.00"
    assert intake.max_amount_usd == "100.00"
    assert intake.daily_limit_usd == "1000.00"


def test_telegram_update_id_duplicate_does_not_duplicate_request_or_document() -> None:
    client = _client()
    first = _start(client, update_id=300, telegram_id=7021, chat_id=8021)
    second = _start(client, update_id=300, telegram_id=7021, chat_id=8021)

    assert first["id"] == second["id"]
    assert len(client.app.state.business_intake_repository.intakes) == 1
    assert _event_types(client).count("business_intake_started") == 1

    _contact(client, first["id"], update_id=301, telegram_id=7021, chat_id=8021)
    upload_1 = client.post(
        f"/api/v1/business-intake/{first['id']}/documents",
        headers=_bot_headers("upload_one"),
        data={"document_kind": "identity_document", "telegram_update_id": "302"},
        files={"file": ("doc.pdf", b"private-document", "application/pdf")},
    )
    upload_2 = client.post(
        f"/api/v1/business-intake/{first['id']}/documents",
        headers=_bot_headers("upload_dup"),
        data={"document_kind": "identity_document", "telegram_update_id": "302"},
        files={"file": ("doc.pdf", b"private-document", "application/pdf")},
    )

    assert upload_1.status_code == 201, upload_1.text
    assert upload_2.status_code == 201, upload_2.text
    assert upload_1.json()["data"]["file"]["id"] == upload_2.json()["data"]["file"]["id"]
    assert len(client.app.state.business_intake_repository.documents) == 1
    assert _event_types(client).count("business_intake_document_uploaded") == 1


def test_document_upload_validation_and_no_storage_path_exposure() -> None:
    client = _client()
    started = _start(client, update_id=400, telegram_id=7031, chat_id=8031)
    _contact(client, started["id"], update_id=401, telegram_id=7031, chat_id=8031)

    valid = client.post(
        f"/api/v1/business-intake/{started['id']}/documents",
        headers=_bot_headers("valid_doc"),
        data={"document_kind": "rif_document", "telegram_update_id": "402"},
        files={"file": ("rif.png", b"image-bytes", "image/png")},
    )
    assert valid.status_code == 201, valid.text
    assert valid.json()["data"]["file"]["file_type"] == "intake_document"
    assert "storage_path" not in valid.text

    video = client.post(
        f"/api/v1/business-intake/{started['id']}/documents",
        headers=_bot_headers("video_doc"),
        data={"document_kind": "local_image", "telegram_update_id": "403"},
        files={"file": ("local.mp4", b"video-bytes", "video/mp4")},
    )
    assert video.status_code == 400
    assert video.json()["error"]["code"] == "BOT_UPLOAD_INVALID"

    too_large = client.post(
        f"/api/v1/business-intake/{started['id']}/documents",
        headers=_bot_headers("large_doc"),
        data={"document_kind": "identity_document", "telegram_update_id": "404"},
        files={"file": ("large.pdf", b"x" * (5 * 1024 * 1024 + 1), "application/pdf")},
    )
    assert too_large.status_code == 400
    assert too_large.json()["error"]["code"] == "BOT_UPLOAD_INVALID"


def test_admin_list_detail_and_review_require_rbac_reason_idempotency() -> None:
    client = _client()
    started = _start(client, update_id=500, telegram_id=7041, chat_id=8041)
    _contact(client, started["id"], update_id=501, telegram_id=7041, chat_id=8041)
    _submit(client, started["id"], update_id=502, telegram_id=7041, chat_id=8041)

    admin = _login(client, 9001, "admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    support = _login(client, 9002, "support")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")
    remitter = _login(client, 9003, "remitter")

    forbidden_list = client.get("/api/v1/admin/business-intake", headers=_bearer(remitter, "req_remitter_list"))
    assert forbidden_list.status_code == 403

    listed = client.get("/api/v1/admin/business-intake", headers=_bearer(admin, "req_admin_list"))
    assert listed.status_code == 200, listed.text
    assert listed.json()["data"]["items"][0]["contact_phone_masked"]
    assert "storage_path" not in listed.text

    detail = client.get(f"/api/v1/admin/business-intake/{started['id']}", headers=_bearer(support, "req_support_detail"))
    assert detail.status_code == 200, detail.text
    assert "storage_path" not in detail.text
    assert "business_intake_viewed_by_admin" in _event_types(client)
    file_id = detail.json()["data"]["documents"][0]["id"]

    support_document_view = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/documents/{file_id}/view-url",
        headers=_bearer(support, "req_support_intake_doc_view"),
        json={"reason": "Revision"},
    )
    assert support_document_view.status_code == 403

    admin_document_view = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/documents/{file_id}/view-url",
        headers=_bearer(admin, "req_admin_intake_doc_view"),
        json={"reason": "Revision de documentos para aprobar negocio"},
    )
    assert admin_document_view.status_code == 200, admin_document_view.text
    assert admin_document_view.json()["data"]["expires_in"] <= 300
    assert "storage_path" not in admin_document_view.text
    assert "business_intake_document_viewed" in _event_types(client)
    audit_text = json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert admin_document_view.json()["data"]["url"] not in audit_text

    support_accept = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(support, "support_accept"), "Content-Type": "application/json"},
        json={"reason": "support cannot accept"},
    )
    assert support_accept.status_code == 403

    accepted_without_reason = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "no_reason"), "Content-Type": "application/json"},
        json={"reason": ""},
    )
    assert accepted_without_reason.status_code == 200, accepted_without_reason.text
    assert accepted_without_reason.json()["data"]["intake"]["status"] == "accepted"

    accepted_1 = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "accept_once"), "Content-Type": "application/json"},
        json={"reason": "evidence reviewed"},
    )
    accepted_2 = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "accept_once"), "Content-Type": "application/json"},
        json={"reason": "evidence reviewed"},
    )
    assert accepted_1.status_code == 200, accepted_1.text
    assert accepted_2.status_code == 200, accepted_2.text
    assert accepted_1.json()["data"]["access_link_created"] is False
    assert accepted_1.json()["data"]["created_business"] is False
    assert client.app.state.business_repository.businesses == {}
    assert client.app.state.business_repository.access_links == {}
    assert _event_types(client).count("business_intake_accepted") == 1


def test_admin_accept_blocks_incomplete_intake_even_if_status_is_submitted() -> None:
    client = _client()
    started = _start(client, update_id=540, telegram_id=7040, chat_id=8040)
    _contact(client, started["id"], update_id=541, telegram_id=7040, chat_id=8040)
    _upload_intake_doc(client, started["id"], update_id=542, request_id="incomplete_doc")
    intake = client.app.state.business_intake_repository.get(started["id"])
    assert intake is not None
    intake.status = "submitted"
    intake.last_step = "submitted"
    intake.submitted_at = utc_now()

    admin = _login(client, 9040, "admin_incomplete_intake")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    response = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "accept_incomplete_intake"), "Content-Type": "application/json"},
        json={"reason": "cannot approve without full review"},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_INTAKE_INCOMPLETE"
    assert "nombre del negocio" in response.text
    assert client.app.state.business_repository.businesses == {}
    assert client.app.state.business_repository.access_links == {}


def test_admin_accept_requires_legal_identity_and_daily_limit_before_approval() -> None:
    client = _client()
    started = _start(client, update_id=545, telegram_id=7045, chat_id=8045)
    _contact(client, started["id"], update_id=546, telegram_id=7045, chat_id=8045)
    _upload_intake_doc(client, started["id"], update_id=547, request_id="legal_missing_doc")
    intake = client.app.state.business_intake_repository.get(started["id"])
    assert intake is not None
    intake.status = "submitted"
    intake.last_step = "submitted"
    intake.submitted_at = utc_now()
    intake.referral_code = "REF-LEGAL"
    intake.business_name = "Cambio Legal"
    intake.responsible_name = "Carlo Responsable"
    intake.contact_phone = "+584121112233"
    intake.business_phone = "+584129998877"
    intake.min_amount_usd = "20.00"
    intake.max_amount_usd = "100.00"

    admin = _login(client, 9045, "admin_legal_missing")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    response = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "accept_legal_missing"), "Content-Type": "application/json"},
        json={
            "reason": "datos incompletos",
            "create_business": True,
            "public_business_name": "Cambio Legal",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_INTAKE_INCOMPLETE"
    assert "cedula" in response.text
    assert "RIF" in response.text
    assert "limite diario" in response.text
    assert client.app.state.business_repository.businesses == {}


def test_admin_accept_can_create_pending_business_with_public_name() -> None:
    client = _client()
    started = _start(client, update_id=570, telegram_id=7042, chat_id=8042)
    _contact(client, started["id"], update_id=571, telegram_id=7042, chat_id=8042)
    _submit(client, started["id"], update_id=572, telegram_id=7042, chat_id=8042)
    admin = _login(client, 9042, "admin_create_intake_business")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    response = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "accept_create_business"), "Content-Type": "application/json"},
        json={
            "reason": "documents reviewed",
            "create_business": True,
            "public_business_name": "Casa Publica NODO",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["created_business"] is True
    assert data["access_link_created"] is False
    assert data["business"]["business_name"] == "Casa Publica NODO"
    assert data["business"]["verification_status"] == "pending"
    assert data["intake"]["created_business_id"] == data["business"]["id"]

    business = client.app.state.business_repository.get_business(data["business"]["id"])
    applicant = client.app.state.user_repository.get_user_by_telegram_id(7042)
    assert business.business_name == "Casa Publica NODO"
    assert business.owner_user_id == applicant.id
    assert business.rif == "J-12345678-9"
    assert str(business.min_order_amount_usd) == "20.00"
    assert str(business.max_order_amount_usd) == "100.00"
    assert str(business.daily_limit_usd) == "1000.00"
    assert business.verification_status == "pending"
    assert applicant.role == "remitter"
    assert client.app.state.business_repository.access_links == {}
    assert "business_created_from_intake" in _event_types(client)


def test_admin_accept_can_approve_business_link_owner_and_send_business_bot_button(monkeypatch: Any) -> None:
    client = _client(TELEGRAM_WEB_APP_URL="https://nodo.example.test")
    telegram_id = 7043
    chat_id = 8043
    sent_messages: list[dict[str, Any]] = []
    menu_buttons: list[dict[str, Any]] = []

    def fake_send(bot_token: str, sent_chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        sent_messages.append({"bot_token": bot_token, "chat_id": sent_chat_id, "text": text, "reply_markup": reply_markup})

    def fake_set_menu(bot_token: str, sent_chat_id: int, text: str, web_app_url: str) -> None:
        menu_buttons.append({"bot_token": bot_token, "chat_id": sent_chat_id, "text": text, "web_app_url": web_app_url})

    monkeypatch.setattr(intake_business_creation, "telegram_send_message_sync", fake_send)
    monkeypatch.setattr(intake_business_creation, "telegram_set_chat_menu_button_sync", fake_set_menu)

    started = _start(client, update_id=580, telegram_id=telegram_id, chat_id=chat_id)
    _contact(client, started["id"], update_id=581, telegram_id=telegram_id, chat_id=chat_id)
    _submit(client, started["id"], update_id=582, telegram_id=telegram_id, chat_id=chat_id)
    admin = _login(client, 9043, "admin_approve_intake_business")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    response = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "accept_approve_business"), "Content-Type": "application/json"},
        json={
            "reason": "documents reviewed and business approved",
            "create_business": True,
            "approve_business": True,
            "public_business_name": "Casa Aprobada NODO",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["created_business"] is True
    assert data["access_link_created"] is True
    assert data["approval_notification_sent"] is True
    assert data["business"]["business_name"] == "Casa Aprobada NODO"
    assert data["business"]["verification_status"] == "approved"

    business = client.app.state.business_repository.get_business(data["business"]["id"])
    applicant = client.app.state.user_repository.get_user_by_telegram_id(telegram_id)
    assert business.verification_status == "approved"
    assert business.owner_user_id == applicant.id
    assert applicant.role == "business_owner"
    link = next(iter(client.app.state.business_repository.access_links.values()))
    assert link.business_id == business.id
    assert link.user_id == applicant.id
    assert link.telegram_id_snapshot == telegram_id
    assert link.status == "active"

    assert sent_messages[0]["bot_token"] == BUSINESS_INTAKE_BOT_TOKEN
    assert sent_messages[0]["chat_id"] == chat_id
    assert sent_messages[0]["text"] == intake_business_creation.BUSINESS_APPROVAL_MESSAGE
    assert sent_messages[0]["reply_markup"]["inline_keyboard"][0][0] == {
        "text": intake_business_creation.BUSINESS_APPROVAL_BUTTON_TEXT,
        "web_app": {"url": "https://nodo.example.test/business/"},
    }
    assert menu_buttons == [
        {
            "bot_token": BUSINESS_INTAKE_BOT_TOKEN,
            "chat_id": chat_id,
            "text": intake_business_creation.BUSINESS_MENU_BUTTON_TEXT,
            "web_app_url": "https://nodo.example.test/business/",
        }
    ]

    business_login = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": "req_business_intake_bot_login", "X-NODO-Surface": "business_mini_app"},
        json={"init_data": _signed_init_data(telegram_id, "approved_business_owner", bot_token=BUSINESS_INTAKE_BOT_TOKEN)},
    )
    assert business_login.status_code == 200, business_login.text
    surface = client.get(
        "/api/v1/surface/session",
        headers={
            "Authorization": f"Bearer {business_login.json()['data']['access_token']}",
            "X-NODO-Surface": "business_mini_app",
            "X-Request-Id": "req_business_surface_after_intake_approval",
        },
    )
    assert surface.status_code == 200, surface.text
    assert surface.json()["data"]["allowed"] is True
    assert surface.json()["data"]["business"]["id"] == business.id

    webhook_messages: list[dict[str, Any]] = []
    webhook_menu_buttons: list[dict[str, Any]] = []

    async def fake_async_send(bot_token: str, sent_chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        webhook_messages.append({"bot_token": bot_token, "chat_id": sent_chat_id, "text": text, "reply_markup": reply_markup})

    async def fake_async_set_menu(bot_token: str, sent_chat_id: int, text: str, web_app_url: str) -> None:
        webhook_menu_buttons.append({"bot_token": bot_token, "chat_id": sent_chat_id, "text": text, "web_app_url": web_app_url})

    monkeypatch.setattr(intake_service, "telegram_send_message", fake_async_send)
    monkeypatch.setattr(intake_routes, "telegram_send_message", fake_async_send)
    monkeypatch.setattr(intake_service, "telegram_set_chat_menu_button", fake_async_set_menu)
    start_again = _business_webhook(client, _telegram_message(584, telegram_id=telegram_id, chat_id=chat_id, text="/start"))

    assert start_again.status_code == 200, start_again.text
    assert start_again.json()["data"]["action"] == "approved_business_open_sent"
    assert start_again.json()["data"]["business_id"] == business.id
    assert webhook_messages[0]["text"] != intake_business_creation.BUSINESS_APPROVAL_MESSAGE
    assert webhook_messages == [
        {
            "bot_token": BUSINESS_INTAKE_BOT_TOKEN,
            "chat_id": chat_id,
            "text": intake_conversation.BUSINESS_OPEN_MESSAGE,
            "reply_markup": {
                "inline_keyboard": [
                    [
                        {
                            "text": intake_business_creation.BUSINESS_APPROVAL_BUTTON_TEXT,
                            "web_app": {"url": "https://nodo.example.test/business/"},
                        }
                    ]
                ]
            },
        }
    ]
    assert webhook_menu_buttons == [
        {
            "bot_token": BUSINESS_INTAKE_BOT_TOKEN,
            "chat_id": chat_id,
            "text": intake_business_creation.BUSINESS_MENU_BUTTON_TEXT,
            "web_app_url": "https://nodo.example.test/business/",
        }
    ]
    assert {
        "business_approved",
        "business_access_linked",
        "business_intake_approval_notification_sent",
        "business_intake_approved_business_start",
    }.issubset(set(_event_types(client)))


def test_admin_accept_keeps_intake_documents_visible_on_created_business_detail(monkeypatch: Any) -> None:
    client = _client(TELEGRAM_WEB_APP_URL="https://nodo.example.test")
    telegram_id = 7048
    chat_id = 8048

    monkeypatch.setattr(intake_business_creation, "telegram_send_message_sync", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(intake_business_creation, "telegram_set_chat_menu_button_sync", lambda *_args, **_kwargs: None)

    started = _start(client, update_id=585, telegram_id=telegram_id, chat_id=chat_id)
    _contact(client, started["id"], update_id=586, telegram_id=telegram_id, chat_id=chat_id)
    _upload_intake_doc(client, started["id"], update_id=587, request_id="intake_doc_for_business_detail")
    _submit(client, started["id"], update_id=588, telegram_id=telegram_id, chat_id=chat_id)
    admin = _login(client, 9048, "admin_intake_docs_business_detail")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    accepted = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "accept_approve_business_with_docs"), "Content-Type": "application/json"},
        json={
            "reason": "documents reviewed and business approved",
            "create_business": True,
            "approve_business": True,
            "public_business_name": "Casa Documentada NODO",
        },
    )

    assert accepted.status_code == 200, accepted.text
    business_id = accepted.json()["data"]["business"]["id"]
    detail = client.get(
        f"/api/v1/admin/businesses/{business_id}",
        headers=_bearer(admin, "req_business_detail_after_intake_docs"),
    )

    assert detail.status_code == 200, detail.text
    documents = detail.json()["data"]["documents"]
    assert len(documents) == 1
    assert documents[0]["file_type"] == "intake_document"
    assert documents[0]["mime_type"] == "application/pdf"
    assert "storage_path" not in documents[0]

    view_url = client.post(
        f"/api/v1/admin/businesses/{business_id}/verification-documents/{documents[0]['id']}/view-url",
        headers=_bearer(admin, "req_business_detail_intake_doc_view_url"),
        json={"reason": "reviewing linked intake document"},
    )

    assert view_url.status_code == 200, view_url.text
    assert view_url.json()["data"]["expires_in"] <= 300
    assert "storage_path" not in view_url.text

    repeated = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "accept_approve_business_with_docs_again"), "Content-Type": "application/json"},
        json={
            "reason": "documents rechecked",
            "create_business": False,
            "approve_business": True,
        },
    )

    assert repeated.status_code == 200, repeated.text
    repeated_detail = client.get(
        f"/api/v1/admin/businesses/{business_id}",
        headers=_bearer(admin, "req_business_detail_after_intake_docs_recheck"),
    )
    assert len(repeated_detail.json()["data"]["documents"]) == 1


def test_admin_accept_can_approve_existing_intake_created_business(monkeypatch: Any) -> None:
    client = _client()
    sent_messages: list[dict[str, Any]] = []

    def fake_send(bot_token: str, sent_chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        sent_messages.append({"bot_token": bot_token, "chat_id": sent_chat_id, "text": text, "reply_markup": reply_markup})

    monkeypatch.setattr(intake_business_creation, "telegram_send_message_sync", fake_send)

    started = _start(client, update_id=590, telegram_id=7044, chat_id=8044)
    _contact(client, started["id"], update_id=591, telegram_id=7044, chat_id=8044)
    _submit(client, started["id"], update_id=592, telegram_id=7044, chat_id=8044)
    admin = _login(client, 9044, "admin_approve_existing_intake_business")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    pending = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "accept_create_pending_then_approve"), "Content-Type": "application/json"},
        json={
            "reason": "documents reviewed",
            "create_business": True,
            "public_business_name": "Casa Pendiente NODO",
        },
    )
    assert pending.status_code == 200, pending.text
    assert pending.json()["data"]["business"]["verification_status"] == "pending"

    approved = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "accept_approve_existing_business"), "Content-Type": "application/json"},
        json={
            "reason": "final approval",
            "create_business": False,
            "approve_business": True,
        },
    )

    assert approved.status_code == 200, approved.text
    data = approved.json()["data"]
    assert data["created_business"] is False
    assert data["access_link_created"] is True
    assert data["approval_notification_sent"] is True
    assert data["business"]["id"] == pending.json()["data"]["business"]["id"]
    assert data["business"]["verification_status"] == "approved"
    assert sent_messages


def test_admin_reject_requires_idempotency_and_does_not_create_business() -> None:
    client = _client()
    started = _start(client, update_id=600, telegram_id=7051, chat_id=8051)
    _contact(client, started["id"], update_id=601, telegram_id=7051, chat_id=8051)
    _submit(client, started["id"], update_id=602, telegram_id=7051, chat_id=8051)
    admin = _login(client, 9011, "admin_reject")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    no_idem = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/reject",
        headers={**_bearer(admin, "req_no_idem"), "Content-Type": "application/json"},
        json={"reason": "insufficient evidence"},
    )
    assert no_idem.status_code == 400
    assert no_idem.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    rejected = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/reject",
        headers={**_admin_headers(admin, "reject_once"), "Content-Type": "application/json"},
        json={},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["data"]["intake"]["status"] == "rejected"
    assert client.app.state.business_repository.businesses == {}
    assert client.app.state.business_repository.access_links == {}
    assert "business_intake_rejected" in _event_types(client)


def test_admin_can_delete_bad_intake_with_reason_and_idempotency(monkeypatch: Any) -> None:
    client = _client()
    started = _start(client, update_id=650, telegram_id=7061, chat_id=8061)
    _contact(client, started["id"], update_id=651, telegram_id=7061, chat_id=8061)
    _submit(client, started["id"], update_id=652, telegram_id=7061, chat_id=8061)
    upload = client.post(
        f"/api/v1/business-intake/{started['id']}/documents",
        headers=_bot_headers("delete_doc"),
        data={"document_kind": "rif_document", "telegram_update_id": 653},
        files={"file": ("rif.pdf", b"private-pdf", "application/pdf")},
    )
    assert upload.status_code == 201, upload.text

    admin = _login(client, 9021, "admin_delete")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    support = _login(client, 9022, "support_delete")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")
    sent_messages: list[dict[str, Any]] = []

    def fake_send(bot_token: str, sent_chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        sent_messages.append({"bot_token": bot_token, "chat_id": sent_chat_id, "text": text, "reply_markup": reply_markup})

    monkeypatch.setattr(intake_admin_delete, "telegram_send_message_sync", fake_send)

    support_delete = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/delete",
        headers={**_admin_headers(support, "support_delete"), "Content-Type": "application/json"},
        json={"reason": "support cannot delete"},
    )
    assert support_delete.status_code == 403

    no_idem = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/delete",
        headers={**_bearer(admin, "req_delete_no_idem"), "Content-Type": "application/json"},
        json={"reason": "bad submission"},
    )
    assert no_idem.status_code == 400
    assert no_idem.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    deleted_1 = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/delete",
        headers={**_admin_headers(admin, "delete_once"), "Content-Type": "application/json"},
        json={"reason": "bad submission"},
    )
    deleted_2 = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/delete",
        headers={**_admin_headers(admin, "delete_once"), "Content-Type": "application/json"},
        json={"reason": "bad submission"},
    )
    assert deleted_1.status_code == 200, deleted_1.text
    assert deleted_2.status_code == 200, deleted_2.text
    assert deleted_1.json()["data"]["deleted"] is True
    assert deleted_1.json()["data"]["intakes_deleted"] == 1
    assert deleted_1.json()["data"]["documents_deleted"] == 1
    assert deleted_1.json()["data"]["reset_notification_sent"] is True
    assert deleted_2.json()["data"] == deleted_1.json()["data"]
    assert client.app.state.business_intake_repository.get(started["id"]) is None
    assert client.app.state.business_intake_repository.list_documents(started["id"]) == []
    assert _event_types(client).count("business_intake_deleted") == 1
    assert _event_types(client).count("business_intake_reset_notification_sent") == 1
    assert len(sent_messages) == 1
    assert sent_messages[0] == {
        "bot_token": BUSINESS_INTAKE_BOT_TOKEN,
        "chat_id": 8061,
        "text": intake_admin_delete.BUSINESS_INTAKE_RESET_MESSAGE,
        "reply_markup": None,
    }


def test_admin_can_reset_intake_without_typing_reason() -> None:
    client = _client()
    started = _start(client, update_id=655, telegram_id=7065, chat_id=8065)
    _contact(client, started["id"], update_id=656, telegram_id=7065, chat_id=8065)
    _submit(client, started["id"], update_id=657, telegram_id=7065, chat_id=8065)
    admin = _login(client, 9025, "admin_delete_without_reason")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    deleted = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/delete",
        headers={**_admin_headers(admin, "delete_without_reason"), "Content-Type": "application/json"},
        json={},
    )

    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["data"]["deleted"] is True
    assert client.app.state.business_intake_repository.get(started["id"]) is None
    delete_events = [event for event in client.app.state.audit_writer.events if event.event_type == "business_intake_deleted"]
    assert delete_events[-1].metadata_json["reason"] == "admin_reset_onboarding"


def test_admin_can_complete_intake_manually_and_submit_for_review() -> None:
    client = _client()
    started = _start(client, update_id=660, telegram_id=7066, chat_id=8066)
    _contact(client, started["id"], update_id=661, telegram_id=7066, chat_id=8066)
    _upload_intake_doc(client, started["id"], update_id=662, request_id="manual_complete_doc")
    admin = _login(client, 9026, "admin_manual_intake_update")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    updated = client.patch(
        f"/api/v1/admin/business-intake/{started['id']}",
        headers={**_admin_headers(admin, "manual_update_intake"), "Content-Type": "application/json"},
        json={
            "referral_code": "REF-MANUAL",
            "contact_phone": "+584121112233",
            "business_name": "Cambio Manual",
            "business_tax_id": "J-98765432-1",
            "responsible_name": "Carlo Responsable",
            "responsible_id_number": "V-87654321",
            "city": "Caracas",
            "business_phone": "+584129998877",
            "operation": "ambas",
            "banks": ["Banesco", "Mercantil"],
            "methods": ["Zelle", "USDT TRC20"],
            "min_amount_usd": "20",
            "max_amount_usd": "100",
            "daily_limit_usd": "1000",
            "schedule": "Lunes a viernes 9am a 6pm",
            "references": ["@referencia"],
            "submit_for_review": True,
        },
    )

    assert updated.status_code == 200, updated.text
    intake = updated.json()["data"]["intake"]
    assert intake["status"] == "submitted"
    assert intake["last_step"] == "submitted"
    assert intake["referral_code"] == "REF-MANUAL"
    assert intake["contact_phone"] == "+584121112233"
    assert intake["business_phone"] == "+584129998877"
    assert intake["business_name"] == "Cambio Manual"
    assert intake["business_tax_id"] == "J-98765432-1"
    assert intake["responsible_id_number"] == "V-87654321"
    assert intake["daily_limit_usd"] == "1000"
    assert intake["operation"] == "both"
    assert intake["methods"] == ["zelle", "usdt_trc20"]
    assert "business_intake_admin_updated" in _event_types(client)

    approved = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/accept",
        headers={**_admin_headers(admin, "manual_update_then_accept"), "Content-Type": "application/json"},
        json={"reason": "datos confirmados por whatsapp"},
    )

    assert approved.status_code == 200, approved.text
    assert approved.json()["data"]["intake"]["status"] == "accepted"


def test_admin_can_save_partial_intake_without_submitting_or_approving() -> None:
    client = _client()
    started = _start(client, update_id=663, telegram_id=7063, chat_id=8063)
    admin = _login(client, 9023, "admin_partial_intake_update")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    updated = client.patch(
        f"/api/v1/admin/business-intake/{started['id']}",
        headers={**_admin_headers(admin, "partial_update_intake"), "Content-Type": "application/json"},
        json={
            "business_name": "Cambio Parcial",
            "business_tax_id": "J-10000000-1",
        },
    )

    assert updated.status_code == 200, updated.text
    intake = updated.json()["data"]["intake"]
    assert intake["business_name"] == "Cambio Parcial"
    assert intake["business_tax_id"] == "J-10000000-1"
    assert intake["status"] == "draft"
    assert intake["last_step"] == "awaiting_referral_code"


def test_admin_can_view_intake_document_without_manual_reason() -> None:
    client = _client()
    started = _start(client, update_id=665, telegram_id=7067, chat_id=8067)
    _contact(client, started["id"], update_id=666, telegram_id=7067, chat_id=8067)
    _submit(client, started["id"], update_id=667, telegram_id=7067, chat_id=8067)
    admin = _login(client, 9027, "admin_view_document_without_reason")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    detail = client.get(f"/api/v1/admin/business-intake/{started['id']}", headers=_bearer(admin, "doc_without_reason_detail"))
    file_id = detail.json()["data"]["documents"][0]["id"]

    viewed = client.post(
        f"/api/v1/admin/business-intake/{started['id']}/documents/{file_id}/view-url",
        headers={**_bearer(admin, "doc_without_reason"), "Content-Type": "application/json"},
        json={},
    )

    assert viewed.status_code == 200, viewed.text
    assert viewed.json()["data"]["download_filename"].startswith("nodo-intake-")
    document_events = [event for event in client.app.state.audit_writer.events if event.event_type == "business_intake_document_viewed"]
    assert document_events[-1].metadata_json["reason"] == "admin_document_review"


def test_business_intake_webhook_requires_business_bot_secret_and_rejects_client_secret() -> None:
    client = _client()
    update = _telegram_message(900, text="/start")

    client_secret = telegram_webhook_secret(BOT_TOKEN)
    wrong_secret = _business_webhook(client, update, secret=client_secret)
    assert wrong_secret.status_code == 403
    assert wrong_secret.json()["error"]["code"] == "FORBIDDEN"

    missing_token = _client(BUSINESS_INTAKE_BOT_TOKEN="")
    configured_secret = telegram_webhook_secret(BUSINESS_INTAKE_BOT_TOKEN)
    missing = _business_webhook(missing_token, update, secret=configured_secret)
    assert missing.status_code == 503
    assert missing.json()["error"]["code"] == "TELEGRAM_BOT_NOT_CONFIGURED"


def test_business_intake_conversation_persists_each_step_and_submits(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client()
    intake_id, sent_messages = _drive_conversation_to_documents(client, monkeypatch, telegram_id=7311, chat_id=8311, start_update=1100)

    intake = client.app.state.business_intake_repository.get(intake_id)
    assert intake is not None
    assert intake.status == "draft"
    assert intake.last_step == "awaiting_documents"
    assert intake.referral_code == "REF-CARLOS-01"
    assert intake.contact_phone == "+584121234567"
    assert intake.min_amount_usd == "20.00"
    assert intake.max_amount_usd == "100.00"
    assert intake.daily_limit_usd == "1000.00"
    assert intake.schedule_text == "El negocio opera con el boton online/offline de NODO."
    assert intake.references_json == ["@referenciauno", "@referenciados"]
    assert all(message["bot_token"] == BUSINESS_INTAKE_BOT_TOKEN for message in sent_messages)
    assert any("Redes sociales obligatorias" in message["text"] for message in sent_messages)
    assert all("monto minimo" not in message["text"].lower() for message in sent_messages)
    assert all("horario habitual" not in message["text"].lower() for message in sent_messages)

    async def fake_download(bot_token: str, file_id: str) -> bytes:
        return b"private-pdf-content"

    monkeypatch.setattr(intake_service, "telegram_download_file", fake_download)
    upload = _business_webhook(
        client,
        _telegram_message(
            1113,
            telegram_id=7311,
            chat_id=8311,
            extra={
                "document": {
                    "file_id": "telegram-submit-file",
                    "file_unique_id": "telegram-submit-file-unique",
                    "file_name": "rif.pdf",
                    "mime_type": "application/pdf",
                    "file_size": 64,
                }
            },
        ),
    )
    assert upload.status_code == 200, upload.text

    submitted = _business_webhook(client, _telegram_message(1114, telegram_id=7311, chat_id=8311, text="finalizar"))
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["data"]["status"] == "submitted"
    assert submitted.json()["data"]["last_step"] == "submitted"
    final_intake = client.app.state.business_intake_repository.get(intake_id)
    assert final_intake is not None
    assert final_intake.status == "submitted"
    assert sent_messages[-1]["text"] == "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso."
    assert {
        "business_intake_started",
        "business_intake_step_answered",
        "business_intake_document_uploaded",
        "business_intake_submitted",
    }.issubset(set(_event_types(client)))
    assert client.app.state.business_repository.businesses == {}
    assert client.app.state.business_repository.access_links == {}


def test_business_intake_webhook_old_update_retry_is_safe_noop(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client()
    sent_messages: list[dict[str, Any]] = []

    async def fake_send(bot_token: str, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        sent_messages.append({"bot_token": bot_token, "chat_id": chat_id, "text": text, "reply_markup": reply_markup})

    monkeypatch.setattr(intake_service, "telegram_send_message", fake_send)
    monkeypatch.setattr(intake_routes, "telegram_send_message", fake_send)

    start = _business_webhook(client, _telegram_message(1500, telegram_id=7351, chat_id=8351, text="/start"))
    assert start.status_code == 200, start.text
    referral_update = _telegram_message(1501, telegram_id=7351, chat_id=8351, text="REF-RETRY")
    referral = _business_webhook(client, referral_update)
    assert referral.status_code == 200, referral.text
    name = _business_webhook(client, _telegram_message(1502, telegram_id=7351, chat_id=8351, text="+584121234567"))
    assert name.status_code == 200, name.text

    retry_old_referral = _business_webhook(client, referral_update)
    assert retry_old_referral.status_code == 200, retry_old_referral.text
    assert retry_old_referral.json()["data"]["duplicate_update"] is True
    intake = client.app.state.business_intake_repository.get(start.json()["data"]["intake_id"])
    assert intake is not None
    assert intake.last_step == "awaiting_business_name"
    assert intake.referral_code == "REF-RETRY"
    assert intake.contact_phone == "+584121234567"


def test_business_intake_webhook_message_after_submitted_does_not_create_new_draft(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client()
    intake_id, _sent_messages = _drive_conversation_to_documents(client, monkeypatch, telegram_id=7361, chat_id=8361, start_update=1600)

    async def fake_download(bot_token: str, file_id: str) -> bytes:
        return b"private-pdf-content"

    monkeypatch.setattr(intake_service, "telegram_download_file", fake_download)
    upload = _business_webhook(
        client,
        _telegram_message(
            1613,
            telegram_id=7361,
            chat_id=8361,
            extra={
                "document": {
                    "file_id": "telegram-after-submit-file",
                    "file_unique_id": "telegram-after-submit-file-unique",
                    "file_name": "rif.pdf",
                    "mime_type": "application/pdf",
                    "file_size": 64,
                }
            },
        ),
    )
    assert upload.status_code == 200, upload.text
    submitted = _business_webhook(client, _telegram_message(1614, telegram_id=7361, chat_id=8361, text="finalizar"))
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["data"]["status"] == "submitted"
    intake_count = len(client.app.state.business_intake_repository.intakes)

    extra_message = _business_webhook(client, _telegram_message(1615, telegram_id=7361, chat_id=8361, text="otro mensaje"))
    assert extra_message.status_code == 200, extra_message.text
    assert extra_message.json()["data"]["intake_id"] == intake_id
    assert extra_message.json()["data"]["status"] == "submitted"
    assert len(client.app.state.business_intake_repository.intakes) == intake_count
    final_intake = client.app.state.business_intake_repository.get(intake_id)
    assert final_intake is not None
    assert final_intake.status == "submitted"
    assert final_intake.last_step == "submitted"


def test_business_intake_conversation_rejects_bad_contact_and_invalid_step_input(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client()
    sent_messages: list[dict[str, Any]] = []

    async def fake_send(bot_token: str, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        sent_messages.append({"bot_token": bot_token, "chat_id": chat_id, "text": text, "reply_markup": reply_markup})

    monkeypatch.setattr(intake_service, "telegram_send_message", fake_send)
    monkeypatch.setattr(intake_routes, "telegram_send_message", fake_send)

    start = _business_webhook(client, _telegram_message(1200, telegram_id=7321, chat_id=8321, text="/start"))
    assert start.status_code == 200, start.text

    valid_referral = _business_webhook(client, _telegram_message(1201, telegram_id=7321, chat_id=8321, text="REF-001"))
    assert valid_referral.status_code == 200, valid_referral.text

    invalid_whatsapp = _business_webhook(client, _telegram_message(1202, telegram_id=7321, chat_id=8321, text="12"))
    assert invalid_whatsapp.status_code == 200
    assert invalid_whatsapp.json()["data"]["recoverable_error"] == "BOT_INPUT_INVALID"
    intake = client.app.state.business_intake_repository.get(start.json()["data"]["intake_id"])
    assert intake is not None
    assert intake.last_step == "awaiting_whatsapp_phone"
    assert "WhatsApp" in sent_messages[-1]["text"]

    valid_whatsapp = _business_webhook(client, _telegram_message(1203, telegram_id=7321, chat_id=8321, text="+584121234567"))
    assert valid_whatsapp.status_code == 200, valid_whatsapp.text
    early_document = _business_webhook(
        client,
        _telegram_message(
            1204,
            telegram_id=7321,
            chat_id=8321,
            extra={
                "document": {
                    "file_id": "too-early-file",
                    "file_unique_id": "too-early-file-unique",
                    "file_name": "rif.pdf",
                    "mime_type": "application/pdf",
                    "file_size": 64,
                }
            },
        ),
    )
    assert early_document.status_code == 200
    assert early_document.json()["data"]["recoverable_error"] == "BOT_INPUT_INVALID"
    assert "No pude usar esa respuesta" in sent_messages[-1]["text"]


def test_business_intake_conversation_requires_social_references_before_documents(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client()
    sent_messages: list[dict[str, Any]] = []

    async def fake_send(bot_token: str, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        sent_messages.append({"bot_token": bot_token, "chat_id": chat_id, "text": text, "reply_markup": reply_markup})

    monkeypatch.setattr(intake_service, "telegram_send_message", fake_send)
    monkeypatch.setattr(intake_routes, "telegram_send_message", fake_send)

    start_update = 1800
    telegram_id = 7381
    chat_id = 8381
    start = _business_webhook(client, _telegram_message(start_update, telegram_id=telegram_id, chat_id=chat_id, text="/start"))
    assert start.status_code == 200, start.text
    intake_id = start.json()["data"]["intake_id"]
    answers_to_methods = [
        "REF-CARLOS-01",
        "+584121234567",
        "Casa Cambio Centro",
        "J-12345678-9",
        "Carlo Responsable",
        "V-12345678",
        "Caracas",
        "+582121234567",
        "both",
        "Mercantil, Banesco",
        "zelle, usdt_trc20",
    ]
    for offset, answer in enumerate(answers_to_methods, start=1):
        response = _business_webhook(client, _telegram_message(start_update + offset, telegram_id=telegram_id, chat_id=chat_id, text=answer))
        assert response.status_code == 200, response.text

    intake = client.app.state.business_intake_repository.get(intake_id)
    assert intake is not None
    assert intake.last_step == "awaiting_references"
    assert intake.min_amount_usd == "20.00"
    assert intake.max_amount_usd == "100.00"
    assert intake.daily_limit_usd == "1000.00"
    assert any("Redes sociales obligatorias" in message["text"] for message in sent_messages)

    rejected = _business_webhook(client, _telegram_message(1812, telegram_id=telegram_id, chat_id=chat_id, text="no"))
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["data"]["recoverable_error"] == "BOT_INPUT_INVALID"
    rejected_intake = client.app.state.business_intake_repository.get(intake_id)
    assert rejected_intake is not None
    assert rejected_intake.last_step == "awaiting_references"

    accepted = _business_webhook(client, _telegram_message(1813, telegram_id=telegram_id, chat_id=chat_id, text="@casa_cambio"))
    assert accepted.status_code == 200, accepted.text
    accepted_intake = client.app.state.business_intake_repository.get(intake_id)
    assert accepted_intake is not None
    assert accepted_intake.last_step == "awaiting_documents"
    assert accepted_intake.references_json == ["@casa_cambio"]


def test_business_intake_telegram_document_downloads_private_storage_and_dedupes(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client()
    intake_id, sent_messages = _drive_conversation_to_documents(client, monkeypatch, telegram_id=7331, chat_id=8331, start_update=1300)
    prompt_count_before_upload = len(sent_messages)
    downloads: list[dict[str, str]] = []

    async def fake_download(bot_token: str, file_id: str) -> bytes:
        downloads.append({"bot_token": bot_token, "file_id": file_id})
        return b"private-pdf-content"

    monkeypatch.setattr(intake_service, "telegram_download_file", fake_download)

    document_update = _telegram_message(
        1313,
        telegram_id=7331,
        chat_id=8331,
        extra={
            "document": {
                "file_id": "telegram-file-1",
                "file_unique_id": "unique-file-1",
                "file_name": "rif.pdf",
                "mime_type": "application/pdf",
                "file_size": 64,
            }
        },
    )
    uploaded = _business_webhook(client, document_update)
    duplicate = _business_webhook(client, document_update)

    assert uploaded.status_code == 200, uploaded.text
    assert duplicate.status_code == 200, duplicate.text
    assert uploaded.json()["data"]["file_id"]
    assert duplicate.json()["data"]["duplicate_update"] is True
    assert downloads == [{"bot_token": BUSINESS_INTAKE_BOT_TOKEN, "file_id": "telegram-file-1"}]
    documents = client.app.state.business_intake_repository.list_documents(intake_id)
    assert len(documents) == 1
    assert documents[0].telegram_file_id == "telegram-file-1"
    assert documents[0].telegram_file_unique_id == "unique-file-1"
    assert "storage_path" not in uploaded.text
    assert "business_intake_document_uploaded" in _event_types(client)
    assert all(message["bot_token"] == BUSINESS_INTAKE_BOT_TOKEN for message in sent_messages)
    assert len(sent_messages) == prompt_count_before_upload


def test_business_intake_photo_album_does_not_repeat_document_prompt(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client()
    intake_id, sent_messages = _drive_conversation_to_documents(client, monkeypatch, telegram_id=7371, chat_id=8371, start_update=1700)
    prompt_count_before_album = len(sent_messages)

    async def fake_download(bot_token: str, file_id: str) -> bytes:
        return f"private-photo-{file_id}".encode()

    monkeypatch.setattr(intake_service, "telegram_download_file", fake_download)

    for index in range(5):
        photo_update = _telegram_message(
            1713 + index,
            telegram_id=7371,
            chat_id=8371,
            extra={
                "media_group_id": "album-1",
                "photo": [
                    {
                        "file_id": f"photo-{index}",
                        "file_unique_id": f"unique-photo-{index}",
                        "file_size": 120 + index,
                    }
                ],
            },
        )
        uploaded = _business_webhook(client, photo_update)
        assert uploaded.status_code == 200, uploaded.text

    documents = client.app.state.business_intake_repository.list_documents(intake_id)
    assert len(documents) == 5
    assert len(sent_messages) == prompt_count_before_album

    submitted = _business_webhook(client, _telegram_message(1722, telegram_id=7371, chat_id=8371, text="Finalizar"))
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["data"]["status"] == "submitted"
    assert sent_messages[-1]["text"] == "Solicitud recibida. Revisaremos tu informacion y te avisaremos el siguiente paso."


def test_business_intake_telegram_rejects_video_invalid_mime_and_large_file(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    client = _client()
    sent_messages: list[dict[str, Any]] = []

    async def fake_send(bot_token: str, chat_id: int, text: str, reply_markup: dict[str, Any] | None = None) -> None:
        sent_messages.append({"bot_token": bot_token, "chat_id": chat_id, "text": text, "reply_markup": reply_markup})

    _drive_conversation_to_documents(client, monkeypatch, telegram_id=7341, chat_id=8341, start_update=1400)
    monkeypatch.setattr(intake_routes, "telegram_send_message", fake_send)

    video = _business_webhook(
        client,
        _telegram_message(1416, telegram_id=7341, chat_id=8341, extra={"video": {"file_id": "video-1", "file_size": 12}}),
    )
    assert video.status_code == 200
    assert video.json()["data"]["recoverable_error"] == "BOT_UPLOAD_INVALID"
    assert "imagen o PDF" in sent_messages[-1]["text"]

    invalid_mime = _business_webhook(
        client,
        _telegram_message(
            1417,
            telegram_id=7341,
            chat_id=8341,
            extra={
                "document": {
                    "file_id": "doc-zip",
                    "file_unique_id": "zip-1",
                    "file_name": "bad.zip",
                    "mime_type": "application/zip",
                    "file_size": 64,
                }
            },
        ),
    )
    assert invalid_mime.status_code == 200
    assert invalid_mime.json()["data"]["recoverable_error"] == "BOT_UPLOAD_INVALID"

    too_large = _business_webhook(
        client,
        _telegram_message(
            1418,
            telegram_id=7341,
            chat_id=8341,
            extra={
                "document": {
                    "file_id": "doc-large",
                    "file_unique_id": "large-1",
                    "file_name": "large.pdf",
                    "mime_type": "application/pdf",
                    "file_size": 5 * 1024 * 1024 + 1,
                }
            },
        ),
    )
    assert too_large.status_code == 200
    assert too_large.json()["data"]["recoverable_error"] == "BOT_UPLOAD_INVALID"
