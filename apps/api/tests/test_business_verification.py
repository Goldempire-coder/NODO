from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from urllib.parse import urlencode

from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-02",
        "NODO_BUILD_ID": "pytest-business-build",
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


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    return TestClient(create_app())


def _signed_init_data(telegram_id: int = 101, username: str = "user") -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": username}, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def _login(client: TestClient, telegram_id: int = 101, username: str = "user") -> dict:
    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": f"req_login_{telegram_id}"},
        json={"init_data": _signed_init_data(telegram_id=telegram_id, username=username)},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _headers(login: dict, key: str = "idem") -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _create_business(client: TestClient, login: dict, key: str = "create") -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, key), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={
            "business_name": "Casa Cambio Centro",
            "rif": "J-12345678-9",
            "address": "Av Principal",
            "phone": "+584121234567",
            "country": "VE",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["business"]


def _upload_doc(client: TestClient, login: dict, business_id: str, file_type: str, *, content: bytes = b"safe-file") -> dict:
    response = client.post(
        f"/api/v1/businesses/{business_id}/verification-documents",
        headers={
            "Authorization": f"Bearer {login['access_token']}",
            "X-Request-Id": f"req_upload_{file_type}",
            "X-NODO-Test-Fixture": "business_create",
        },
        files={"file": ("document.pdf", content, "application/pdf")},
        data={"file_type": file_type},
    )
    assert response.status_code == 201
    payload = response.json()
    assert "storage_path" not in response.text
    return payload["data"]["file"]


def _upload_required_docs(client: TestClient, login: dict, business_id: str) -> list[str]:
    return [
        _upload_doc(client, login, business_id, "rif_document")["id"],
        _upload_doc(client, login, business_id, "business_license")["id"],
        _upload_doc(client, login, business_id, "owner_identity")["id"],
        _upload_doc(client, login, business_id, "address_proof")["id"],
    ]


def _submit(client: TestClient, login: dict, business_id: str, file_ids: list[str], key: str = "submit") -> dict:
    response = client.post(
        f"/api/v1/businesses/{business_id}/submit-verification",
        headers={**_headers(login, key), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={
            "submitted_data": {
                "business_name": "Casa Cambio Centro",
                "rif": "J-12345678-9",
                "address": "Av Principal",
                "phone": "+584121234567",
                "country": "VE",
                "document_file_ids": file_ids,
            }
        },
    )
    assert response.status_code == 200
    assert "storage_path" not in response.text
    return response.json()["data"]


def _set_role(client: TestClient, user_id: str, role: str) -> None:
    user = client.app.state.user_repository.get_user_by_id(user_id)
    user.role = role


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_guest_cannot_create_business() -> None:
    client = _client()
    response = client.post(
        "/api/v1/businesses",
        headers={"X-Request-Id": "req_guest", "Idempotency-Key": "guest"},
        json={"business_name": "Guest", "country": "VE"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHENTICATED"


def test_authenticated_user_cannot_self_onboard_business() -> None:
    client = _client()
    login = _login(client)
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, "self_onboarding_disabled"), "Content-Type": "application/json"},
        json={"business_name": "Casa Directa", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "BUSINESS_SELF_ONBOARDING_DISABLED"
    assert client.app.state.user_repository.get_user_by_id(login["user"]["id"]).role == "remitter"


def test_legacy_owner_verification_endpoints_are_disabled_without_test_fixture_header() -> None:
    client = _client()
    login = _login(client)
    business = _create_business(client, login)

    update = client.put(
        f"/api/v1/businesses/{business['id']}",
        headers={**_headers(login, "legacy_update_disabled"), "Content-Type": "application/json"},
        json={"business_name": "Cambio publico", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    upload = client.post(
        f"/api/v1/businesses/{business['id']}/verification-documents",
        headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_legacy_upload_disabled"},
        files={"file": ("document.pdf", b"safe-file", "application/pdf")},
        data={"file_type": "rif_document"},
    )
    submit = client.post(
        f"/api/v1/businesses/{business['id']}/submit-verification",
        headers={**_headers(login, "legacy_submit_disabled"), "Content-Type": "application/json"},
        json={
            "submitted_data": {
                "business_name": "Cambio publico",
                "rif": "J-12345678-9",
                "address": "Av Principal",
                "phone": "+584121234567",
                "country": "VE",
                "document_file_ids": [
                    "00000000-0000-4000-8000-000000000001",
                    "00000000-0000-4000-8000-000000000002",
                    "00000000-0000-4000-8000-000000000003",
                    "00000000-0000-4000-8000-000000000004",
                ],
            }
        },
    )

    for response in [update, upload, submit]:
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "BUSINESS_SELF_ONBOARDING_DISABLED"


def test_create_business_promotes_owner_and_blocks_duplicate_active_business() -> None:
    client = _client()
    login = _login(client)
    business = _create_business(client, login)

    assert business["verification_status"] == "pending"
    assert business["trust_level"] == "new"
    assert client.app.state.user_repository.get_user_by_id(login["user"]["id"]).role == "business_owner"
    duplicate = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, "create_duplicate"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": "Otro", "country": "VE"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "BUSINESS_ALREADY_EXISTS"
    assert "business_created" in _event_types(client)


def test_owner_cannot_edit_other_business_or_admin_fields() -> None:
    client = _client()
    owner_login = _login(client, 201, "owner")
    other_login = _login(client, 202, "other")
    business = _create_business(client, owner_login, "create_owner")

    response = client.put(
        f"/api/v1/businesses/{business['id']}",
        headers={**_headers(other_login, "edit_other"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": "Nombre ajeno", "verification_status": "approved", "trust_level": "pro"},
    )
    assert response.status_code == 403
    stored = client.app.state.business_repository.get_business(business["id"])
    assert stored.verification_status == "pending"
    assert stored.trust_level == "new"


def test_submit_requires_all_required_documents_and_does_not_duplicate_pending_submission() -> None:
    client = _client()
    login = _login(client)
    business = _create_business(client, login)
    one_file = [_upload_doc(client, login, business["id"], "rif_document")["id"]]

    missing = client.post(
        f"/api/v1/businesses/{business['id']}/submit-verification",
        headers={**_headers(login, "submit_missing"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={
            "submitted_data": {
                "business_name": "Casa Cambio Centro",
                "rif": "J-12345678-9",
                "address": "Av Principal",
                "phone": "+584121234567",
                "country": "VE",
                "document_file_ids": one_file,
            }
        },
    )
    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "BUSINESS_DOCUMENT_REQUIRED"

    file_ids = _upload_required_docs(client, login, business["id"])
    submitted = _submit(client, login, business["id"], file_ids)
    assert submitted["submission"]["status"] == "pending"
    duplicate = client.post(
        f"/api/v1/businesses/{business['id']}/submit-verification",
        headers={**_headers(login, "submit_second"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={
            "submitted_data": {
                "business_name": "Casa Cambio Centro",
                "rif": "J-12345678-9",
                "address": "Av Principal",
                "phone": "+584121234567",
                "country": "VE",
                "document_file_ids": file_ids,
            }
        },
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "BUSINESS_ALREADY_SUBMITTED"


def test_upload_rejects_invalid_mime_and_oversize_and_never_exposes_storage_path() -> None:
    client = _client()
    login = _login(client)
    business = _create_business(client, login)

    invalid = client.post(
        f"/api/v1/businesses/{business['id']}/verification-documents",
        headers={
            "Authorization": f"Bearer {login['access_token']}",
            "X-Request-Id": "req_bad_upload",
            "X-NODO-Test-Fixture": "business_create",
        },
        files={"file": ("document.txt", b"bad", "text/plain")},
        data={"file_type": "rif_document"},
    )
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "BUSINESS_DOCUMENT_INVALID"

    oversize = client.post(
        f"/api/v1/businesses/{business['id']}/verification-documents",
        headers={
            "Authorization": f"Bearer {login['access_token']}",
            "X-Request-Id": "req_big_upload",
            "X-NODO-Test-Fixture": "business_create",
        },
        files={"file": ("document.pdf", b"x" * (5 * 1024 * 1024 + 1), "application/pdf")},
        data={"file_type": "rif_document"},
    )
    assert oversize.status_code == 400
    assert "storage_path" not in invalid.text + oversize.text


def test_admin_pending_pagination_support_readonly_and_approve_reject_permissions() -> None:
    client = _client()
    owner_login = _login(client, 301, "owner")
    support_login = _login(client, 302, "support")
    admin_login = _login(client, 303, "admin")
    _set_role(client, support_login["user"]["id"], "support")
    _set_role(client, admin_login["user"]["id"], "admin")

    business = _create_business(client, owner_login)
    file_ids = _upload_required_docs(client, owner_login, business["id"])
    _submit(client, owner_login, business["id"], file_ids)

    pending = client.get("/api/v1/admin/businesses/pending?limit=1", headers={"Authorization": f"Bearer {support_login['access_token']}", "X-Request-Id": "req_support_pending"})
    assert pending.status_code == 200
    assert len(pending.json()["data"]["items"]) == 1
    assert "storage_path" not in pending.text

    support_approve = client.post(
        f"/api/v1/admin/businesses/{business['id']}/approve",
        headers={**_headers(support_login, "support_approve"), "Content-Type": "application/json"},
        json={"reason": "No debe aprobar"},
    )
    assert support_approve.status_code == 403
    assert support_approve.json()["error"]["code"] == "FORBIDDEN"

    missing_reason = client.post(
        f"/api/v1/admin/businesses/{business['id']}/approve",
        headers={**_headers(admin_login, "admin_approve_missing"), "Content-Type": "application/json"},
        json={"reason": ""},
    )
    assert missing_reason.status_code == 400
    assert missing_reason.json()["error"]["code"] == "ADMIN_REASON_REQUIRED"

    approved = client.post(
        f"/api/v1/admin/businesses/{business['id']}/approve",
        headers={**_headers(admin_login, "admin_approve"), "Content-Type": "application/json"},
        json={"reason": "Datos validados manualmente"},
    )
    assert approved.status_code == 200
    assert approved.json()["data"]["business"]["verification_status"] == "approved"
    assert "business_approved" in _event_types(client)

    reject_after_approve = client.post(
        f"/api/v1/admin/businesses/{business['id']}/reject",
        headers={**_headers(admin_login, "admin_reject_after_approve"), "Content-Type": "application/json"},
        json={"reason": "No procede"},
    )
    assert reject_after_approve.status_code == 409
    assert reject_after_approve.json()["error"]["code"] == "BUSINESS_STATUS_INVALID"


def test_signed_url_requires_admin_reason_audits_and_is_not_persisted() -> None:
    client = _client()
    owner_login = _login(client, 401, "owner")
    admin_login = _login(client, 402, "admin")
    support_login = _login(client, 403, "support")
    _set_role(client, admin_login["user"]["id"], "admin")
    _set_role(client, support_login["user"]["id"], "support")
    business = _create_business(client, owner_login)
    file_id = _upload_doc(client, owner_login, business["id"], "rif_document")["id"]

    forbidden = client.post(
        f"/api/v1/admin/businesses/{business['id']}/verification-documents/{file_id}/view-url",
        headers={"Authorization": f"Bearer {support_login['access_token']}", "X-Request-Id": "req_support_view"},
        json={"reason": "Revision"},
    )
    assert forbidden.status_code == 403

    ok = client.post(
        f"/api/v1/admin/businesses/{business['id']}/verification-documents/{file_id}/view-url",
        headers={"Authorization": f"Bearer {admin_login['access_token']}", "X-Request-Id": "req_admin_view"},
        json={"reason": "Revision de documento RIF para aprobacion"},
    )
    assert ok.status_code == 200
    assert ok.json()["data"]["expires_in"] <= 300
    assert "storage_path" not in ok.text
    assert "verification_document_viewed" in _event_types(client)
    audit_text = json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert ok.json()["data"]["url"] not in audit_text


def test_idempotency_payload_mismatch_and_rate_limit_are_enforced() -> None:
    client = _client(BUSINESS_RATE_LIMIT_MAX_ATTEMPTS="1")
    login = _login(client)

    first = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, "same_key"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": "Casa Uno", "country": "VE"},
    )
    assert first.status_code == 201

    mismatch = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, "same_key"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": "Casa Dos", "country": "VE"},
    )
    assert mismatch.status_code in {409, 429}
    if mismatch.status_code == 409:
        assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"

    first_update = client.put(
        f"/api/v1/businesses/{first.json()['data']['business']['id']}",
        headers={**_headers(login, "rate_update"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": "Casa Tres"},
    )
    assert first_update.status_code == 200

    limited = client.put(
        f"/api/v1/businesses/{first.json()['data']['business']['id']}",
        headers={**_headers(login, "rate_update_second"), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": "Casa Cuatro"},
    )
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "RATE_LIMITED"


def test_sensitive_values_are_not_leaked_in_responses_or_audit() -> None:
    client = _client()
    login = _login(client)
    business = _create_business(client, login)
    file_ids = _upload_required_docs(client, login, business["id"])
    _submit(client, login, business["id"], file_ids)

    response = client.get("/api/v1/businesses/me", headers={"Authorization": f"Bearer {login['access_token']}", "X-Request-Id": "req_me_business"})
    combined = response.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "storage_path" not in combined
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined
    assert login["access_token"] not in combined
    assert login["refresh_token"] not in combined
