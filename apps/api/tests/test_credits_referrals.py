from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient
from PIL import Image

from app.core.errors import ApiError
from app.modules.credits.onchain import JsonRpcBaseUsdcVerifier, OnchainVerificationResult


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"
STRIPE_WEBHOOK_SECRET = "whsec_test_secret"
BASE_WALLET = "0x1111111111111111111111111111111111111111"
BASE_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
VALID_PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"


def _image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color=(20, 120, 220)).save(buffer, format=image_format)
    return buffer.getvalue()


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-08",
        "NODO_BUILD_ID": "pytest-credits-referrals-build",
        "DATABASE_URL": "postgresql://user:password@127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "JWT_SECRET": JWT_SECRET,
        "JWT_REFRESH_SECRET": JWT_REFRESH_SECRET,
        "STRIPE_SECRET_KEY": "sk_test_not_public",
        "STRIPE_WEBHOOK_SECRET": STRIPE_WEBHOOK_SECRET,
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
        "LEGACY_CREDIT_PAYMENT_METHODS_ENABLED": "1",
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.modules.businesses.models import utc_now  # noqa: E402
from app.modules.businesses.pin_security import hash_pin  # noqa: E402


class FakeBaseUsdcVerifier:
    def __init__(self) -> None:
        self.results: dict[str, OnchainVerificationResult] = {}
        self.calls: list[str] = []

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
        self.calls.append(tx_hash.lower())
        return self.results[tx_hash.lower()]


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    client = TestClient(create_app())
    client.app.state.onchain_credit_verifier = FakeBaseUsdcVerifier()
    client.app.state.verify_base_usdc_credit_purchases_worker._verifier = client.app.state.onchain_credit_verifier
    return client


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


def _create_business(client: TestClient, login: dict, key: str, *, approved: bool = True) -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, key), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": f"Casa {key}", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201, response.text
    business = response.json()["data"]["business"]
    stored = client.app.state.business_repository.get_business(business["id"])
    if approved:
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


def _stripe_signature(raw: bytes, *, secret: str = STRIPE_WEBHOOK_SECRET, timestamp: int | None = None) -> str:
    timestamp = timestamp or int(time.time())
    digest = hmac.new(secret.encode("utf-8"), f"{timestamp}.".encode("utf-8") + raw, hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={digest}"


def _checkout(client: TestClient, login: dict, package_code: str = "starter", key: str = "stripe") -> dict:
    response = client.post(
        "/api/v1/business/credits/stripe-checkout",
        headers={**_headers(login, key), "Content-Type": "application/json"},
        json={"package_code": package_code},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _stripe_completed_event(session_id: str, event_id: str = "evt_test_1") -> bytes:
    return json.dumps(
        {
            "id": event_id,
            "type": "checkout.session.completed",
            "data": {"object": {"id": session_id, "payment_intent": f"pi_{event_id}"}},
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _manual_payment(client: TestClient, login: dict, key: str = "manual", method: str = "zelle_manual_admin_approved") -> dict:
    data = {"package_code": "starter", "payment_method": method}
    if method == "zelle_manual_admin_approved":
        data["manual_payment_reference"] = "ZELLE-123456"
    else:
        data["manual_tx_hash"] = "0x" + "a" * 64
        data["manual_network"] = "TRC20"
    response = client.post(
        "/api/v1/business/credits/manual-payment",
        headers=_headers(login, key),
        data=data,
        files={"file": ("proof.pdf", VALID_PDF, "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


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


def _verification(
    tx_hash: str,
    *,
    amount_units: int = 10_000_000,
    confirmations: int = 6,
    status: str = "verified",
    error_code: str | None = None,
    chain_id: int = 8453,
    token: str = BASE_USDC,
    to_address: str = BASE_WALLET,
    log_index: int = 0,
) -> OnchainVerificationResult:
    return OnchainVerificationResult(
        chain_id=chain_id,
        token_contract_address=token.lower(),
        destination_wallet_address=BASE_WALLET,
        tx_hash=tx_hash.lower(),
        tx_from_address="0x2222222222222222222222222222222222222222",
        tx_to_address=to_address.lower(),
        tx_amount_units=amount_units,
        tx_block_number=123,
        tx_log_index=log_index,
        confirmations=confirmations,
        verification_status=status,
        error_code=error_code,
    )


def _transfer_log(*, to_address: str = BASE_WALLET, amount_units: int = 10_000_000, log_index: int = 0) -> dict:
    return {
        "address": BASE_USDC,
        "topics": [
            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
            "0x" + "0" * 24 + "2222222222222222222222222222222222222222",
            "0x" + "0" * 24 + to_address.removeprefix("0x"),
        ],
        "data": hex(amount_units),
        "logIndex": hex(log_index),
    }


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_base_usdc_verifier_rejects_failed_receipt() -> None:
    class FailedReceiptVerifier(JsonRpcBaseUsdcVerifier):
        def __init__(self) -> None:
            super().__init__(rpc_url="https://base-rpc.example", timeout_seconds=1)

        def _rpc(self, method: str, params: list[object]) -> object:
            if method == "eth_chainId":
                return "0x2105"
            if method == "eth_getTransactionReceipt":
                return {"status": "0x0", "blockNumber": "0x7b"}
            raise AssertionError(f"unexpected rpc method: {method}")

    tx_hash = _tx_hash("failed-receipt")
    result = FailedReceiptVerifier().verify(tx_hash=tx_hash, expected_amount_units=10_000_000, destination_wallet_address=BASE_WALLET, min_confirmations=3)

    assert result.verification_status == "verification_failed"
    assert result.error_code == "ONCHAIN_TX_FAILED"


def test_base_usdc_verifier_caches_chain_id_and_reuses_prefetched_block() -> None:
    class CountingVerifier(JsonRpcBaseUsdcVerifier):
        def __init__(self) -> None:
            super().__init__(rpc_url="https://base-rpc.example", timeout_seconds=1)
            self.calls: list[str] = []

        def latest_block_number(self) -> int:
            self._rpc_call_count += 1
            self.calls.append("eth_blockNumber")
            return 130

        def _rpc(self, method: str, params: list[object]) -> object:
            self._rpc_call_count += 1
            self.calls.append(method)
            if method == "eth_chainId":
                return "0x2105"
            if method == "eth_getTransactionReceipt":
                return {
                    "status": "0x1",
                    "blockNumber": "0x7b",
                    "from": "0x2222222222222222222222222222222222222222",
                    "logs": [_transfer_log()],
                }
            raise AssertionError(f"unexpected rpc method: {method}")

    verifier = CountingVerifier()
    latest_block = verifier.latest_block_number()

    first = verifier.verify(tx_hash=_tx_hash("cost-one"), expected_amount_units=10_000_000, destination_wallet_address=BASE_WALLET, min_confirmations=3, latest_block_number=latest_block)
    second = verifier.verify(tx_hash=_tx_hash("cost-two"), expected_amount_units=10_000_000, destination_wallet_address=BASE_WALLET, min_confirmations=3, latest_block_number=latest_block)

    assert first.verification_status == "verified"
    assert second.verification_status == "verified"
    assert verifier.calls.count("eth_chainId") == 1
    assert verifier.calls.count("eth_blockNumber") == 1
    assert verifier.calls.count("eth_getTransactionReceipt") == 2


def test_wallet_and_ledger_are_business_owned_and_no_guest_access() -> None:
    client = _client()
    owner = _login(client, 900, "owner")
    _create_business(client, owner, "wallet")
    guest = _login(client, 901, "guest")

    wallet = client.get("/api/v1/business/credits/wallet", headers=_bearer(owner, "req_wallet"))
    ledger = client.get("/api/v1/business/credits/ledger", headers=_bearer(owner, "req_ledger"))
    guest_wallet = client.get("/api/v1/business/credits/wallet", headers=_bearer(guest, "req_guest_wallet"))

    assert wallet.status_code == 200, wallet.text
    assert wallet.json()["data"]["wallet"]["available_credits"] == 0
    assert ledger.status_code == 200, ledger.text
    assert ledger.json()["data"]["items"] == []
    assert guest_wallet.status_code in {403, 404}
    assert "storage_path" not in wallet.text + ledger.text


def test_stripe_redirect_does_not_credit_and_signed_webhook_credits_once() -> None:
    client = _client()
    owner = _login(client, 910, "stripe")
    business = _create_business(client, owner, "stripe")

    no_key = client.post(
        "/api/v1/business/credits/stripe-checkout",
        headers={**_bearer(owner, "req_no_idem_stripe"), "Content-Type": "application/json"},
        json={"package_code": "starter"},
    )
    checkout = _checkout(client, owner, key="stripe_checkout")
    purchase = checkout["purchase"]
    wallet_after_redirect = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after_redirect.available_credits == 0
    assert purchase["status"] == "pending_payment"
    assert "redirect no acredita" in checkout["disclaimer"]

    raw = _stripe_completed_event(purchase["id"] and client.app.state.credit_repository.get_purchase(purchase["id"]).stripe_checkout_session_id)
    signed = client.post("/api/v1/webhooks/stripe", headers={"Stripe-Signature": _stripe_signature(raw), "X-Request-Id": "req_stripe_webhook"}, content=raw)
    duplicate = client.post("/api/v1/webhooks/stripe", headers={"Stripe-Signature": _stripe_signature(raw), "X-Request-Id": "req_stripe_dup"}, content=raw)
    invalid = client.post("/api/v1/webhooks/stripe", headers={"Stripe-Signature": "t=1,v1=bad", "X-Request-Id": "req_stripe_bad"}, content=raw)

    assert no_key.status_code == 400
    assert no_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert signed.status_code == 200, signed.text
    assert signed.json()["data"]["credited"] is True
    assert duplicate.status_code == 200
    assert duplicate.json()["data"]["duplicate"] is True
    assert duplicate.json()["data"]["credited"] is False
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "STRIPE_SIGNATURE_INVALID"
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet.available_credits == 5
    purchases = [item for item in client.app.state.ad_repository.ledger.values() if item.type == "purchase" and item.related_credit_purchase_id == purchase["id"]]
    assert len(purchases) == 1
    assert {"stripe_checkout_started", "stripe_payment_succeeded", "credits_added"}.issubset(set(_event_types(client)))


def test_legacy_credit_payment_methods_can_be_disabled() -> None:
    client = _client(LEGACY_CREDIT_PAYMENT_METHODS_ENABLED="0")
    owner = _login(client, 915, "legacy_disabled")
    _create_business(client, owner, "legacy_disabled")

    stripe = client.post(
        "/api/v1/business/credits/stripe-checkout",
        headers={**_headers(owner, "legacy_disabled_stripe"), "Content-Type": "application/json"},
        json={"package_code": "starter"},
    )
    manual = client.post(
        "/api/v1/business/credits/manual-payment",
        headers=_headers(owner, "legacy_disabled_manual"),
        data={"package_code": "starter", "payment_method": "zelle_manual_admin_approved", "manual_payment_reference": "ZELLE-LEGACY"},
        files={"file": ("proof.pdf", VALID_PDF, "application/pdf")},
    )

    assert stripe.status_code == 410
    assert stripe.json()["error"]["code"] == "CREDIT_PAYMENT_METHOD_DISABLED"
    assert manual.status_code == 410
    assert manual.json()["error"]["code"] == "CREDIT_PAYMENT_METHOD_DISABLED"


def test_manual_payment_submit_pending_admin_approve_once_and_reject_never_credits() -> None:
    client = _client()
    owner = _login(client, 920, "manual")
    business = _create_business(client, owner, "manual")
    admin = _login(client, 921, "admin")
    support = _login(client, 922, "support")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")

    no_key_manual = client.post(
        "/api/v1/business/credits/manual-payment",
        headers=_bearer(owner, "req_no_idem_manual"),
        data={"package_code": "starter", "payment_method": "zelle_manual_admin_approved", "manual_payment_reference": "ZELLE-NOKEY"},
        files={"file": ("proof.pdf", VALID_PDF, "application/pdf")},
    )
    manual = _manual_payment(client, owner, key="manual_ok")
    assert no_key_manual.status_code == 400
    assert no_key_manual.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert manual["purchase"]["status"] == "pending_manual_review"
    assert manual["proof"]["file_type"] == "credit_purchase_proof"
    assert "storage_path" not in json.dumps(manual)
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 0

    missing_reason = client.post(
        f"/api/v1/admin/credit-purchases/{manual['purchase']['id']}/approve",
        headers={**_headers(admin, "approve_missing"), "Content-Type": "application/json"},
        json={},
    )
    support_approve = client.post(
        f"/api/v1/admin/credit-purchases/{manual['purchase']['id']}/approve",
        headers={**_headers(support, "support_approve"), "Content-Type": "application/json"},
        json={"reason": "Comprobante valido"},
    )
    approved = client.post(
        f"/api/v1/admin/credit-purchases/{manual['purchase']['id']}/approve",
        headers={**_headers(admin, "approve_once"), "Content-Type": "application/json"},
        json={"reason": "Comprobante valido"},
    )
    replay = client.post(
        f"/api/v1/admin/credit-purchases/{manual['purchase']['id']}/approve",
        headers={**_headers(admin, "approve_once"), "Content-Type": "application/json"},
        json={"reason": "Comprobante valido"},
    )

    assert missing_reason.status_code == 422
    assert support_approve.status_code == 403
    assert approved.status_code == 200, approved.text
    assert replay.status_code == 200
    assert approved.json()["data"]["purchase"]["status"] == "approved"
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 5
    purchase_ledgers = [item for item in client.app.state.ad_repository.ledger.values() if item.related_credit_purchase_id == manual["purchase"]["id"] and item.type == "purchase"]
    assert len(purchase_ledgers) == 1

    owner_reject = _login(client, 923, "reject_owner")
    reject_business = _create_business(client, owner_reject, "manual_reject")
    rejected_manual = _manual_payment(client, owner_reject, key="manual_reject")
    rejected = client.post(
        f"/api/v1/admin/credit-purchases/{rejected_manual['purchase']['id']}/reject",
        headers={**_headers(admin, "reject_once"), "Content-Type": "application/json"},
        json={"reason": "Referencia no coincide"},
    )
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["data"]["purchase"]["status"] == "rejected"
    assert client.app.state.ad_repository.get_wallet(reject_business["id"]).available_credits == 0
    assert {"manual_credit_payment_submitted", "manual_credit_payment_approved", "manual_credit_payment_rejected"}.issubset(set(_event_types(client)))


def test_manual_payment_rejects_disguised_files_without_side_effects() -> None:
    client = _client()
    owner = _login(client, 924, "manual_upload_hardening")
    _create_business(client, owner, "manual_upload_hardening")
    baseline = {
        "purchases": len(client.app.state.credit_repository.purchases),
        "files": len(client.app.state.credit_repository.files),
        "storage": len(client.app.state.private_storage._objects),
        "audit": len(client.app.state.audit_writer.events),
    }
    cases = [
        ("html-as-jpg", "proof.jpg", b"<html><script>alert(1)</script></html>", "image/jpeg"),
        ("html-as-pdf", "proof.pdf", b"<html>not a pdf</html>", "application/pdf"),
        ("pdf-as-jpg", "proof.jpg", b"%PDF-1.7\n%%EOF\n", "image/jpeg"),
        ("arbitrary-pdf", "proof.pdf", b"not-a-document", "application/pdf"),
        ("corrupt-png", "proof.png", b"\x89PNG\r\n\x1a\ncorrupt", "image/png"),
        ("oversize", "proof.pdf", b"x" * (5 * 1024 * 1024 + 1), "application/pdf"),
    ]

    for key, file_name, content, mime_type in cases:
        response = client.post(
            "/api/v1/business/credits/manual-payment",
            headers=_headers(owner, key),
            data={
                "package_code": "starter",
                "payment_method": "zelle_manual_admin_approved",
                "manual_payment_reference": "ZELLE-HARDENING",
            },
            files={"file": (file_name, content, mime_type)},
        )

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "MANUAL_PAYMENT_PROOF_REQUIRED"
        assert "storage_path" not in response.text

    assert len(client.app.state.credit_repository.purchases) == baseline["purchases"]
    assert len(client.app.state.credit_repository.files) == baseline["files"]
    assert len(client.app.state.private_storage._objects) == baseline["storage"]
    assert len(client.app.state.audit_writer.events) == baseline["audit"]


def test_manual_payment_accepts_allowed_content_and_uses_canonical_metadata() -> None:
    client = _client()
    owner = _login(client, 925, "manual_upload_formats")
    _create_business(client, owner, "manual_upload_formats")
    cases = (
        ("jpeg", _image_bytes("JPEG"), "image/jpeg", ".jpg"),
        ("png", _image_bytes("PNG"), "image/png", ".png"),
        ("webp", _image_bytes("WEBP"), "image/webp", ".webp"),
        ("pdf", VALID_PDF, "application/pdf", ".pdf"),
    )

    for label, content, mime_type, expected_suffix in cases:
        response = client.post(
            "/api/v1/business/credits/manual-payment",
            headers=_headers(owner, f"manual_valid_{label}"),
            data={
                "package_code": "starter",
                "payment_method": "zelle_manual_admin_approved",
                "manual_payment_reference": f"ZELLE-{label.upper()}",
            },
            files={"file": ("untrusted-name.bin", content, mime_type)},
        )

        assert response.status_code == 201, response.text
        payload = response.json()["data"]
        assert payload["proof"]["mime_type"] == mime_type
        assert "storage_path" not in response.text
        stored_file = client.app.state.credit_repository.files[payload["proof"]["id"]]
        assert stored_file.storage_path.endswith(expected_suffix)

def test_admin_adjustment_requires_admin_and_keeps_wallet_non_negative() -> None:
    client = _client()
    owner = _login(client, 930, "adjust_owner")
    business = _create_business(client, owner, "adjust")
    admin = _login(client, 931, "adjust_admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "super_admin")

    no_key = client.post(
        "/api/v1/admin/credits/adjust",
        headers={**_bearer(admin, "req_no_idem_adjust"), "Content-Type": "application/json"},
        json={"business_id": business["id"], "amount": 1, "direction": "add", "reason": "owner_test_adjustment"},
    )
    add = client.post(
        "/api/v1/admin/credits/adjust",
        headers={**_headers(admin, "adjust_add"), "Content-Type": "application/json"},
        json={"business_id": business["id"], "amount": 3, "direction": "add", "reason": "owner_test_adjustment"},
    )
    remove_too_much = client.post(
        "/api/v1/admin/credits/adjust",
        headers={**_headers(admin, "adjust_remove"), "Content-Type": "application/json"},
        json={"business_id": business["id"], "amount": 4, "direction": "remove", "reason": "owner_test_adjustment"},
    )

    assert no_key.status_code == 400
    assert no_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert add.status_code == 200, add.text
    assert add.json()["data"]["ledger"]["type"] == "admin_adjustment"
    assert remove_too_much.status_code == 409
    assert remove_too_much.json()["error"]["code"] == "CREDIT_BALANCE_INSUFFICIENT"
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 3


def test_referral_approval_awards_once_and_later_purchase_does_not_duplicate_bonus() -> None:
    client = _client()
    referrer_login = _login(client, 940, "referrer")
    referred_login = _login(client, 941, "referred")
    referrer_business = _create_business(client, referrer_login, "referrer")
    referred_business = _create_business(client, referred_login, "referred")

    referrer_data = client.get("/api/v1/business/referrals", headers=_bearer(referrer_login, "req_referrer")).json()["data"]
    no_key_apply = client.post(
        "/api/v1/business/referrals/apply",
        headers={**_bearer(referred_login, "req_no_idem_referral"), "Content-Type": "application/json"},
        json={"referral_code": referrer_data["referral_code"]},
    )
    self_referral = client.post(
        "/api/v1/business/referrals/apply",
        headers={**_headers(referrer_login, "self_ref"), "Content-Type": "application/json"},
        json={"referral_code": referrer_data["referral_code"]},
    )
    late_apply = client.post(
        "/api/v1/business/referrals/apply",
        headers={**_headers(referred_login, "apply_ref"), "Content-Type": "application/json"},
        json={"referral_code": referrer_data["referral_code"]},
    )
    awarded = client.app.state.credit_repository.award_referral_on_business_approval(
        referred_business_id=referred_business["id"],
        referral_code=referrer_data["referral_code"],
        actor_user_id=referrer_login["user"]["id"],
    )
    replay = client.app.state.credit_repository.award_referral_on_business_approval(
        referred_business_id=referred_business["id"],
        referral_code=referrer_data["referral_code"],
        actor_user_id=referrer_login["user"]["id"],
    )
    checkout = _checkout(client, referred_login, key="referred_stripe")
    session_id = client.app.state.credit_repository.get_purchase(checkout["purchase"]["id"]).stripe_checkout_session_id
    raw = _stripe_completed_event(session_id, event_id="evt_referral")
    credited = client.post("/api/v1/webhooks/stripe", headers={"Stripe-Signature": _stripe_signature(raw), "X-Request-Id": "req_referral_webhook"}, content=raw)
    duplicate_event = client.post("/api/v1/webhooks/stripe", headers={"Stripe-Signature": _stripe_signature(raw), "X-Request-Id": "req_referral_webhook_dup"}, content=raw)

    assert no_key_apply.status_code == 400
    assert no_key_apply.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert self_referral.status_code == 409
    assert self_referral.json()["error"]["code"] == "REFERRAL_NOT_ALLOWED"
    assert late_apply.status_code == 409
    assert late_apply.json()["error"]["code"] == "REFERRAL_NOT_ALLOWED"
    assert awarded.created is True
    assert awarded.event is not None and awarded.event.credits_awarded == 5
    assert replay.created is False
    assert credited.status_code == 200, credited.text
    assert duplicate_event.status_code == 200
    assert client.app.state.ad_repository.get_wallet(referred_business["id"]).available_credits == 5
    assert client.app.state.ad_repository.get_wallet(referrer_business["id"]).available_credits == 5
    referral_ledgers = [item for item in client.app.state.ad_repository.ledger.values() if item.business_id == referrer_business["id"] and item.type == "referral_bonus"]
    assert len(referral_ledgers) == 1


def test_referral_approval_finalizes_legacy_pending_event_once() -> None:
    client = _client()
    referrer_login = _login(client, 946, "legacy_pending_referrer")
    referred_login = _login(client, 947, "legacy_pending_referred")
    referrer_business = _create_business(client, referrer_login, "legacy_pending_referrer")
    referred_business = _create_business(client, referred_login, "legacy_pending_referred")
    repository = client.app.state.credit_repository
    code = repository.get_or_create_referral_code(referrer_business["id"])
    pending = repository.apply_referral_code(
        referred_business_id=referred_business["id"],
        referral_code=code.code,
    )
    referred = client.app.state.business_repository.get_business(referred_business["id"])
    referred.verification_status = "pending"
    referred.approved_at = None

    awarded = repository.award_referral_on_business_approval(
        referred_business_id=referred_business["id"],
        referral_code=code.code,
        actor_user_id=referrer_login["user"]["id"],
    )
    replay = repository.award_referral_on_business_approval(
        referred_business_id=referred_business["id"],
        referral_code=code.code,
        actor_user_id=referrer_login["user"]["id"],
    )

    assert awarded.event is pending
    assert awarded.event.status == "rewarded"
    assert awarded.event.credits_awarded == 5
    assert awarded.created is False
    assert awarded.event_changed is True
    assert replay.outcome == "already_processed"
    assert replay.event_changed is False
    assert client.app.state.ad_repository.get_wallet(referrer_business["id"]).available_credits == 5
    referral_ledgers = [
        item
        for item in client.app.state.ad_repository.ledger.values()
        if item.business_id == referrer_business["id"] and item.type == "referral_bonus"
    ]
    assert len(referral_ledgers) == 1


def test_legacy_pending_referral_respects_partial_cap_and_rejected_replay() -> None:
    client = _client()
    referrer_login = _login(client, 948, "legacy_cap_referrer")
    partial_login = _login(client, 949, "legacy_cap_partial")
    capped_login = _login(client, 950, "legacy_cap_rejected")
    referrer_business = _create_business(client, referrer_login, "legacy_cap_referrer")
    partial_business = _create_business(client, partial_login, "legacy_cap_partial")
    capped_business = _create_business(client, capped_login, "legacy_cap_rejected")
    repository = client.app.state.credit_repository
    referrer = client.app.state.business_repository.get_business(referrer_business["id"])
    referrer.referral_credits_earned = 18
    code = repository.get_or_create_referral_code(referrer_business["id"])

    partial_event = repository.apply_referral_code(
        referred_business_id=partial_business["id"],
        referral_code=code.code,
    )
    partial = client.app.state.business_repository.get_business(partial_business["id"])
    partial.verification_status = "pending"
    partial.approved_at = None
    partial_result = repository.award_referral_on_business_approval(
        referred_business_id=partial_business["id"],
        referral_code=code.code,
        actor_user_id=referrer_login["user"]["id"],
    )

    capped_event = repository.apply_referral_code(
        referred_business_id=capped_business["id"],
        referral_code=code.code,
    )
    capped = client.app.state.business_repository.get_business(capped_business["id"])
    capped.verification_status = "pending"
    capped.approved_at = None
    capped_result = repository.award_referral_on_business_approval(
        referred_business_id=capped_business["id"],
        referral_code=code.code,
        actor_user_id=referrer_login["user"]["id"],
    )
    capped_replay = repository.award_referral_on_business_approval(
        referred_business_id=capped_business["id"],
        referral_code=code.code,
        actor_user_id=referrer_login["user"]["id"],
    )

    assert partial_result.event is partial_event
    assert partial_event.status == "rewarded"
    assert partial_event.credits_awarded == 2
    assert capped_result.event is capped_event
    assert capped_event.status == "rejected"
    assert capped_event.reject_reason == "referral_cap_reached"
    assert capped_replay.outcome == "already_processed"
    assert capped_replay.event_changed is False
    assert referrer.referral_credits_earned == 20
    assert client.app.state.ad_repository.get_wallet(referrer_business["id"]).available_credits == 2
    referral_ledgers = [
        item
        for item in client.app.state.ad_repository.ledger.values()
        if item.business_id == referrer_business["id"] and item.type == "referral_bonus"
    ]
    assert len(referral_ledgers) == 1
    assert referral_ledgers[0].amount == 2


def test_referral_approval_respects_partial_and_total_cap() -> None:
    client = _client()
    referrer_login = _login(client, 942, "referrer_cap")
    first_referred_login = _login(client, 943, "referred_cap_partial")
    second_referred_login = _login(client, 944, "referred_cap_full")
    referrer_business = _create_business(client, referrer_login, "referrer_cap")
    first_referred = _create_business(client, first_referred_login, "referred_cap_partial")
    second_referred = _create_business(client, second_referred_login, "referred_cap_full")
    referrer = client.app.state.business_repository.get_business(referrer_business["id"])
    referrer.referral_credits_earned = 18
    referral = client.app.state.credit_repository.get_or_create_referral_code(referrer.id)

    partial = client.app.state.credit_repository.award_referral_on_business_approval(
        referred_business_id=first_referred["id"],
        referral_code=f" {referral.code.lower()} ",
        actor_user_id=referrer_login["user"]["id"],
    )
    capped = client.app.state.credit_repository.award_referral_on_business_approval(
        referred_business_id=second_referred["id"],
        referral_code=referral.code,
        actor_user_id=referrer_login["user"]["id"],
    )

    assert partial.event is not None
    assert partial.event.status == "rewarded"
    assert partial.event.credits_awarded == 2
    assert capped.event is not None
    assert capped.event.status == "rejected"
    assert capped.event.reject_reason == "referral_cap_reached"
    assert referrer.referral_credits_earned == 20
    assert client.app.state.credit_repository.get_wallet(referrer.id).available_credits == 2
    referral_ledgers = [
        item
        for item in client.app.state.ad_repository.ledger.values()
        if item.business_id == referrer.id and item.type == "referral_bonus"
    ]
    assert len(referral_ledgers) == 1
    assert referral_ledgers[0].amount == 2


def test_referral_approval_rejects_self_referral_without_credit() -> None:
    client = _client()
    owner = _login(client, 945, "referral_self_owner")
    business = _create_business(client, owner, "referral_self_owner")
    code = client.app.state.credit_repository.get_or_create_referral_code(business["id"])

    result = client.app.state.credit_repository.award_referral_on_business_approval(
        referred_business_id=business["id"],
        referral_code=code.code.lower(),
        actor_user_id=owner["user"]["id"],
    )

    assert result.outcome == "self_referral"
    assert result.event is None
    assert client.app.state.credit_repository.get_wallet(business["id"]) is None
    assert client.app.state.credit_repository.referral_events == {}


def test_base_usdc_payment_create_does_not_credit_and_valid_tx_credits_once() -> None:
    client = _client()
    owner = _login(client, 970, "base_owner")
    business = _create_business(client, owner, "base_owner")

    payment = _base_payment(client, owner, key="base_create")
    purchase = payment["purchase"]
    assert purchase["status"] == "pending_payment"
    assert purchase["chain_id"] == 8453
    assert purchase["token_contract_address"] == BASE_USDC
    assert purchase["expected_amount_units"] == "10000000"
    assert payment["payment"]["network"] == "base_mainnet"
    assert payment["payment"]["chain_id"] == 8453
    assert payment["payment"]["token_symbol"] == "USDC"
    assert payment["payment"]["token_contract_address"] == BASE_USDC
    assert payment["payment"]["destination_wallet_address"] == BASE_WALLET
    assert payment["payment"]["expected_amount_units"] == "10000000"
    assert payment["payment"]["expected_amount_display"] == "10.00"
    assert payment["payment"]["min_confirmations"] == 3
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 0

    tx_hash = _tx_hash("valid-onchain")
    client.app.state.onchain_credit_verifier.set_result(tx_hash, _verification(tx_hash))
    submitted = client.post(
        f"/api/v1/business/credits/purchases/{purchase['id']}/tx-hash",
        headers={**_headers(owner, "base_tx"), "Content-Type": "application/json"},
        json={"tx_hash": tx_hash},
    )
    replay = client.post(
        f"/api/v1/business/credits/purchases/{purchase['id']}/tx-hash",
        headers={**_headers(owner, "base_tx"), "Content-Type": "application/json"},
        json={"tx_hash": tx_hash},
    )

    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["data"]["credited"] is True
    assert submitted.json()["data"]["purchase"]["status"] == "credited"
    assert submitted.json()["data"]["purchase"]["tx_hash_masked"].endswith(tx_hash[-8:])
    assert tx_hash not in submitted.text
    assert replay.status_code == 200
    assert replay.json()["data"]["credited"] is True
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 5
    purchase_ledgers = [item for item in client.app.state.ad_repository.ledger.values() if item.type == "purchase" and item.related_credit_purchase_id == purchase["id"]]
    assert len(purchase_ledgers) == 1
    assert purchase_ledgers[0].reason == "base_usdc_onchain_verified"
    assert "storage_path" not in submitted.text
    assert "account_value" not in submitted.text
    audit_json = json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert tx_hash not in audit_json
    assert "tx_hash_masked" in audit_json

    overpay = _base_payment(client, owner, key="base_overpay")
    overpay_hash = _tx_hash("valid-overpay")
    client.app.state.onchain_credit_verifier.set_result(overpay_hash, _verification(overpay_hash, amount_units=15_000_000, log_index=2))
    overpay_response = client.post(
        f"/api/v1/business/credits/purchases/{overpay['purchase']['id']}/tx-hash",
        headers={**_headers(owner, "base_overpay_tx"), "Content-Type": "application/json"},
        json={"tx_hash": overpay_hash},
    )
    assert overpay_response.status_code == 200, overpay_response.text
    assert overpay_response.json()["data"]["purchase"]["status"] == "credited"
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 10


def test_base_usdc_payment_requires_configured_receiving_wallet() -> None:
    client = _client(NODO_CREDIT_RECEIVING_WALLET_BASE="")
    owner = _login(client, 976, "base_missing_wallet")
    _create_business(client, owner, "base_missing_wallet")

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "base_missing_wallet"), "Content-Type": "application/json"},
        json={"package_code": "starter"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ONCHAIN_RECEIVING_WALLET_NOT_CONFIGURED"
    assert response.json()["error"]["message"] == "La wallet de recepcion BASE no esta configurada correctamente."
    assert client.app.state.credit_repository.purchases == {}
    assert "onchain_receiving_wallet_configuration_invalid" in _event_types(client)


def test_base_usdc_payment_rejects_invalid_receiving_wallet_without_credit() -> None:
    client = _client(NODO_CREDIT_RECEIVING_WALLET_BASE="not-an-evm-address")
    owner = _login(client, 980, "base_invalid_wallet")
    business = _create_business(client, owner, "base_invalid_wallet")

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "base_invalid_wallet"), "Content-Type": "application/json"},
        json={"package_code": "starter"},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "ONCHAIN_RECEIVING_WALLET_NOT_CONFIGURED"
    assert client.app.state.credit_repository.purchases == {}
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet is None or wallet.available_credits == 0
    events = [event for event in client.app.state.audit_writer.events if event.event_type == "onchain_receiving_wallet_configuration_invalid"]
    assert len(events) == 1
    assert events[0].metadata_json == {"code": "ONCHAIN_RECEIVING_WALLET_NOT_CONFIGURED"}


def test_base_usdc_payment_rejects_client_supplied_destination_wallet() -> None:
    client = _client()
    owner = _login(client, 985, "base_client_wallet_override")
    _create_business(client, owner, "base_client_wallet_override")

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "base_client_wallet_override"), "Content-Type": "application/json"},
        json={
            "package_code": "starter",
            "token_symbol": "USDC",
            "destination_wallet_address": "0x4444444444444444444444444444444444444444",
        },
    )

    assert response.status_code == 422
    assert client.app.state.credit_repository.purchases == {}


def test_base_usdc_wrong_chain_token_wallet_partial_and_pending_confirmations() -> None:
    client = _client()
    owner = _login(client, 971, "base_failures")
    _create_business(client, owner, "base_failures")

    cases = [
        ("wrong_chain", _verification(_tx_hash("wrong_chain"), chain_id=1, error_code="ONCHAIN_WRONG_CHAIN"), 409, "ONCHAIN_WRONG_CHAIN"),
        ("wrong_token", _verification(_tx_hash("wrong_token"), token="0x3333333333333333333333333333333333333333", error_code="ONCHAIN_WRONG_TOKEN_OR_WALLET"), 409, "ONCHAIN_WRONG_TOKEN_OR_WALLET"),
        ("wrong_wallet", _verification(_tx_hash("wrong_wallet"), to_address="0x4444444444444444444444444444444444444444", error_code="ONCHAIN_WRONG_TOKEN_OR_WALLET"), 409, "ONCHAIN_WRONG_TOKEN_OR_WALLET"),
    ]
    for suffix, result, status_code, code in cases:
        payment = _base_payment(client, owner, key=f"base_{suffix}")
        client.app.state.onchain_credit_verifier.set_result(result.tx_hash, result)
        response = client.post(
            f"/api/v1/business/credits/purchases/{payment['purchase']['id']}/tx-hash",
            headers={**_headers(owner, f"tx_{suffix}"), "Content-Type": "application/json"},
            json={"tx_hash": result.tx_hash},
        )
        assert response.status_code == status_code, response.text
        assert response.json()["error"]["code"] == code

    partial = _base_payment(client, owner, key="base_partial")
    partial_hash = _tx_hash("partial")
    client.app.state.onchain_credit_verifier.set_result(partial_hash, _verification(partial_hash, amount_units=5_000_000, status="under_review"))
    partial_response = client.post(
        f"/api/v1/business/credits/purchases/{partial['purchase']['id']}/tx-hash",
        headers={**_headers(owner, "tx_partial"), "Content-Type": "application/json"},
        json={"tx_hash": partial_hash},
    )
    assert partial_response.status_code == 200, partial_response.text
    assert partial_response.json()["data"]["purchase"]["status"] == "under_review"

    pending = _base_payment(client, owner, key="base_pending_confirmations")
    pending_hash = _tx_hash("pending_confirmations")
    client.app.state.onchain_credit_verifier.set_result(pending_hash, _verification(pending_hash, confirmations=1, status="pending_onchain_confirmation"))
    pending_response = client.post(
        f"/api/v1/business/credits/purchases/{pending['purchase']['id']}/tx-hash",
        headers={**_headers(owner, "tx_pending_confirmations"), "Content-Type": "application/json"},
        json={"tx_hash": pending_hash},
    )
    assert pending_response.status_code == 200, pending_response.text
    assert pending_response.json()["data"]["purchase"]["status"] == "pending_onchain_confirmation"


def test_base_usdc_defense_in_depth_rejects_untrusted_verified_result_fields() -> None:
    client = _client()
    owner = _login(client, 982, "base_verified_result_guard")
    business = _create_business(client, owner, "base_verified_result_guard")
    cases = (
        ("chain", {"chain_id": 1}, "ONCHAIN_WRONG_CHAIN"),
        ("token", {"token": "0x3333333333333333333333333333333333333333"}, "ONCHAIN_WRONG_TOKEN_OR_WALLET"),
        ("wallet", {"to_address": "0x4444444444444444444444444444444444444444"}, "ONCHAIN_WRONG_TOKEN_OR_WALLET"),
        ("amount", {"amount_units": 1}, "ONCHAIN_VERIFICATION_FAILED"),
        ("confirmations", {"confirmations": 0}, "ONCHAIN_VERIFICATION_FAILED"),
    )

    for suffix, overrides, expected_code in cases:
        payment = _base_payment(client, owner, key=f"guard_{suffix}")
        tx_hash = _tx_hash(f"guard-{suffix}")
        result = _verification(tx_hash, **overrides)
        client.app.state.onchain_credit_verifier.set_result(tx_hash, result)
        response = client.post(
            f"/api/v1/business/credits/purchases/{payment['purchase']['id']}/tx-hash",
            headers={**_headers(owner, f"guard_tx_{suffix}"), "Content-Type": "application/json"},
            json={"tx_hash": tx_hash},
        )

        assert response.status_code == 409, response.text
        assert response.json()["error"]["code"] == expected_code
        assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 0


def test_base_usdc_expired_purchase_and_unavailable_verifier_never_credit() -> None:
    client = _client()
    owner = _login(client, 983, "base_expiry_rpc_guard")
    business = _create_business(client, owner, "base_expiry_rpc_guard")

    expired = _base_payment(client, owner, key="expired_guard")
    expired_record = client.app.state.credit_repository.get_purchase(expired["purchase"]["id"])
    expired_record.expires_at = utc_now() - timedelta(seconds=1)
    expired_hash = _tx_hash("expired-guard")
    client.app.state.onchain_credit_verifier.set_result(expired_hash, _verification(expired_hash))
    expired_response = client.post(
        f"/api/v1/business/credits/purchases/{expired_record.id}/tx-hash",
        headers={**_headers(owner, "expired_guard_tx"), "Content-Type": "application/json"},
        json={"tx_hash": expired_hash},
    )

    class UnavailableVerifier:
        def verify(self, **kwargs):  # type: ignore[no-untyped-def]
            raise ApiError("ONCHAIN_RPC_UNAVAILABLE", status_code=503)

    unavailable = _base_payment(client, owner, key="rpc_unavailable_guard")
    unavailable_hash = _tx_hash("rpc-unavailable-guard")
    client.app.state.onchain_credit_verifier = UnavailableVerifier()
    unavailable_response = client.post(
        f"/api/v1/business/credits/purchases/{unavailable['purchase']['id']}/tx-hash",
        headers={**_headers(owner, "rpc_unavailable_guard_tx"), "Content-Type": "application/json"},
        json={"tx_hash": unavailable_hash},
    )

    assert expired_response.status_code == 200, expired_response.text
    assert expired_response.json()["data"]["credited"] is False
    assert expired_response.json()["data"]["purchase"]["status"] == "under_review"
    assert unavailable_response.status_code == 503
    assert unavailable_response.json()["error"]["code"] == "ONCHAIN_RPC_UNAVAILABLE"
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 0
    audit_json = json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert expired_hash not in audit_json
    assert unavailable_hash not in audit_json
    assert "onchain_payment_verification_failed" in _event_types(client)


def test_base_usdc_different_idempotency_key_after_credit_does_not_repeat_effects() -> None:
    client = _client()
    owner = _login(client, 984, "base_replay_guard")
    business = _create_business(client, owner, "base_replay_guard")
    payment = _base_payment(client, owner, key="base_replay_guard")
    tx_hash = _tx_hash("base-replay-guard")
    client.app.state.onchain_credit_verifier.set_result(tx_hash, _verification(tx_hash, log_index=41))

    first = client.post(
        f"/api/v1/business/credits/purchases/{payment['purchase']['id']}/tx-hash",
        headers={**_headers(owner, "base_replay_guard_first"), "Content-Type": "application/json"},
        json={"tx_hash": tx_hash},
    )
    audit_count = len(client.app.state.audit_writer.events)
    verifier_calls = len(client.app.state.onchain_credit_verifier.calls)
    second = client.post(
        f"/api/v1/business/credits/purchases/{payment['purchase']['id']}/tx-hash",
        headers={**_headers(owner, "base_replay_guard_second"), "Content-Type": "application/json"},
        json={"tx_hash": tx_hash},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["data"]["credited"] is False
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 5
    assert len(client.app.state.onchain_credit_verifier.calls) == verifier_calls
    assert len(client.app.state.audit_writer.events) == audit_count
    ledgers = [item for item in client.app.state.ad_repository.ledger.values() if item.related_credit_purchase_id == payment["purchase"]["id"] and item.type == "purchase"]
    assert len(ledgers) == 1


def test_credit_wallet_configuration_is_backend_only_and_has_no_signing_material() -> None:
    frontend = "\n".join(path.read_text(encoding="utf-8") for path in Path("apps/web/src").rglob("*.*") if path.suffix in {".ts", ".tsx"})
    credit_runtime = "\n".join(path.read_text(encoding="utf-8") for path in Path("apps/api/app/modules/credits").glob("*.py"))
    env_examples = "\n".join(Path(name).read_text(encoding="utf-8") for name in (".env.example", ".env.local.example", ".env.staging.example"))

    assert "NEXT_PUBLIC_NODO_CREDIT_RECEIVING_WALLET_BASE" not in frontend
    assert "NODO_CREDIT_RECEIVING_WALLET_BASE" not in frontend
    for forbidden in ("PRIVATE_KEY", "MNEMONIC", "SEED_PHRASE", "SIGNING_KEY"):
        assert forbidden not in frontend
        assert forbidden not in credit_runtime
        assert forbidden not in env_examples


def test_base_usdc_pending_tx_is_credited_later_by_watcher() -> None:
    client = _client()
    owner = _login(client, 981, "base_pending_then_auto_credit")
    business = _create_business(client, owner, "base_pending_then_auto_credit")

    payment = _base_payment(client, owner, key="base_pending_then_auto_credit")
    purchase_id = payment["purchase"]["id"]
    tx_hash = _tx_hash("pending-then-auto-credit")
    client.app.state.onchain_credit_verifier.set_result(
        tx_hash,
        _verification(tx_hash, confirmations=1, status="pending_onchain_confirmation", log_index=31),
    )
    submitted = client.post(
        f"/api/v1/business/credits/purchases/{purchase_id}/tx-hash",
        headers={**_headers(owner, "base_pending_submit"), "Content-Type": "application/json"},
        json={"tx_hash": tx_hash},
    )

    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["data"]["credited"] is False
    assert submitted.json()["data"]["purchase"]["status"] == "pending_onchain_confirmation"
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 0

    client.app.state.onchain_credit_verifier.set_result(
        tx_hash,
        _verification(tx_hash, confirmations=6, status="verified", log_index=31),
    )
    watcher_result = client.app.state.verify_base_usdc_credit_purchases_worker.run_once(request_id="req_auto_credit_later")

    assert watcher_result["credited"] == 1
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 5
    purchase = client.app.state.credit_repository.get_purchase(purchase_id)
    assert purchase.status == "credited"
    purchase_ledgers = [
        item
        for item in client.app.state.ad_repository.ledger.values()
        if item.type == "purchase" and item.related_credit_purchase_id == purchase_id
    ]
    assert len(purchase_ledgers) == 1


def test_base_usdc_watcher_moves_expired_verified_payment_to_review_without_credit() -> None:
    client = _client()
    owner = _login(client, 986, "base_watcher_expiry_guard")
    business = _create_business(client, owner, "base_watcher_expiry_guard")
    payment = _base_payment(client, owner, key="base_watcher_expiry_guard")
    purchase = client.app.state.credit_repository.get_purchase(payment["purchase"]["id"])
    purchase.expires_at = utc_now() - timedelta(seconds=1)
    tx_hash = _tx_hash("base-watcher-expiry-guard")
    purchase.tx_hash = tx_hash
    client.app.state.onchain_credit_verifier.set_result(tx_hash, _verification(tx_hash, log_index=42))

    result = client.app.state.verify_base_usdc_credit_purchases_worker.run_once(request_id="req_watcher_expiry_guard")

    assert result["credited"] == 0
    assert result["under_review"] == 1
    assert client.app.state.credit_repository.get_purchase(purchase.id).status == "under_review"
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 0
    ledgers = [item for item in client.app.state.ad_repository.ledger.values() if item.related_credit_purchase_id == purchase.id and item.type == "purchase"]
    assert ledgers == []


def test_admin_detail_and_reject_onchain_under_review_requires_admin_reason() -> None:
    client = _client()
    owner = _login(client, 974, "base_admin_owner")
    _create_business(client, owner, "base_admin_owner")
    admin = _login(client, 975, "base_admin")
    support = _login(client, 976, "base_support")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")

    payment = _base_payment(client, owner, key="base_admin_review")
    tx_hash = _tx_hash("admin-under-review")
    client.app.state.onchain_credit_verifier.set_result(tx_hash, _verification(tx_hash, amount_units=5_000_000, status="under_review"))
    submitted = client.post(
        f"/api/v1/business/credits/purchases/{payment['purchase']['id']}/tx-hash",
        headers={**_headers(owner, "base_admin_review_tx"), "Content-Type": "application/json"},
        json={"tx_hash": tx_hash},
    )
    detail = client.get(f"/api/v1/admin/credit-purchases/{payment['purchase']['id']}", headers=_bearer(admin, "req_admin_purchase_detail"))
    missing_reason = client.post(
        f"/api/v1/admin/credit-purchases/{payment['purchase']['id']}/reject",
        headers={**_headers(admin, "base_admin_reject_missing"), "Content-Type": "application/json"},
        json={},
    )
    support_reject = client.post(
        f"/api/v1/admin/credit-purchases/{payment['purchase']['id']}/reject",
        headers={**_headers(support, "base_support_reject"), "Content-Type": "application/json"},
        json={"reason": "Pago parcial"},
    )
    rejected = client.post(
        f"/api/v1/admin/credit-purchases/{payment['purchase']['id']}/reject",
        headers={**_headers(admin, "base_admin_reject"), "Content-Type": "application/json"},
        json={"reason": "Pago parcial"},
    )

    assert submitted.status_code == 200, submitted.text
    assert detail.status_code == 200, detail.text
    assert detail.json()["data"]["purchase"]["status"] == "under_review"
    assert missing_reason.status_code == 422
    assert support_reject.status_code == 403
    assert rejected.status_code == 200, rejected.text
    assert rejected.json()["data"]["purchase"]["status"] == "rejected"
    assert "onchain_credit_purchase_rejected" in _event_types(client)


def test_admin_credit_purchase_list_is_lightweight_and_detail_reconciles_masked_onchain_credit() -> None:
    client = _client()
    owner = _login(client, 1991, "credit_reconciliation_owner")
    business = _create_business(client, owner, "credit_reconciliation_owner")
    admin = _login(client, 1992, "credit_reconciliation_admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    payment = _base_payment(client, owner, key="credit_reconciliation_purchase")
    purchase_id = payment["purchase"]["id"]
    tx_hash = _tx_hash("credit-reconciliation-valid")
    client.app.state.onchain_credit_verifier.set_result(tx_hash, _verification(tx_hash, log_index=52))
    submitted = client.post(
        f"/api/v1/business/credits/purchases/{purchase_id}/tx-hash",
        headers={**_headers(owner, "credit_reconciliation_submit"), "Content-Type": "application/json"},
        json={"tx_hash": tx_hash},
    )
    listed = client.get(
        "/api/v1/admin/credit-purchases?status=credited&limit=20",
        headers=_bearer(admin, "req_credit_reconciliation_list"),
    )
    detail = client.get(
        f"/api/v1/admin/credit-purchases/{purchase_id}",
        headers=_bearer(admin, "req_credit_reconciliation_detail"),
    )

    assert submitted.status_code == 200, submitted.text
    assert listed.status_code == 200, listed.text
    summary = next(item for item in listed.json()["data"]["items"] if item["id"] == purchase_id)
    assert set(summary) == {
        "id",
        "business_id",
        "package_code",
        "credits_amount",
        "price_usd",
        "payment_method",
        "status",
        "verification_status",
        "has_reported_tx",
        "created_at",
        "updated_at",
    }

    assert detail.status_code == 200, detail.text
    data = detail.json()["data"]
    assert data["purchase"]["id"] == purchase_id
    assert data["purchase"]["business_id"] == business["id"]
    assert data["ledger"]["reference_id"] == purchase_id
    assert data["ledger"]["balance_available_before"] == 0
    assert data["ledger"]["balance_available_after"] == 5
    assert data["reconciliation"] == {"state": "matched", "warning_codes": []}
    evidence = data["onchain_evidence"]
    assert evidence["tx_hash_masked"].endswith(tx_hash[-8:])
    assert "tx_hash" not in evidence
    assert "destination_wallet_address" not in evidence
    assert "tx_to_address" not in evidence
    serialized_detail = json.dumps(data)
    assert tx_hash not in serialized_detail
    assert BASE_WALLET not in serialized_detail


def test_admin_credit_purchase_detail_warns_when_credited_purchase_has_no_ledger() -> None:
    client = _client()
    owner = _login(client, 1993, "credit_missing_ledger_owner")
    _create_business(client, owner, "credit_missing_ledger_owner")
    admin = _login(client, 1994, "credit_missing_ledger_admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    payment = _base_payment(client, owner, key="credit_missing_ledger_purchase")
    purchase = client.app.state.credit_repository.get_purchase(payment["purchase"]["id"])
    purchase.status = "credited"
    purchase.credited_at = utc_now()

    detail = client.get(
        f"/api/v1/admin/credit-purchases/{purchase.id}",
        headers=_bearer(admin, "req_credit_missing_ledger_detail"),
    )

    assert detail.status_code == 200, detail.text
    data = detail.json()["data"]
    assert data["ledger"] is None
    assert data["reconciliation"] == {
        "state": "warning",
        "warning_codes": ["CREDITED_WITHOUT_LEDGER"],
    }


def test_admin_credit_purchase_detail_explains_non_terminal_onchain_states() -> None:
    client = _client()
    owner = _login(client, 1996, "credit_diagnostic_owner")
    _create_business(client, owner, "credit_diagnostic_owner")
    admin = _login(client, 1997, "credit_diagnostic_admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    expected = {
        "under_review": ("pending", ["PAYMENT_REQUIRES_REVIEW"]),
        "verification_failed": ("failed", ["ONCHAIN_VERIFICATION_FAILED"]),
        "expired": ("failed", ["CREDIT_PURCHASE_EXPIRED"]),
    }

    for index, (status, (state, warning_codes)) in enumerate(expected.items()):
        payment = _base_payment(client, owner, key=f"credit_diagnostic_{index}")
        purchase = client.app.state.credit_repository.get_purchase(payment["purchase"]["id"])
        purchase.status = status
        detail = client.get(
            f"/api/v1/admin/credit-purchases/{purchase.id}",
            headers=_bearer(admin, f"req_credit_diagnostic_{index}"),
        )
        assert detail.status_code == 200, detail.text
        assert detail.json()["data"]["reconciliation"] == {
            "state": state,
            "warning_codes": warning_codes,
        }


def test_memory_credit_ledger_cursor_does_not_lose_tied_timestamps() -> None:
    client = _client()
    owner = _login(client, 1995, "credit_ledger_cursor_owner")
    business = _create_business(client, owner, "credit_ledger_cursor_owner")
    repository = client.app.state.credit_repository
    fixed_at = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    entries = [
        repository.adjust_wallet(
            business_id=business["id"],
            amount=1,
            direction="add",
            reason=f"cursor_tie_{index}",
            notes=None,
            created_by=owner["user"]["id"],
        )
        for index in range(3)
    ]
    for entry in entries:
        entry.created_at = fixed_at

    first, cursor = repository.list_ledger(
        business_id=business["id"],
        ledger_type=None,
        cursor=None,
        limit=2,
    )
    second, final_cursor = repository.list_ledger(
        business_id=business["id"],
        ledger_type=None,
        cursor=cursor,
        limit=2,
    )

    assert cursor is not None
    assert final_cursor is None
    assert len({item.id for item in [*first, *second]}) == 3


def test_base_usdc_purchase_does_not_duplicate_referral_bonus_awarded_on_approval() -> None:
    client = _client()
    referrer_login = _login(client, 972, "base_referrer")
    referred_login = _login(client, 973, "base_referred")
    referrer_business = _create_business(client, referrer_login, "base_referrer")
    referred_business = _create_business(client, referred_login, "base_referred")
    referral_code = client.get("/api/v1/business/referrals", headers=_bearer(referrer_login, "req_base_referrer")).json()["data"]["referral_code"]
    awarded = client.app.state.credit_repository.award_referral_on_business_approval(
        referred_business_id=referred_business["id"],
        referral_code=referral_code,
        actor_user_id=referrer_login["user"]["id"],
    )
    assert awarded.created is True

    first = _base_payment(client, referred_login, key="base_ref_purchase")
    tx_hash = _tx_hash("base-ref-valid")
    client.app.state.onchain_credit_verifier.set_result(tx_hash, _verification(tx_hash, log_index=7))
    purchase_record = client.app.state.credit_repository.get_purchase(first["purchase"]["id"])
    purchase_record.tx_hash = tx_hash
    watcher_result = client.app.state.verify_base_usdc_credit_purchases_worker.run_once(request_id="req_watcher_base")
    duplicate_purchase = _base_payment(client, referred_login, key="base_ref_duplicate")
    duplicate = client.post(
        f"/api/v1/business/credits/purchases/{duplicate_purchase['purchase']['id']}/tx-hash",
        headers={**_headers(referred_login, "base_dup_tx"), "Content-Type": "application/json"},
        json={"tx_hash": tx_hash},
    )

    assert watcher_result["credited"] == 1
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "ONCHAIN_TX_ALREADY_USED"
    assert client.app.state.ad_repository.get_wallet(referred_business["id"]).available_credits == 5
    assert client.app.state.ad_repository.get_wallet(referrer_business["id"]).available_credits == 5
    referral_ledgers = [item for item in client.app.state.ad_repository.ledger.values() if item.business_id == referrer_business["id"] and item.type == "referral_bonus"]
    assert len(referral_ledgers) == 1


def test_base_usdc_watcher_scans_only_tx_ready_purchases_and_reports_cost_counters() -> None:
    client = _client()
    owner = _login(client, 979, "base_cost_owner")
    business = _create_business(client, owner, "base_cost_owner")
    no_hash = _base_payment(client, owner, key="base_cost_no_hash")
    tx_ready = _base_payment(client, owner, key="base_cost_ready")
    tx_hash = _tx_hash("base-cost-ready")
    client.app.state.onchain_credit_verifier.set_result(tx_hash, _verification(tx_hash, log_index=21))
    purchase_record = client.app.state.credit_repository.get_purchase(tx_ready["purchase"]["id"])
    purchase_record.tx_hash = tx_hash

    watcher_result = client.app.state.verify_base_usdc_credit_purchases_worker.run_once(request_id="req_watcher_cost")

    assert watcher_result["scanned"] == 1
    assert watcher_result["eligible"] == 1
    assert watcher_result["skipped_missing_tx"] == 0
    assert watcher_result["verified_attempts"] == 1
    assert watcher_result["credited"] == 1
    assert watcher_result["rpc_calls"] == 0
    assert watcher_result["latest_block_prefetched"] is False
    assert client.app.state.credit_repository.get_purchase(no_hash["purchase"]["id"]).status == "pending_payment"
    assert client.app.state.ad_repository.get_wallet(business["id"]).available_credits == 5


def test_base_usdc_duplicate_tx_log_race_only_one_purchase_credits() -> None:
    client = _client()
    first_owner = _login(client, 977, "race_first")
    second_owner = _login(client, 978, "race_second")
    first_business = _create_business(client, first_owner, "race_first")
    second_business = _create_business(client, second_owner, "race_second")
    first = _base_payment(client, first_owner, key="base_race_first")
    second = _base_payment(client, second_owner, key="base_race_second")
    tx_hash = _tx_hash("race-duplicate")
    client.app.state.onchain_credit_verifier.set_result(tx_hash, _verification(tx_hash, log_index=19))

    def submit(login: dict, purchase_id: str, key: str):
        return client.post(
            f"/api/v1/business/credits/purchases/{purchase_id}/tx-hash",
            headers={**_headers(login, key), "Content-Type": "application/json"},
            json={"tx_hash": tx_hash},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda args: submit(*args),
                [
                    (first_owner, first["purchase"]["id"], "race_tx_first"),
                    (second_owner, second["purchase"]["id"], "race_tx_second"),
                ],
            )
        )

    status_codes = sorted(response.status_code for response in responses)
    assert status_codes == [200, 409]
    assert sum(response.status_code == 200 and response.json()["data"]["credited"] for response in responses) == 1
    assert sum(response.status_code == 409 and response.json()["error"]["code"] == "ONCHAIN_TX_ALREADY_USED" for response in responses) == 1
    total_available = client.app.state.ad_repository.get_wallet(first_business["id"]).available_credits + client.app.state.ad_repository.get_wallet(second_business["id"]).available_credits
    assert total_available == 5


def test_base_usdc_business_buy_screen_hides_legacy_fallback_controls() -> None:
    source = open("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx", encoding="utf-8").read()
    hook_source = open("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts", encoding="utf-8").read()
    model_source = open("apps/web/src/hooks/useBusinessMiniAppModel.ts", encoding="utf-8").read()
    assert "Generando..." in source
    assert "Copiar wallet" in source
    assert "Copiar monto" in source
    assert "mini-action-button--copied" in source
    assert "setCopiedTarget(\"wallet\")" in source
    assert "setCopiedTarget(\"amount\")" in source
    assert "NODO acredita automaticamente cuando la tx confirma en Base." in source
    assert "Compra de creditos no disponible todavia. Falta configurar la wallet Base de NODO." in hook_source
    assert 'const action = "comprar creditos"' in hook_source
    assert "requireBusinessPinFor(action)" in hook_source
    assert "handleBusinessPinError(error, action)" in hook_source
    assert "BUSINESS_PIN_REQUIRED" in hook_source
    assert "useBusinessCreditsModel({ business: access.business" in model_source
    assert "startBusinessBaseUsdcPayment" in hook_source
    assert "submitBusinessBaseUsdcTxHash" in hook_source
    assert "localStorage.setItem(storageKey, purchase.id)" in hook_source
    assert "Fallback tarjeta" not in source
    assert "Metodo manual" not in source
    assert "Zelle manual" not in source
    assert "USDT TRC20 manual" not in source
    assert "Comprobante privado" not in source


def test_base_usdc_buy_screen_requires_explicit_pending_continue_and_package_choice() -> None:
    source = open("apps/web/src/screens/business-app/BusinessCreditsScreens.tsx", encoding="utf-8").read()
    hook_source = open("apps/web/src/hooks/business-mini-app/useBusinessCreditsModel.ts", encoding="utf-8").read()
    open_buy_source = hook_source.split("const openBuyCredits = useCallback", 1)[1].split("const continuePendingBaseUsdcPayment", 1)[0]

    assert "pendingCreditPurchase" in hook_source
    assert "loadingPendingPurchase" in hook_source
    assert "continuePendingBaseUsdcPayment" in hook_source
    assert "pendingBaseUsdcPurchaseStorageKey(business?.id)" in hook_source
    assert "BASE_USDC_PENDING_PURCHASE_LEGACY_KEY" in hook_source
    assert 'setView("credit-payment-pending")' not in open_buy_source
    assert "Tienes un pago pendiente" in source
    assert "Continuar pago pendiente" in source
    assert "Elige un paquete para generar el pago." in source
    assert "disabled={generatingCreditPayment || !creditPackage}" in source


def test_postgres_onchain_duplicate_tx_log_path_is_atomic() -> None:
    source = open("apps/api/app/modules/credits/postgres_onchain.py", encoding="utf-8").read()
    assert "on conflict (chain_id, tx_hash, tx_log_index) do nothing" in source
    assert "for update" in source
    assert "ONCHAIN_TX_ALREADY_USED" in source
    assert "do update" not in source.lower()


def test_founder_access_remains_audited_credit_free_publish_without_bypassing_verification() -> None:
    client = _client()
    owner = _login(client, 950, "founder")
    business = _create_business(client, owner, "founder")
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.founder_status = "active"
    stored_business.founder_expires_at = stored_business.created_at.replace(year=stored_business.created_at.year + 1)
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

    response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, "founder_ad"), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment.id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )

    assert response.status_code == 201, response.text
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet.available_credits == 0
    assert wallet.blocked_credits == 0
    assert "founder_free_use" in _event_types(client)
    assert response.json()["data"]["credit_hold"]["ledger_id"] is None


def test_safe_errors_and_migration_contracts_do_not_expose_private_fields_or_legacy_types() -> None:
    client = _client()
    owner = _login(client, 960, "safe")
    _create_business(client, owner, "safe")
    invalid_manual = client.post(
        "/api/v1/business/credits/manual-payment",
        headers=_headers(owner, "bad_manual"),
        data={"package_code": "starter", "payment_method": "zelle_manual_admin_approved"},
        files={"file": ("bad.txt", b"bad", "text/plain")},
    )
    assert invalid_manual.status_code == 400
    combined = invalid_manual.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined
    assert "sk_test_not_public" not in combined
    assert "whsec_test_secret" not in combined
    assert "storage_path" not in combined
    assert "owner@example.com" not in combined

    migration = open("database/migrations/0009_slice_08_credits_referrals.up.sql", encoding="utf-8").read()
    purchase_review = open("apps/api/app/modules/credits/postgres_purchase_review.py", encoding="utf-8").read()
    service = open("apps/api/app/modules/credits/service.py", encoding="utf-8").read()
    for expected in [
        "create table if not exists credit_purchases",
        "create table if not exists referral_codes",
        "create table if not exists referral_events",
        "'credit_purchase_proof'",
        "'credit_purchase'",
        "'admin_adjustment'",
        "'referral_bonus'",
        "credit_purchases_stripe_event_idx",
        "referral_events_referred_active_idx",
    ]:
        assert expected in migration
    assert "'refund'" not in migration
    assert "'adjustment'" not in migration
    assert "select * from credit_purchases where id = %s for update" in purchase_review
    assert 'allowed_statuses = {"pending_manual_review"} if admin_note else {"pending_payment", "paid"}' in purchase_review
    assert "IDEMPOTENCY_KEY_REQUIRED" in service
