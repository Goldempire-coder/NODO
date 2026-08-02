from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.core.errors import ApiError
from app.modules.orders.models import new_id


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"
USDT_TX_HASH = "0x" + ("abcdef1234567890" * 4)
USDT_TX_HASH_ALT = "0x" + ("1234567890abcdef" * 4)


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


def _seed_order_context(
    client: TestClient,
    *,
    method: str = "zelle",
    owner_id: int = 600,
    remitter_id: int = 601,
    share_zelle: bool = True,
) -> tuple[dict, dict, dict, dict, dict]:
    owner = _login(client, owner_id, f"owner_{owner_id}")
    business, method_id = _approved_business_with_method(client, owner, method=method, credits=1)
    ad = _create_ad(client, owner, method_id, method=method, key=f"ad_{method}_{owner_id}")
    remitter = _login(client, remitter_id, f"remitter_{remitter_id}")
    order = _create_order(
        client,
        remitter,
        ad["id"],
        key=f"order_{method}_{owner_id}_{remitter_id}",
    )
    if method == "zelle" and share_zelle:
        shared = client.post(
            f"/api/v1/orders/{order['id']}/share-zelle",
            headers=_headers(owner, f"share_zelle_{owner_id}_{remitter_id}"),
        )
        assert shared.status_code == 201, shared.text
    return owner, business, ad, remitter, order


def _seed_order(client: TestClient, *, method: str = "zelle", owner_id: int = 600, remitter_id: int = 601) -> tuple[dict, dict, dict, dict]:
    _, business, ad, remitter, order = _seed_order_context(
        client,
        method=method,
        owner_id=owner_id,
        remitter_id=remitter_id,
    )
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


def _replace_evidence_content_hash(client: TestClient, evidence: dict, value: str | None) -> None:
    file = client.app.state.order_repository.files[evidence["file"]["id"]]
    metadata = dict(file.metadata_json or {})
    if value is None:
        metadata.pop("content_sha256", None)
    else:
        metadata["content_sha256"] = value
    file.metadata_json = metadata


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_slice_50a_zelle_payment_is_blocked_until_business_shares_configured_account() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_order_context(
        client,
        owner_id=605,
        remitter_id=606,
        share_zelle=False,
    )

    reveal_before = client.get(
        f"/api/v1/orders/{order['id']}/payment-instructions",
        headers=_bearer(remitter, "req_slice50a_reveal_before"),
    )
    evidence = _upload_evidence(
        client,
        remitter,
        order["id"],
        key="slice50a_evidence_before_share",
        content=b"slice50a-proof",
    )
    report_before = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={**_headers(remitter, "slice50a_report_before_share"), "Content-Type": "application/json"},
        json={
            "payment_type": "zelle",
            "payment_reference": "SLICE50A123",
            "payment_sender_name": "Remitter Test",
            "payment_amount": "50.00",
            "proof_file_id": evidence["file"]["id"],
            "pending_payment_report_id": evidence["pending_payment_report_id"],
        },
    )

    assert reveal_before.status_code == 409
    assert reveal_before.json()["error"]["code"] == "ORDER_PAYMENT_DETAILS_NOT_SHARED"
    assert report_before.status_code == 409
    assert report_before.json()["error"]["code"] == "ORDER_PAYMENT_DETAILS_NOT_SHARED"
    stored_before = client.app.state.order_repository.get_by_id(order["id"])
    assert stored_before.status == "waiting_payment"
    assert stored_before.payment_data_revealed_at is None
    assert client.app.state.order_repository.payment_reports == {}

    shared = client.post(
        f"/api/v1/orders/{order['id']}/share-zelle",
        headers=_headers(owner, "slice50a_share_then_pay"),
    )
    reveal_after = client.get(
        f"/api/v1/orders/{order['id']}/payment-instructions",
        headers=_bearer(remitter, "req_slice50a_reveal_after"),
    )

    assert shared.status_code == 201, shared.text
    assert reveal_after.status_code == 200, reveal_after.text
    assert reveal_after.json()["data"]["payment_instructions"]["account_value"] == "owner@example.com"


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


def test_slice_50c_zelle_report_accepts_locked_amount_with_optional_proof() -> None:
    client = _client()
    business, ad, remitter, order = _seed_order(client, owner_id=632, remitter_id=633)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    evidence = _upload_evidence(
        client,
        remitter,
        order["id"],
        key="slice50c_zelle_evidence_only",
        content=b"slice50c-zelle-proof",
    )

    report = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={**_headers(remitter, "slice50c_zelle_report_minimal"), "Content-Type": "application/json"},
        json={
            "payment_type": "zelle",
            "payment_amount": "50.00",
            "proof_file_id": evidence["file"]["id"],
            "pending_payment_report_id": evidence["pending_payment_report_id"],
        },
    )

    assert report.status_code == 201, report.text
    assert report.json()["data"]["order"]["status"] == "payment_reported"
    assert report.json()["data"]["payment_report"]["payment_reference_masked"] is None
    stored = client.app.state.order_repository.get_by_id(order["id"])
    assert stored.status == "payment_reported"
    assert stored.paid_reported_at is not None
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.available_credits == wallet_before.available_credits
    assert wallet_after.blocked_credits == wallet_before.blocked_credits
    assert wallet_after.consumed_credits == wallet_before.consumed_credits


def test_report_usdt_valid_invalid_method_expired_and_foreign_failures() -> None:
    client = _client()
    _, _, remitter, usdt_order = _seed_order(client, method="usdt_trc20", owner_id=640, remitter_id=641)
    usdt = client.post(
        f"/api/v1/orders/{usdt_order['id']}/payment-report",
        headers={**_headers(remitter, "usdt_report"), "Content-Type": "application/json"},
        json={"payment_type": "usdt_trc20", "tx_hash": USDT_TX_HASH.upper(), "network": "TRC20", "payment_amount": "50.00"},
    )
    assert usdt.status_code == 201, usdt.text
    assert usdt.json()["data"]["payment_report"]["tx_hash_masked"] == "abcdef...7890"

    _, _, zelle_remitter, zelle_order = _seed_order(client, owner_id=642, remitter_id=643)
    invalid_method = client.post(
        f"/api/v1/orders/{zelle_order['id']}/payment-report",
        headers={**_headers(zelle_remitter, "invalid_method"), "Content-Type": "application/json"},
        json={"payment_type": "usdt_trc20", "tx_hash": USDT_TX_HASH_ALT, "network": "TRC20", "payment_amount": "50.00"},
    )
    invalid_hash = client.post(
        f"/api/v1/orders/{zelle_order['id']}/payment-report",
        headers={**_headers(zelle_remitter, "invalid_hash"), "Content-Type": "application/json"},
        json={"payment_type": "usdt_trc20", "tx_hash": "not-a-real-hash", "network": "TRC20", "payment_amount": "50.00"},
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
    assert invalid_hash.status_code == 422
    assert invalid_hash.json()["error"]["code"] == "VALIDATION_ERROR"
    assert foreign.status_code == 404
    assert expired.status_code == 409
    assert expired.json()["error"]["code"] == "ORDER_EXPIRED"


def test_zelle_payment_report_allows_client_to_mark_paid_without_evidence() -> None:
    client = _client()
    _, _, remitter, order = _seed_order(
        client,
        owner_id=645,
        remitter_id=646,
    )

    response = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={
            **_headers(remitter, "zelle_without_evidence"),
            "Content-Type": "application/json",
        },
        json={
            "payment_type": "zelle",
            "payment_amount": "50.00",
        },
    )

    assert response.status_code == 201, response.text
    assert response.json()["data"]["order"]["status"] == "payment_reported"
    assert response.json()["data"]["payment_report"]["proof_file_id"] is None
    stored_report = client.app.state.order_repository.get_submitted_payment_report_for_order(order["id"])
    assert stored_report is not None
    assert stored_report.proof_file_id is None
    assert stored_report.proof_content_sha256 is None


def test_zelle_optional_evidence_rejects_incomplete_identity() -> None:
    client = _client()
    _, _, remitter, order = _seed_order(
        client,
        owner_id=647,
        remitter_id=648,
    )

    response = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={
            **_headers(remitter, "zelle_incomplete_evidence"),
            "Content-Type": "application/json",
        },
        json={
            "payment_type": "zelle",
            "payment_amount": "50.00",
            "pending_payment_report_id": new_id(),
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "INVALID_PAYMENT_EVIDENCE"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "waiting_payment"
    assert client.app.state.order_repository.get_submitted_payment_report_for_order(order["id"]) is None


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


def test_slice_49a_payment_report_requires_exact_order_amount() -> None:
    client = _client()
    _, _, remitter, order = _seed_order(
        client,
        method="usdt_trc20",
        owner_id=652,
        remitter_id=653,
    )

    response = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={
            **_headers(remitter, "slice49a_amount_mismatch"),
            "Content-Type": "application/json",
        },
        json={
            "payment_type": "usdt_trc20",
            "tx_hash": USDT_TX_HASH,
            "network": "TRC20",
            "payment_amount": "49.99",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "PAYMENT_REPORT_AMOUNT_MISMATCH"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "waiting_payment"
    assert client.app.state.order_repository.get_submitted_payment_report_for_order(order["id"]) is None


def test_slice_49a_canonical_transaction_hash_cannot_cross_orders() -> None:
    client = _client()
    _, _, first_remitter, first_order = _seed_order(
        client,
        method="usdt_trc20",
        owner_id=654,
        remitter_id=655,
    )
    _, _, second_remitter, second_order = _seed_order(
        client,
        method="usdt_trc20",
        owner_id=656,
        remitter_id=657,
    )
    first = client.post(
        f"/api/v1/orders/{first_order['id']}/payment-report",
        headers={
            **_headers(first_remitter, "slice49a_hash_first"),
            "Content-Type": "application/json",
        },
        json={
            "payment_type": "usdt_trc20",
            "tx_hash": USDT_TX_HASH.upper(),
            "network": "TRC20",
            "payment_amount": "50.00",
        },
    )
    second = client.post(
        f"/api/v1/orders/{second_order['id']}/payment-report",
        headers={
            **_headers(second_remitter, "slice49a_hash_second"),
            "Content-Type": "application/json",
        },
        json={
            "payment_type": "usdt_trc20",
            "tx_hash": USDT_TX_HASH,
            "network": "trc20",
            "payment_amount": "50.00",
        },
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "PAYMENT_REPORT_PROOF_ALREADY_USED"
    assert client.app.state.order_repository.get_by_id(second_order["id"]).status == "waiting_payment"
    assert client.app.state.order_repository.get_submitted_payment_report_for_order(second_order["id"]) is None


def test_slice_49a_zelle_evidence_cannot_cross_orders() -> None:
    client = _client()
    _, _, first_remitter, first_order = _seed_order(
        client,
        owner_id=674,
        remitter_id=675,
    )
    _, _, second_remitter, second_order = _seed_order(
        client,
        owner_id=676,
        remitter_id=675,
    )
    evidence = _upload_evidence(
        client,
        first_remitter,
        first_order["id"],
        key="slice49a_zelle_proof",
    )
    payload = {
        "payment_type": "zelle",
        "payment_reference": "ABC123456",
        "payment_sender_name": "Remitter Test",
        "payment_amount": "50.00",
        "proof_file_id": evidence["file"]["id"],
        "pending_payment_report_id": evidence["pending_payment_report_id"],
    }

    first = client.post(
        f"/api/v1/orders/{first_order['id']}/payment-report",
        headers={
            **_headers(first_remitter, "slice49a_zelle_first"),
            "Content-Type": "application/json",
        },
        json=payload,
    )
    second = client.post(
        f"/api/v1/orders/{second_order['id']}/payment-report",
        headers={
            **_headers(second_remitter, "slice49a_zelle_second"),
            "Content-Type": "application/json",
        },
        json=payload,
    )

    assert first.status_code == 201, first.text
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "INVALID_PAYMENT_EVIDENCE"
    assert client.app.state.order_repository.get_by_id(second_order["id"]).status == "waiting_payment"
    assert client.app.state.order_repository.get_submitted_payment_report_for_order(second_order["id"]) is None


def test_slice_49a_zelle_evidence_uploaded_for_order_a_cannot_initially_report_order_b() -> None:
    client = _client()
    _, _, remitter, first_order = _seed_order(
        client,
        owner_id=677,
        remitter_id=678,
    )
    _, _, same_remitter, second_order = _seed_order(
        client,
        owner_id=679,
        remitter_id=678,
    )
    evidence = _upload_evidence(
        client,
        remitter,
        first_order["id"],
        key="slice49a_initial_cross_order",
    )

    cross_order_report = client.post(
        f"/api/v1/orders/{second_order['id']}/payment-report",
        headers={
            **_headers(same_remitter, "slice49a_initial_cross_order_report"),
            "Content-Type": "application/json",
        },
        json={
            "payment_type": "zelle",
            "payment_reference": "ABC123456",
            "payment_sender_name": "Remitter Test",
            "payment_amount": "50.00",
            "proof_file_id": evidence["file"]["id"],
            "pending_payment_report_id": evidence["pending_payment_report_id"],
        },
    )

    assert cross_order_report.status_code == 400
    assert cross_order_report.json()["error"]["code"] == "INVALID_PAYMENT_EVIDENCE"
    assert client.app.state.order_repository.get_by_id(second_order["id"]).status == "waiting_payment"
    assert client.app.state.order_repository.get_submitted_payment_report_for_order(second_order["id"]) is None


def test_slice_49a_zelle_evidence_rejects_missing_short_or_non_hex_content_hash() -> None:
    cases = [
        ("missing", None),
        ("short", "a" * 63),
        ("non_hex", "g" * 64),
    ]
    for index, (label, content_hash) in enumerate(cases):
        client = _client()
        _, _, remitter, order = _seed_order(
            client,
            owner_id=680 + index * 2,
            remitter_id=681 + index * 2,
        )
        evidence = _upload_evidence(
            client,
            remitter,
            order["id"],
            key=f"slice49a_malformed_content_hash_{label}",
        )
        _replace_evidence_content_hash(client, evidence, content_hash)

        response = client.post(
            f"/api/v1/orders/{order['id']}/payment-report",
            headers={
                **_headers(remitter, f"slice49a_report_malformed_content_hash_{label}"),
                "Content-Type": "application/json",
            },
            json={
                "payment_type": "zelle",
                "payment_reference": "ABC123456",
                "payment_sender_name": "Remitter Test",
                "payment_amount": "50.00",
                "proof_file_id": evidence["file"]["id"],
                "pending_payment_report_id": evidence["pending_payment_report_id"],
            },
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "INVALID_PAYMENT_EVIDENCE"
        assert client.app.state.order_repository.get_by_id(order["id"]).status == "waiting_payment"
        assert client.app.state.order_repository.get_submitted_payment_report_for_order(order["id"]) is None


def test_slice_49a_zelle_evidence_content_cannot_be_reuploaded_for_another_order() -> None:
    client = _client()
    _, _, first_remitter, first_order = _seed_order(
        client,
        owner_id=677,
        remitter_id=678,
    )
    _, _, second_remitter, second_order = _seed_order(
        client,
        owner_id=679,
        remitter_id=678,
    )
    content = b"same visual proof bytes"
    first_evidence = _upload_evidence(
        client,
        first_remitter,
        first_order["id"],
        key="slice49a_hash_proof_first",
        content=content,
    )
    second_evidence = _upload_evidence(
        client,
        second_remitter,
        second_order["id"],
        key="slice49a_hash_proof_second",
        content=content,
    )

    first = client.post(
        f"/api/v1/orders/{first_order['id']}/payment-report",
        headers={
            **_headers(first_remitter, "slice49a_hash_first"),
            "Content-Type": "application/json",
        },
        json={
            "payment_type": "zelle",
            "payment_reference": "ABC123456",
            "payment_sender_name": "Remitter Test",
            "payment_amount": "50.00",
            "proof_file_id": first_evidence["file"]["id"],
            "pending_payment_report_id": first_evidence["pending_payment_report_id"],
        },
    )
    second = client.post(
        f"/api/v1/orders/{second_order['id']}/payment-report",
        headers={
            **_headers(second_remitter, "slice49a_hash_second"),
            "Content-Type": "application/json",
        },
        json={
            "payment_type": "zelle",
            "payment_reference": "XYZ987654",
            "payment_sender_name": "Remitter Test",
            "payment_amount": "50.00",
            "proof_file_id": second_evidence["file"]["id"],
            "pending_payment_report_id": second_evidence["pending_payment_report_id"],
        },
    )

    assert first.status_code == 201, first.text
    assert first_evidence["file"]["id"] != second_evidence["file"]["id"]
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "PAYMENT_REPORT_PROOF_ALREADY_USED"
    assert client.app.state.order_repository.get_by_id(second_order["id"]).status == "waiting_payment"
    assert client.app.state.order_repository.get_submitted_payment_report_for_order(second_order["id"]) is None


def test_slice_49a_payment_reveal_and_unconfirmed_cancel_have_one_winner() -> None:
    client = _client()
    _, _, remitter, order = _seed_order(
        client,
        owner_id=677,
        remitter_id=678,
    )

    def reveal() -> tuple[int, str | None]:
        response = client.get(
            f"/api/v1/orders/{order['id']}/payment-instructions",
            headers=_bearer(remitter, "req_slice49a_reveal_race"),
        )
        return response.status_code, response.json().get("error", {}).get("code")

    def cancel_without_confirmation() -> tuple[int, str | None]:
        response = client.post(
            f"/api/v1/orders/{order['id']}/cancel",
            headers={
                **_headers(remitter, "slice49a_reveal_cancel_race"),
                "Content-Type": "application/json",
            },
            json={
                "reason": "choose_another_business",
                "payment_not_sent_confirmed": False,
            },
        )
        return response.status_code, response.json().get("error", {}).get("code")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda action: action(),
                [reveal, cancel_without_confirmation],
            )
        )

    assert len([status for status, _ in results if status == 200]) == 1
    assert len([status for status, _ in results if status == 409]) == 1
    final_order = client.app.state.order_repository.get_by_id(order["id"])
    if final_order.status == "waiting_payment":
        assert final_order.payment_data_revealed_at is not None
        assert [code for _, code in results if code] == [
            "ORDER_PAYMENT_NOT_SENT_CONFIRMATION_REQUIRED"
        ]
    else:
        assert final_order.status == "cancelled"
        assert final_order.payment_data_revealed_at is None


def test_slice_49a_payment_and_cancel_race_has_one_winner() -> None:
    client = _client()
    _, ad, remitter, order = _seed_order(
        client,
        method="usdt_trc20",
        owner_id=658,
        remitter_id=659,
    )
    report_payload = {
        "payment_type": "usdt_trc20",
        "tx_hash": USDT_TX_HASH_ALT,
        "network": "TRC20",
        "payment_amount": "50.00",
    }

    def report_payment() -> tuple[int, str | None]:
        response = client.post(
            f"/api/v1/orders/{order['id']}/payment-report",
            headers={
                **_headers(remitter, "slice49a_race_report"),
                "Content-Type": "application/json",
            },
            json=report_payload,
        )
        return response.status_code, response.json().get("error", {}).get("code")

    def cancel_order() -> tuple[int, str | None]:
        response = client.post(
            f"/api/v1/orders/{order['id']}/cancel",
            headers={
                **_headers(remitter, "slice49a_race_cancel"),
                "Content-Type": "application/json",
            },
            json={
                "reason": "choose_another_business",
                "payment_not_sent_confirmed": True,
            },
        )
        return response.status_code, response.json().get("error", {}).get("code")

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda action: action(), [report_payment, cancel_order]))

    assert sorted(status for status, _ in results) == [201, 409] or sorted(
        status for status, _ in results
    ) == [200, 409]
    assert [code for _, code in results if code] == ["ORDER_STATE_CONFLICT"]
    stored = client.app.state.order_repository.get_by_id(order["id"])
    report = client.app.state.order_repository.get_submitted_payment_report_for_order(order["id"])
    if stored.status == "payment_reported":
        assert report is not None
        assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    else:
        assert stored.status == "cancelled"
        assert report is None
        assert client.app.state.ad_repository.get_ad(ad["id"]).status == "active"


def test_slice_49a_payment_and_expiration_race_keeps_report_and_capacity_consistent() -> None:
    client = _client()
    _, _, remitter, order = _seed_order(
        client,
        method="usdt_trc20",
        owner_id=660,
        remitter_id=661,
    )
    repository = client.app.state.order_repository
    stored = repository.get_by_id(order["id"])
    deadline = stored.payment_report_deadline_at
    report_id = new_id()
    report_fields = {
        "report_id": report_id,
        "order_id": stored.id,
        "reported_by_user_id": remitter["user"]["id"],
        "idempotency_key": "slice49a_expiration_race_report",
        "payment_type": "usdt_trc20",
        "payment_reference": None,
        "payment_sender_name": None,
        "payment_sender_account_masked": None,
        "tx_hash": "0x" + ("2" * 64),
        "network": "TRC20",
        "payment_amount": stored.amount_usd,
        "proof_file_id": None,
        "proof_content_sha256": None,
        "report_payload_hash": "slice49a-expiration-race",
    }

    def report_payment() -> str:
        try:
            repository.report_payment_atomically(
                order_id=stored.id,
                remitter_user_id=remitter["user"]["id"],
                create_report_fields=report_fields,
                paid_reported_at=deadline - timedelta(microseconds=1),
                business_response_warning_at=deadline + timedelta(hours=2),
                business_response_deadline_at=deadline + timedelta(hours=6),
                request_id="req_slice49a_expiration_race_report",
                event_metadata={"payment_report_id": report_id},
                audit_metadata={"payment_report_id": report_id},
            )
            return "payment_reported"
        except ApiError as exc:
            return exc.code

    def expire_order() -> str:
        try:
            repository.cancel_waiting_payment_atomically(
                order_id=stored.id,
                expected_remitter_user_id=None,
                expected_business_id=None,
                transition_at=deadline + timedelta(microseconds=1),
                require_expired=True,
                enforce_payment_not_sent_confirmation=False,
                payment_not_sent_confirmed=False,
                cancel_reason="payment_not_reported_in_time",
                event_type="order_cancelled_by_timeout",
                actor_user_id=None,
                actor_role=None,
                event_reason="payment_not_reported_in_time",
                request_id="req_slice49a_expiration_race_job",
                event_metadata={},
                audit_event_type="order_expired",
                audit_metadata={},
            )
            return "cancelled"
        except ApiError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda action: action(), [report_payment, expire_order]))

    assert sorted(results) == ["ORDER_STATE_CONFLICT", repository.get_by_id(stored.id).status]
    final_order = repository.get_by_id(stored.id)
    final_report = repository.get_submitted_payment_report_for_order(stored.id)
    reservation = client.app.state.capacity_repository.get_reservation(stored.id)
    if final_order.status == "payment_reported":
        assert final_report is not None
        assert reservation.status == "reserved"
    else:
        assert final_order.status == "cancelled"
        assert final_report is None
        assert reservation.status == "released"


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
