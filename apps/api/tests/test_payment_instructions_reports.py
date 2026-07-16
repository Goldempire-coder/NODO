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
        "APP_VERSION": "0.0.0-slice-05",
        "NODO_BUILD_ID": "pytest-payment-reports-build",
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
    return response.json()["data"]


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


def _approved_business_with_method(client: TestClient, login: dict, *, method: str = "zelle", credits: int = 5) -> tuple[dict, str]:
    business = _create_business(client, login, f"biz_{method}_{login['user']['id']}")
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
        account_value="owner@example.com" if method == "zelle" else "TFullWalletValue123456789",
        account_masked="***.com" if method == "zelle" else "TFull...6789",
        holder_name="Owner Test",
    )
    payment.verified_status = "approved"
    payment.active = True
    if credits:
        client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=credits, created_by=login["user"]["id"])
    return business, payment.id


def _create_ad(client: TestClient, owner: dict, payment_method_id: str, *, method: str = "zelle", key: str = "ad") -> dict:
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


def _seed_order(client: TestClient, *, method: str = "zelle", owner_id: int = 600, remitter_id: int = 601) -> tuple[dict, dict, dict, dict]:
    owner = _login(client, owner_id, f"owner_{owner_id}")
    business, method_id = _approved_business_with_method(client, owner, method=method, credits=1)
    ad = _create_ad(client, owner, method_id, method=method, key=f"ad_{method}_{owner_id}")
    remitter = _login(client, remitter_id, f"remitter_{remitter_id}")
    order = _create_order(client, remitter, ad["id"], key=f"order_{method}_{remitter_id}")
    return business, ad, remitter, order


def _upload_evidence(client: TestClient, remitter: dict, order_id: str, key: str = "evidence", pending_id: str | None = None, content: bytes = b"proof") -> dict:
    data = {"file_type": "payment_evidence"}
    if pending_id:
        data["pending_payment_report_id"] = pending_id
    response = client.post(
        f"/api/v1/orders/{order_id}/payment-evidence",
        headers=_headers(remitter, key),
        data=data,
        files={"file": ("proof.png", content, "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_reveal_own_waiting_payment_sets_tracking_audit_and_only_endpoint_exposes_full_account() -> None:
    client = _client()
    _, _, remitter, order = _seed_order(client)

    reveal = client.get(f"/api/v1/orders/{order['id']}/payment-instructions", headers=_bearer(remitter, "req_reveal"))

    assert reveal.status_code == 200, reveal.text
    body = reveal.json()["data"]
    assert body["payment_instructions"]["account_value"] == "owner@example.com"
    stored = client.app.state.order_repository.get_by_id(order["id"])
    assert stored.payment_data_revealed_at is not None
    assert stored.payment_data_revealed_by == remitter["user"]["id"]
    assert client.app.state.order_repository.payment_reports == {}
    assert stored.status == "waiting_payment"
    assert "payment_instructions_viewed" in _event_types(client)
    detail = client.get(f"/api/v1/orders/{order['id']}", headers=_bearer(remitter, "req_detail_no_full"))
    assert "owner@example.com" not in detail.text
    audit_text = json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "owner@example.com" not in audit_text


def test_reveal_foreign_and_expired_order_are_blocked_safely() -> None:
    client = _client()
    _, _, remitter, order = _seed_order(client, owner_id=610, remitter_id=611)
    other = _login(client, 612, "other")

    foreign = client.get(f"/api/v1/orders/{order['id']}/payment-instructions", headers=_bearer(other, "req_foreign_reveal"))
    stored = client.app.state.order_repository.get_by_id(order["id"])
    client.app.state.order_repository.update_order(stored, payment_report_deadline_at=stored.created_at - timedelta(minutes=1), expires_at=stored.created_at - timedelta(minutes=1))
    expired = client.get(f"/api/v1/orders/{order['id']}/payment-instructions", headers=_bearer(remitter, "req_expired_reveal"))

    assert foreign.status_code == 404
    assert foreign.json()["error"]["code"] == "ORDER_NOT_FOUND"
    assert expired.status_code == 409
    assert expired.json()["error"]["code"] == "ORDER_EXPIRED"


def test_payment_evidence_upload_owner_only_pending_id_validation_and_no_private_path_exposure() -> None:
    client = _client()
    _, _, remitter, order = _seed_order(client, owner_id=620, remitter_id=621)
    other = _login(client, 622, "other")

    foreign = client.post(
        f"/api/v1/orders/{order['id']}/payment-evidence",
        headers=_headers(other, "foreign_evidence"),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", b"proof", "image/png")},
    )
    evidence = _upload_evidence(client, remitter, order["id"], key="own_evidence")
    invalid_mime = client.post(
        f"/api/v1/orders/{order['id']}/payment-evidence",
        headers=_headers(remitter, "invalid_mime"),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.txt", b"proof", "text/plain")},
    )
    too_large = client.post(
        f"/api/v1/orders/{order['id']}/payment-evidence",
        headers=_headers(remitter, "too_large"),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
    )
    invalid_pending_id = client.post(
        f"/api/v1/orders/{order['id']}/payment-evidence",
        headers=_headers(remitter, "invalid_pending_id"),
        data={"file_type": "payment_evidence", "pending_payment_report_id": "not-a-uuid"},
        files={"file": ("proof.png", b"proof", "image/png")},
    )

    assert foreign.status_code == 404
    assert evidence["file"]["file_type"] == "payment_evidence"
    assert evidence["pending_payment_report_id"]
    assert "storage_path" not in json.dumps(evidence)
    assert invalid_mime.status_code == 400
    assert invalid_mime.json()["error"]["code"] == "INVALID_PAYMENT_EVIDENCE"
    assert too_large.status_code == 400
    assert too_large.json()["error"]["code"] == "INVALID_PAYMENT_EVIDENCE"
    assert invalid_pending_id.status_code == 400
    assert invalid_pending_id.json()["error"]["code"] == "INVALID_PAYMENT_EVIDENCE"
    assert "payment_evidence_uploaded" in _event_types(client)


def test_report_zelle_valid_changes_state_without_consuming_credits_or_changing_ad() -> None:
    client = _client()
    business, ad, remitter, order = _seed_order(client, owner_id=630, remitter_id=631)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    evidence = _upload_evidence(client, remitter, order["id"], key="zelle_evidence")

    report = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={**_headers(remitter, "zelle_report"), "Content-Type": "application/json"},
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

    assert report.status_code == 201, report.text
    assert report.json()["data"]["order"]["status"] == "payment_reported"
    stored = client.app.state.order_repository.get_by_id(order["id"])
    assert stored.status == "payment_reported"
    assert stored.paid_reported_at is not None
    assert stored.business_response_warning_at is not None
    assert stored.business_response_deadline_at is not None
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.available_credits == wallet_before.available_credits
    assert wallet_after.blocked_credits == wallet_before.blocked_credits
    assert wallet_after.consumed_credits == wallet_before.consumed_credits
    assert {"payment_reported", "payment_evidence_uploaded"}.issubset(set(_event_types(client)))
    assert client.app.state.order_repository.events[-1].event_type == "payment_reported"
    combined = report.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "owner@example.com" not in combined
    assert "storage_path" not in combined
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined


def test_report_usdt_valid_invalid_method_missing_evidence_expired_and_foreign_failures() -> None:
    client = _client()
    _, _, remitter, usdt_order = _seed_order(client, method="usdt_trc20", owner_id=640, remitter_id=641)
    usdt = client.post(
        f"/api/v1/orders/{usdt_order['id']}/payment-report",
        headers={**_headers(remitter, "usdt_report"), "Content-Type": "application/json"},
        json={"payment_type": "usdt_trc20", "tx_hash": "0xabcdef1234567890abcdef", "network": "TRC20", "payment_amount": "50.00"},
    )
    assert usdt.status_code == 201, usdt.text
    assert usdt.json()["data"]["payment_report"]["tx_hash_masked"] == "0xabcd...cdef"

    _, _, zelle_remitter, zelle_order = _seed_order(client, owner_id=642, remitter_id=643)
    invalid_method = client.post(
        f"/api/v1/orders/{zelle_order['id']}/payment-report",
        headers={**_headers(zelle_remitter, "invalid_method"), "Content-Type": "application/json"},
        json={"payment_type": "usdt_trc20", "tx_hash": "0xabcdef1234567890abcdef", "network": "TRC20", "payment_amount": "50.00"},
    )
    missing_evidence = client.post(
        f"/api/v1/orders/{zelle_order['id']}/payment-report",
        headers={**_headers(zelle_remitter, "missing_evidence"), "Content-Type": "application/json"},
        json={"payment_type": "zelle", "payment_reference": "ABC", "payment_sender_name": "Sender", "payment_amount": "50.00"},
    )
    other = _login(client, 644, "other")
    foreign = client.post(
        f"/api/v1/orders/{zelle_order['id']}/payment-report",
        headers={**_headers(other, "foreign_report"), "Content-Type": "application/json"},
        json={"payment_type": "zelle", "payment_reference": "ABC", "payment_sender_name": "Sender", "payment_amount": "50.00", "proof_file_id": "missing", "pending_payment_report_id": "missing"},
    )
    stored = client.app.state.order_repository.get_by_id(zelle_order["id"])
    client.app.state.order_repository.update_order(stored, payment_report_deadline_at=stored.created_at - timedelta(minutes=1), expires_at=stored.created_at - timedelta(minutes=1))
    expired = client.post(
        f"/api/v1/orders/{zelle_order['id']}/payment-report",
        headers={**_headers(zelle_remitter, "expired_report"), "Content-Type": "application/json"},
        json={"payment_type": "zelle", "payment_reference": "ABC", "payment_sender_name": "Sender", "payment_amount": "50.00", "proof_file_id": "missing", "pending_payment_report_id": "missing"},
    )

    assert invalid_method.status_code == 400
    assert invalid_method.json()["error"]["code"] == "INVALID_PAYMENT_METHOD"
    assert missing_evidence.status_code == 400
    assert missing_evidence.json()["error"]["code"] == "PAYMENT_EVIDENCE_REQUIRED"
    assert foreign.status_code == 404
    assert expired.status_code == 409
    assert expired.json()["error"]["code"] == "ORDER_EXPIRED"


def test_payment_report_idempotency_replay_and_payload_mismatch() -> None:
    client = _client()
    _, _, remitter, order = _seed_order(client, owner_id=650, remitter_id=651)
    evidence = _upload_evidence(client, remitter, order["id"], key="idem_evidence")
    payload = {
        "payment_type": "zelle",
        "payment_reference": "ABC123456",
        "payment_sender_name": "Remitter Test",
        "payment_amount": "50.00",
        "proof_file_id": evidence["file"]["id"],
        "pending_payment_report_id": evidence["pending_payment_report_id"],
    }

    first = client.post(f"/api/v1/orders/{order['id']}/payment-report", headers={**_headers(remitter, "same_report"), "Content-Type": "application/json"}, json=payload)
    replay = client.post(f"/api/v1/orders/{order['id']}/payment-report", headers={**_headers(remitter, "same_report"), "Content-Type": "application/json"}, json=payload)
    mismatch = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={**_headers(remitter, "same_report"), "Content-Type": "application/json"},
        json={**payload, "payment_reference": "CHANGED"},
    )

    assert first.status_code == 201
    assert replay.status_code in {200, 201}
    assert replay.json()["data"]["payment_report"]["id"] == first.json()["data"]["payment_report"]["id"]
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"


def test_migration_0006_contains_payment_reports_file_assets_constraints_and_indexes() -> None:
    migration = open("database/migrations/0006_slice_05_payment_instructions_reports.up.sql", encoding="utf-8").read()
    for text in [
        "create table if not exists payment_reports",
        "payment_reports_zelle_required_check",
        "payment_reports_usdt_required_check",
        "payment_reports_order_submitted_idx",
        "payment_reports_reported_by_idempotency_idx",
        "file_type in ('rif_document', 'business_license', 'owner_identity', 'address_proof', 'payment_evidence')",
        "resource_type in ('business', 'payment_report')",
    ]:
        assert text in migration
