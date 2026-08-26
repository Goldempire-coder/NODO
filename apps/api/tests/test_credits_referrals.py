from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlencode

import pytest
from eth_account import Account
from eth_account.messages import encode_defunct, encode_typed_data
from fastapi.testclient import TestClient
from PIL import Image

from app.core.errors import ApiError
from app.modules.credits.onchain import JsonRpcBaseUsdcVerifier, OnchainVerificationResult
from app.modules.credits.payment_authorizations import authorization_is_expired


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"
STRIPE_WEBHOOK_SECRET = "whsec_test_secret"
BASE_WALLET = "0x1111111111111111111111111111111111111111"
BASE_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
PAYMENT_CONTRACT = "0x3333333333333333333333333333333333333333"
PAYER_WALLET = "0x2222222222222222222222222222222222222222"
VALID_PDF = b"%PDF-1.7\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
CONTRACT_ENV_KEYS = (
    "NODO_CREDIT_PAYMENT_CONTRACT_ADDRESS",
    "NODO_CREDIT_PAYMENT_CONTRACT_VERSION",
    "NODO_CREDIT_AUTH_SIGNER_KEY",
    "NODO_CREDIT_AUTH_SIGNER_ADDRESS",
    "NODO_CREDIT_AUTH_SIGNER_VERSION",
    "CREDIT_CONTRACT_RATE_LIMIT_USER_MAX_ATTEMPTS",
    "CREDIT_CONTRACT_RATE_LIMIT_BUSINESS_MAX_ATTEMPTS",
    "CREDIT_CONTRACT_RATE_LIMIT_IP_MAX_ATTEMPTS",
    "CREDIT_CONTRACT_RATE_LIMIT_WINDOW_SECONDS",
    "CREDIT_CONTRACT_PENDING_PURCHASE_LIMIT",
)


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
from app.modules.credits import business_purchases as business_purchases_module  # noqa: E402
from app.modules.credits.credit_handoffs import CreditHandoffStoreUnavailable  # noqa: E402
from app.shared.rate_limit.redis import RateLimitUnavailableError  # noqa: E402


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


class SelectiveCreditContractRateLimiter:
    def __init__(self, blocked_key_fragment: str) -> None:
        self.blocked_key_fragment = blocked_key_fragment
        self.keys: list[str] = []

    def allow(self, key: str, *, max_attempts: int, window_seconds: int) -> bool:
        del max_attempts, window_seconds
        self.keys.append(key)
        return self.blocked_key_fragment not in key


class UnavailableSharedRateLimiter:
    def allow(self, key: str, *, max_attempts: int, window_seconds: int) -> bool:
        del key, max_attempts, window_seconds
        return True

    def allow_shared(self, key: str, *, max_attempts: int, window_seconds: int) -> bool:
        del key, max_attempts, window_seconds
        raise RateLimitUnavailableError("test shared limiter unavailable")


class UnavailableCreditHandoffStore:
    def create(self, record) -> None:  # type: ignore[no-untyped-def]
        del record
        raise CreditHandoffStoreUnavailable("test handoff store unavailable")


def _client(**env_overrides: str) -> TestClient:
    for key in CONTRACT_ENV_KEYS:
        if key not in env_overrides:
            os.environ.pop(key, None)
    _set_env(**env_overrides)
    client = TestClient(create_app())
    client.app.state.onchain_credit_verifier = FakeBaseUsdcVerifier()
    client.app.state.verify_base_usdc_credit_purchases_worker._verifier = client.app.state.onchain_credit_verifier
    return client


def _contract_client(**env_overrides: str | None) -> tuple[TestClient, str]:
    signer = Account.create()
    contract_env = {
        "NODO_CREDIT_PAYMENT_CONTRACT_ADDRESS": PAYMENT_CONTRACT,
        "NODO_CREDIT_PAYMENT_CONTRACT_VERSION": "2",
        "NODO_CREDIT_AUTH_SIGNER_KEY": signer.key.hex(),
        "NODO_CREDIT_AUTH_SIGNER_ADDRESS": signer.address,
        "NODO_CREDIT_AUTH_SIGNER_VERSION": "test-signer-v1",
        "ONCHAIN_CREDIT_AUTHORIZATION_TTL_MINUTES": "15",
    }
    contract_env.update({key: value for key, value in env_overrides.items() if value is not None})
    for key, value in env_overrides.items():
        if value is None:
            contract_env.pop(key, None)
            os.environ.pop(key, None)
    return _client(**contract_env), signer.address


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
    base = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "legacy_disabled_base"), "Content-Type": "application/json"},
        json={"package_code": "starter", "token_symbol": "USDC"},
    )

    assert stripe.status_code == 410
    assert stripe.json()["error"]["code"] == "CREDIT_PAYMENT_METHOD_DISABLED"
    assert manual.status_code == 410
    assert manual.json()["error"]["code"] == "CREDIT_PAYMENT_METHOD_DISABLED"
    assert base.status_code == 410
    assert base.json()["error"]["code"] == "CREDIT_PAYMENT_METHOD_DISABLED"
    assert client.app.state.credit_repository.purchases == {}


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


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("business_id", "00000000-0000-0000-0000-000000000001"),
        ("amount", "10.00"),
        ("price", "10.00"),
        ("credits_amount", 5),
        ("token", "USDC"),
        ("token_symbol", "USDC"),
        ("token_contract_address", BASE_USDC),
        ("chain_id", 8453),
        ("network", "base_mainnet"),
        ("treasury", BASE_WALLET),
        ("destination_wallet_address", BASE_WALLET),
        ("contract_address", PAYMENT_CONTRACT),
        ("contract_version", 2),
        ("valid_until", 1_800_000_000),
        ("expires_at", "2027-01-01T00:00:00Z"),
        ("purchase_ref", "0x" + "a" * 64),
        ("authorization", {"amount": 10_000_000}),
        ("signature", "0x" + "b" * 130),
    ],
)
def test_contract_payment_rejects_client_authority_fields_without_side_effects(field: str, value: object) -> None:
    client, _ = _contract_client()
    owner = _login(client, 1100, f"contract_forbidden_{field}")
    _create_business(client, owner, f"contract_forbidden_{field}")

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, f"contract_forbidden_{field}"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET, field: value},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.app.state.credit_repository.purchases == {}


def test_contract_mode_rejects_legacy_body_even_when_legacy_flag_is_enabled() -> None:
    client, _ = _contract_client(LEGACY_CREDIT_PAYMENT_METHODS_ENABLED="1")
    owner = _login(client, 1105, "contract_rejects_legacy")
    _create_business(client, owner, "contract_rejects_legacy")

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_rejects_legacy"), "Content-Type": "application/json"},
        json={"package_code": "starter", "token_symbol": "USDC"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert client.app.state.credit_repository.purchases == {}


def test_contract_mode_rejects_legacy_body_when_legacy_flag_is_disabled_without_side_effects() -> None:
    client, _ = _contract_client(LEGACY_CREDIT_PAYMENT_METHODS_ENABLED="0")
    owner = _login(client, 1107, "contract_rejects_disabled_legacy")
    business = _create_business(client, owner, "contract_rejects_disabled_legacy")
    wallet_before = client.app.state.credit_repository.get_wallet(business["id"])
    credits_before = wallet_before.available_credits if wallet_before is not None else 0
    ledger_count_before = len(client.app.state.ad_repository.ledger)

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_rejects_disabled_legacy"), "Content-Type": "application/json"},
        json={"package_code": "starter", "token_symbol": "USDC"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert "authorization_signature" not in response.text
    assert client.app.state.credit_repository.purchases == {}
    assert len(client.app.state.ad_repository.ledger) == ledger_count_before
    wallet_after = client.app.state.credit_repository.get_wallet(business["id"])
    credits_after = wallet_after.available_credits if wallet_after is not None else 0
    assert credits_after == credits_before


def test_legacy_base_payment_remains_available_without_contract_configuration() -> None:
    client = _client(LEGACY_CREDIT_PAYMENT_METHODS_ENABLED="1")
    owner = _login(client, 1106, "legacy_base_compatibility")
    _create_business(client, owner, "legacy_base_compatibility")

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "legacy_base_compatibility"), "Content-Type": "application/json"},
        json={"package_code": "starter", "token_symbol": "USDC"},
    )

    assert response.status_code == 201, response.text
    assert response.json()["data"]["purchase"]["payment_method"] == "base_usdc_onchain"


def test_contract_payment_signs_backend_snapshot_and_does_not_credit() -> None:
    client, signer_address = _contract_client()
    owner = _login(client, 1110, "contract_valid")
    business = _create_business(client, owner, "contract_valid")

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_valid"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET.upper().replace("0X", "0x")},
    )

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    purchase = data["purchase"]
    payment = data["payment"]
    assert purchase["business_id"] == business["id"]
    assert purchase["payment_method"] == "base_usdc_contract"
    assert purchase["status"] == "pending_payment"
    assert payment["payer_wallet_address"] == PAYER_WALLET
    assert payment["contract_address"] == PAYMENT_CONTRACT
    assert payment["contract_version"] == 2
    assert payment["purchase_ref"].startswith("0x") and len(payment["purchase_ref"]) == 66
    assert payment["authorization_signature"].startswith("0x") and len(payment["authorization_signature"]) == 132
    recovered = Account.recover_message(
        encode_typed_data(full_message=payment["authorization_typed_data"]),
        signature=payment["authorization_signature"],
    )
    assert recovered.lower() == signer_address.lower()
    stored = client.app.state.credit_repository.get_purchase(purchase["id"])
    assert stored is not None
    assert stored.payment_authorization_signer_address == signer_address.lower()
    assert client.app.state.credit_repository.ledger_for_purchase(purchase["id"]) is None
    wallet = client.app.state.credit_repository.get_wallet(business["id"])
    assert wallet is None or wallet.available_credits == 0


def test_contract_payment_rejects_tx_hash_submission_without_financial_effects() -> None:
    client, _ = _contract_client()
    owner = _login(client, 1115, "contract_tx_hash_reject")
    business = _create_business(client, owner, "contract_tx_hash_reject")
    payment = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_tx_hash_payment"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )
    assert payment.status_code == 201, payment.text
    purchase = payment.json()["data"]["purchase"]
    tx_hash = _tx_hash("contract-tx-hash-rejected")
    wallet_before = client.app.state.credit_repository.get_wallet(business["id"])
    credits_before = wallet_before.available_credits if wallet_before is not None else 0
    ledger_count_before = len(client.app.state.ad_repository.ledger)

    response = client.post(
        f"/api/v1/business/credits/purchases/{purchase['id']}/tx-hash",
        headers={**_headers(owner, "contract_tx_hash_submit"), "Content-Type": "application/json"},
        json={"tx_hash": tx_hash},
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CRYPTO_PAYMENT_TX_HASH_NOT_ACCEPTED"
    stored = client.app.state.credit_repository.get_purchase(purchase["id"])
    assert stored is not None
    assert stored.status == "pending_payment"
    assert stored.tx_hash is None
    assert client.app.state.credit_repository.ledger_for_purchase(purchase["id"]) is None
    assert len(client.app.state.ad_repository.ledger) == ledger_count_before
    wallet_after = client.app.state.credit_repository.get_wallet(business["id"])
    credits_after = wallet_after.available_credits if wallet_after is not None else 0
    assert credits_after == credits_before


def test_contract_payment_idempotency_replays_same_signature_and_rejects_payload_change() -> None:
    client, _ = _contract_client()
    owner = _login(client, 1120, "contract_replay")
    _create_business(client, owner, "contract_replay")
    headers = {**_headers(owner, "contract_replay"), "Content-Type": "application/json"}
    payload = {"package_code": "starter", "payer_wallet_address": PAYER_WALLET}

    first = client.post("/api/v1/business/credits/base-payment", headers=headers, json=payload)
    replay = client.post("/api/v1/business/credits/base-payment", headers=headers, json=payload)
    mismatch = client.post(
        "/api/v1/business/credits/base-payment",
        headers=headers,
        json={"package_code": "starter", "payer_wallet_address": "0x4444444444444444444444444444444444444444"},
    )

    assert first.status_code == 201, first.text
    assert replay.status_code == 201, replay.text
    assert replay.json()["data"] == first.json()["data"]
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"
    assert len(client.app.state.credit_repository.purchases) == 1


def test_contract_payment_allows_three_pending_and_rejects_fourth_before_signing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = _contract_client()
    owner = _login(client, 1122, "contract_pending_limit")
    business = _create_business(client, owner, "contract_pending_limit")
    payload = {"package_code": "starter", "payer_wallet_address": PAYER_WALLET}
    signed_calls = 0
    original_sign = business_purchases_module.sign_payment_authorization

    def track_signing(*args, **kwargs):  # type: ignore[no-untyped-def]
        nonlocal signed_calls
        signed_calls += 1
        return original_sign(*args, **kwargs)

    monkeypatch.setattr(business_purchases_module, "sign_payment_authorization", track_signing)
    created = [
        client.post(
            "/api/v1/business/credits/base-payment",
            headers={**_headers(owner, f"contract_pending_{index}"), "Content-Type": "application/json"},
            json=payload,
        )
        for index in range(1, 4)
    ]
    wallet_before = client.app.state.credit_repository.get_wallet(business["id"])
    credits_before = wallet_before.available_credits if wallet_before is not None else 0

    blocked = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_pending_4"), "Content-Type": "application/json"},
        json=payload,
    )

    assert [response.status_code for response in created] == [201, 201, 201]
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "CRYPTO_PAYMENT_PENDING_LIMIT_REACHED"
    assert signed_calls == 3
    assert len(client.app.state.credit_repository.purchases) == 3
    assert all(
        client.app.state.credit_repository.ledger_for_purchase(purchase.id) is None
        for purchase in client.app.state.credit_repository.purchases.values()
    )
    wallet_after = client.app.state.credit_repository.get_wallet(business["id"])
    credits_after = wallet_after.available_credits if wallet_after is not None else 0
    assert credits_after == credits_before


def test_contract_payment_terminal_purchases_do_not_count_and_replay_does_not_add_pending() -> None:
    client, _ = _contract_client()
    owner = _login(client, 1123, "contract_pending_terminal")
    _create_business(client, owner, "contract_pending_terminal")
    payload = {"package_code": "starter", "payer_wallet_address": PAYER_WALLET}
    first_headers = {**_headers(owner, "contract_terminal_1"), "Content-Type": "application/json"}
    first = client.post("/api/v1/business/credits/base-payment", headers=first_headers, json=payload)
    replay = client.post("/api/v1/business/credits/base-payment", headers=first_headers, json=payload)
    second = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_terminal_2"), "Content-Type": "application/json"},
        json=payload,
    )
    third = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_terminal_3"), "Content-Type": "application/json"},
        json=payload,
    )
    purchases = list(client.app.state.credit_repository.purchases.values())
    purchases[0].status = "credited"
    purchases[1].status = "expired"
    purchases[2].status = "rejected"

    fourth = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_terminal_4"), "Content-Type": "application/json"},
        json=payload,
    )

    assert first.status_code == replay.status_code == second.status_code == third.status_code == 201
    assert replay.json()["data"] == first.json()["data"]
    assert fourth.status_code == 201, fourth.text
    assert len(client.app.state.credit_repository.purchases) == 4


@pytest.mark.parametrize(
    "blocked_key_fragment",
    [
        "credits:base_usdc_contract_payment:user:",
        "credits:base_usdc_contract_payment:business:",
        "credits:base_usdc_contract_payment:ip:",
    ],
)
def test_contract_payment_enforces_user_business_and_ip_rate_limit_keys(
    blocked_key_fragment: str,
) -> None:
    client, _ = _contract_client()
    owner = _login(client, 1124, f"contract_rate_{blocked_key_fragment[-4:]}")
    _create_business(client, owner, f"contract_rate_{blocked_key_fragment[-4:]}")
    limiter = SelectiveCreditContractRateLimiter(blocked_key_fragment)
    client.app.state.rate_limiter = limiter

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, f"contract_rate_{blocked_key_fragment[-4:]}"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert any(blocked_key_fragment in key for key in limiter.keys)
    assert client.app.state.credit_repository.purchases == {}


@pytest.mark.parametrize(
    "limited_setting",
    [
        "credit_contract_rate_limit_user_max_attempts",
        "credit_contract_rate_limit_business_max_attempts",
        "credit_contract_rate_limit_ip_max_attempts",
    ],
)
def test_contract_payment_rate_limits_each_actor_dimension(limited_setting: str) -> None:
    client, _ = _contract_client()
    owner = _login(client, 1126, f"contract_actual_rate_{limited_setting}")
    _create_business(client, owner, f"contract_actual_rate_{limited_setting}")
    limits = {
        "credit_contract_rate_limit_user_max_attempts": 10,
        "credit_contract_rate_limit_business_max_attempts": 10,
        "credit_contract_rate_limit_ip_max_attempts": 10,
    }
    limits[limited_setting] = 1
    client.app.state.settings = replace(client.app.state.settings, **limits)
    payload = {"package_code": "starter", "payer_wallet_address": PAYER_WALLET}

    first = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, f"contract_actual_rate_{limited_setting}_1"), "Content-Type": "application/json"},
        json=payload,
    )
    blocked = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, f"contract_actual_rate_{limited_setting}_2"), "Content-Type": "application/json"},
        json=payload,
    )

    assert first.status_code == 201, first.text
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "RATE_LIMITED"
    assert len(client.app.state.credit_repository.purchases) == 1


def test_contract_payment_env_cannot_relax_antiabuse_policy() -> None:
    client, _ = _contract_client(
        CREDIT_CONTRACT_RATE_LIMIT_USER_MAX_ATTEMPTS="500",
        CREDIT_CONTRACT_RATE_LIMIT_BUSINESS_MAX_ATTEMPTS="500",
        CREDIT_CONTRACT_RATE_LIMIT_IP_MAX_ATTEMPTS="500",
        CREDIT_CONTRACT_RATE_LIMIT_WINDOW_SECONDS="1",
        CREDIT_CONTRACT_PENDING_PURCHASE_LIMIT="500",
    )

    assert client.app.state.settings.credit_contract_rate_limit_user_max_attempts == 5
    assert client.app.state.settings.credit_contract_rate_limit_business_max_attempts == 5
    assert client.app.state.settings.credit_contract_rate_limit_ip_max_attempts == 20
    assert client.app.state.settings.credit_contract_rate_limit_window_seconds == 600
    assert client.app.state.settings.credit_contract_pending_purchase_limit == 3


def test_contract_payment_fails_closed_when_shared_rate_limiter_is_unavailable() -> None:
    client, _ = _contract_client()
    owner = _login(client, 1125, "contract_shared_limiter_unavailable")
    business = _create_business(client, owner, "contract_shared_limiter_unavailable")
    client.app.state.settings = replace(client.app.state.settings, app_env="staging")
    client.app.state.rate_limiter = UnavailableSharedRateLimiter()
    wallet_before = client.app.state.credit_repository.get_wallet(business["id"])
    credits_before = wallet_before.available_credits if wallet_before is not None else 0

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_shared_limiter_unavailable"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CRYPTO_PAYMENT_RATE_LIMIT_UNAVAILABLE"
    assert client.app.state.credit_repository.purchases == {}
    ledger, next_cursor = client.app.state.credit_repository.list_ledger(
        business_id=business["id"],
        ledger_type=None,
        cursor=None,
        limit=50,
    )
    assert ledger == []
    assert next_cursor is None
    wallet_after = client.app.state.credit_repository.get_wallet(business["id"])
    credits_after = wallet_after.available_credits if wallet_after is not None else 0
    assert credits_after == credits_before


def test_credit_wallet_handoff_prepares_one_contract_purchase_without_crediting() -> None:
    client, _ = _contract_client()
    owner = _login(client, 1127, "credit_handoff_owner")
    business = _create_business(client, owner, "credit_handoff_owner")
    payer = Account.create()
    wallet_before = client.app.state.credit_repository.ensure_wallet(business["id"])

    created = client.post(
        "/api/v1/business/credits/handoffs",
        headers={**_bearer(owner, "req_handoff_create"), "Content-Type": "application/json"},
        json={"package_code": "starter"},
    )

    assert created.status_code == 201, created.text
    handoff = created.json()["data"]["handoff"]
    assert handoff["token"]
    assert "business_id" not in handoff
    assert handoff["token"] not in repr(client.app.state.credit_handoff_store.__dict__)
    assert handoff["token"] not in json.dumps(
        [event.__dict__ for event in client.app.state.audit_writer.events],
        default=str,
    )
    challenge = client.post(
        "/api/v1/business/credits/handoffs/challenge",
        json={"handoff_token": handoff["token"]},
    )
    assert challenge.status_code == 200, challenge.text
    challenge_text = challenge.json()["data"]["challenge"]
    signature = "0x" + Account.sign_message(
        encode_defunct(text=challenge_text),
        payer.key,
    ).signature.hex()
    claim_payload = {
        "handoff_token": handoff["token"],
        "wallet_address": payer.address,
        "chain_id": 8453,
        "signature": signature,
    }

    claimed = client.post(
        "/api/v1/business/credits/handoffs/claim",
        json=claim_payload,
    )
    replay = client.post(
        "/api/v1/business/credits/handoffs/claim",
        json=claim_payload,
    )
    status = client.get(
        f"/api/v1/business/credits/handoffs/{handoff['id']}",
        headers=_bearer(owner, "req_handoff_status"),
    )

    assert claimed.status_code == 200, claimed.text
    assert replay.status_code == 200, replay.text
    assert replay.json()["data"] == claimed.json()["data"]
    assert status.status_code == 200, status.text
    for response in (created, challenge, claimed, replay, status):
        assert response.headers["cache-control"] == "private, no-store"
    status_data = status.json()["data"]
    assert status_data["handoff"]["status"] == "prepared"
    assert status_data["handoff"]["wallet_address_masked"] != payer.address.lower()
    assert status_data["purchase"]["payment_method"] == "base_usdc_contract"
    assert status_data["payment"]["payer_wallet_address"] == payer.address.lower()
    assert len(client.app.state.credit_repository.purchases) == 1
    purchase = next(iter(client.app.state.credit_repository.purchases.values()))
    assert client.app.state.credit_repository.ledger_for_purchase(purchase.id) is None
    wallet_after = client.app.state.credit_repository.ensure_wallet(business["id"])
    assert wallet_after.available_credits == wallet_before.available_credits == 0


def test_credit_wallet_handoff_rejects_wrong_chain_and_wrong_signature() -> None:
    client, _ = _contract_client()
    owner = _login(client, 1128, "credit_handoff_invalid")
    _create_business(client, owner, "credit_handoff_invalid")
    payer = Account.create()
    other = Account.create()
    created = client.post(
        "/api/v1/business/credits/handoffs",
        headers={**_bearer(owner, "req_handoff_invalid_create"), "Content-Type": "application/json"},
        json={"package_code": "starter"},
    )
    handoff = created.json()["data"]["handoff"]
    challenge = client.post(
        "/api/v1/business/credits/handoffs/challenge",
        json={"handoff_token": handoff["token"]},
    ).json()["data"]["challenge"]
    wrong_signature = "0x" + Account.sign_message(
        encode_defunct(text=challenge),
        other.key,
    ).signature.hex()

    wrong_chain = client.post(
        "/api/v1/business/credits/handoffs/claim",
        json={
            "handoff_token": handoff["token"],
            "wallet_address": payer.address,
            "chain_id": 1,
            "signature": wrong_signature,
        },
    )
    wrong_signer = client.post(
        "/api/v1/business/credits/handoffs/claim",
        json={
            "handoff_token": handoff["token"],
            "wallet_address": payer.address,
            "chain_id": 8453,
            "signature": wrong_signature,
        },
    )

    assert wrong_chain.status_code == 409
    assert wrong_chain.json()["error"]["code"] == "CREDIT_HANDOFF_NETWORK_INVALID"
    assert wrong_signer.status_code == 409
    assert wrong_signer.json()["error"]["code"] == "CREDIT_HANDOFF_SIGNATURE_INVALID"
    assert client.app.state.credit_repository.purchases == {}


def test_credit_wallet_handoff_status_is_owned_and_expired_handoff_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = _contract_client()
    owner = _login(client, 1129, "credit_handoff_expired")
    _create_business(client, owner, "credit_handoff_expired")
    other = _login(client, 1131, "credit_handoff_other")
    _create_business(client, other, "credit_handoff_other")
    created = client.post(
        "/api/v1/business/credits/handoffs",
        headers={**_bearer(owner, "req_handoff_expired_create"), "Content-Type": "application/json"},
        json={"package_code": "starter"},
    )
    handoff = created.json()["data"]["handoff"]

    forbidden_status = client.get(
        f"/api/v1/business/credits/handoffs/{handoff['id']}",
        headers=_bearer(other, "req_handoff_other_status"),
    )
    from app.modules.credits import credit_handoffs as credit_handoffs_module

    monkeypatch.setattr(
        credit_handoffs_module,
        "utc_now",
        lambda: datetime.fromisoformat(handoff["expires_at"]) + timedelta(seconds=1),
    )
    expired = client.post(
        "/api/v1/business/credits/handoffs/challenge",
        json={"handoff_token": handoff["token"]},
    )

    assert forbidden_status.status_code == 404
    assert forbidden_status.json()["error"]["code"] == "CREDIT_HANDOFF_NOT_FOUND"
    assert expired.status_code == 410
    assert expired.json()["error"]["code"] == "CREDIT_HANDOFF_EXPIRED"
    assert client.app.state.credit_repository.purchases == {}


def test_credit_wallet_handoff_rejects_client_authority_and_store_failure() -> None:
    client, _ = _contract_client()
    owner = _login(client, 1132, "credit_handoff_strict")
    _create_business(client, owner, "credit_handoff_strict")
    forbidden = client.post(
        "/api/v1/business/credits/handoffs",
        headers={**_bearer(owner, "req_handoff_forbidden"), "Content-Type": "application/json"},
        json={"package_code": "starter", "business_id": "client-controlled"},
    )
    client.app.state.credit_handoff_store = UnavailableCreditHandoffStore()
    unavailable = client.post(
        "/api/v1/business/credits/handoffs",
        headers={**_bearer(owner, "req_handoff_store_down"), "Content-Type": "application/json"},
        json={"package_code": "starter"},
    )

    assert forbidden.status_code == 422
    assert forbidden.json()["error"]["code"] == "VALIDATION_ERROR"
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "CREDIT_HANDOFF_UNAVAILABLE"
    assert client.app.state.credit_repository.purchases == {}


@pytest.mark.parametrize(
    "blocked_key_fragment",
    (
        "credits:wallet_handoff:create:user:",
        "credits:wallet_handoff:create:business:",
        "credits:wallet_handoff:create:ip:",
    ),
)
def test_credit_wallet_handoff_creation_is_rate_limited_before_storage(
    blocked_key_fragment: str,
) -> None:
    client, _ = _contract_client()
    owner = _login(client, 1133, "credit_handoff_limited")
    _create_business(client, owner, "credit_handoff_limited")
    client.app.state.rate_limiter = SelectiveCreditContractRateLimiter(
        blocked_key_fragment,
    )

    response = client.post(
        "/api/v1/business/credits/handoffs",
        headers={**_bearer(owner, "req_handoff_limited"), "Content-Type": "application/json"},
        json={"package_code": "starter"},
    )

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMITED"
    assert client.app.state.credit_handoff_store._records == {}
    assert client.app.state.credit_repository.purchases == {}


def test_contract_payment_replay_rejects_an_expired_cached_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _ = _contract_client()
    owner = _login(client, 1121, "contract_expired_replay")
    _create_business(client, owner, "contract_expired_replay")
    headers = {**_headers(owner, "contract_expired_replay"), "Content-Type": "application/json"}
    payload = {"package_code": "starter", "payer_wallet_address": PAYER_WALLET}

    first = client.post("/api/v1/business/credits/base-payment", headers=headers, json=payload)
    valid_until = first.json()["data"]["payment"]["authorization_valid_until"]
    monkeypatch.setattr(
        business_purchases_module,
        "utc_now",
        lambda: datetime.fromtimestamp(valid_until, tz=timezone.utc),
    )
    replay = client.post("/api/v1/business/credits/base-payment", headers=headers, json=payload)

    assert first.status_code == 201, first.text
    assert replay.status_code == 409
    assert replay.json()["error"]["code"] == "CRYPTO_PAYMENT_AUTHORIZATION_EXPIRED"
    assert len(client.app.state.credit_repository.purchases) == 1


def test_contract_payment_fails_closed_when_signer_configuration_is_missing() -> None:
    client, _ = _contract_client(NODO_CREDIT_AUTH_SIGNER_KEY="")
    owner = _login(client, 1130, "contract_no_signer")
    _create_business(client, owner, "contract_no_signer")

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_no_signer"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CRYPTO_PAYMENT_SIGNER_UNAVAILABLE"
    assert client.app.state.credit_repository.purchases == {}


def test_contract_payment_fails_closed_when_contract_version_is_missing() -> None:
    client, _ = _contract_client(NODO_CREDIT_PAYMENT_CONTRACT_VERSION=None)
    owner = _login(client, 1133, "contract_no_version")
    _create_business(client, owner, "contract_no_version")

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_no_version"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "CRYPTO_CONTRACT_PAYMENT_NOT_CONFIGURED"
    assert client.app.state.credit_repository.purchases == {}


def test_contract_payment_rejects_zero_payer_and_invalid_contract_configuration() -> None:
    client, _ = _contract_client()
    owner = _login(client, 1131, "contract_zero_payer")
    _create_business(client, owner, "contract_zero_payer")
    zero_payer = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_zero_payer"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": "0x" + "0" * 40},
    )
    assert zero_payer.status_code == 422
    assert client.app.state.credit_repository.purchases == {}

    invalid_client, _ = _contract_client(NODO_CREDIT_PAYMENT_CONTRACT_ADDRESS="0x" + "0" * 40)
    invalid_owner = _login(invalid_client, 1132, "contract_zero_contract")
    _create_business(invalid_client, invalid_owner, "contract_zero_contract")
    invalid_contract = invalid_client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(invalid_owner, "contract_zero_contract"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )
    assert invalid_contract.status_code == 503
    assert invalid_contract.json()["error"]["code"] == "CRYPTO_CONTRACT_PAYMENT_NOT_CONFIGURED"
    assert invalid_client.app.state.credit_repository.purchases == {}


def test_contract_purchase_detail_resumes_valid_authorization_without_side_effects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = _contract_client()
    owner = _login(client, 1134, "contract_resume_valid")
    business = _create_business(client, owner, "contract_resume_valid")
    created = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_resume_create"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )
    assert created.status_code == 201, created.text
    created_data = created.json()["data"]
    purchase_id = created_data["purchase"]["id"]
    verifier_calls_before = list(client.app.state.onchain_credit_verifier.calls)
    ledger_count_before = len(client.app.state.ad_repository.ledger)
    wallet_before = client.app.state.credit_repository.get_wallet(business["id"])
    credits_before = wallet_before.available_credits if wallet_before is not None else 0
    monkeypatch.setattr(
        business_purchases_module,
        "sign_payment_authorization",
        lambda *args, **kwargs: pytest.fail("purchase detail must not re-sign"),
    )

    detail = client.get(
        f"/api/v1/business/credits/purchases/{purchase_id}",
        headers=_bearer(owner, "contract_resume_detail"),
    )

    assert detail.status_code == 200, detail.text
    data = detail.json()["data"]
    assert data["purchase"]["id"] == purchase_id
    assert data["payment"]["authorization_status"] == "valid"
    assert data["payment"]["capabilities"] == {"can_pay": True}
    assert data["payment"]["payer_wallet_address"] == PAYER_WALLET
    assert data["payment"]["purchase_ref"] == created_data["payment"]["purchase_ref"]
    assert data["payment"]["authorization_typed_data"] == created_data["payment"]["authorization_typed_data"]
    assert data["payment"]["authorization_signature"] == created_data["payment"]["authorization_signature"]
    assert client.app.state.onchain_credit_verifier.calls == verifier_calls_before
    assert len(client.app.state.ad_repository.ledger) == ledger_count_before
    wallet_after = client.app.state.credit_repository.get_wallet(business["id"])
    credits_after = wallet_after.available_credits if wallet_after is not None else 0
    assert credits_after == credits_before == 0


def test_contract_purchase_detail_returns_expired_without_payable_signature() -> None:
    client, _ = _contract_client()
    owner = _login(client, 1135, "contract_resume_expired")
    _create_business(client, owner, "contract_resume_expired")
    created = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_resume_expired_create"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )
    purchase_id = created.json()["data"]["purchase"]["id"]
    stored = client.app.state.credit_repository.get_purchase(purchase_id)
    stored.payment_authorization_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    detail = client.get(
        f"/api/v1/business/credits/purchases/{purchase_id}",
        headers=_bearer(owner, "contract_resume_expired_detail"),
    )

    assert detail.status_code == 200, detail.text
    payment = detail.json()["data"]["payment"]
    assert payment["authorization_status"] == "expired"
    assert payment["capabilities"] == {"can_pay": False}
    assert "authorization_signature" not in payment
    assert "authorization_typed_data" not in payment


@pytest.mark.parametrize("invalid_field", ["payment_contract_address", "payment_authorization_signer_version"])
def test_contract_purchase_detail_requires_reissue_for_incomplete_or_incompatible_snapshot(invalid_field: str) -> None:
    client, _ = _contract_client()
    owner = _login(client, 1136, f"contract_resume_{invalid_field}")
    _create_business(client, owner, f"contract_resume_{invalid_field}")
    created = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, f"contract_resume_{invalid_field}_create"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )
    purchase_id = created.json()["data"]["purchase"]["id"]
    stored = client.app.state.credit_repository.get_purchase(purchase_id)
    setattr(stored, invalid_field, None if invalid_field == "payment_contract_address" else "obsolete-signer")

    detail = client.get(
        f"/api/v1/business/credits/purchases/{purchase_id}",
        headers=_bearer(owner, f"contract_resume_{invalid_field}_detail"),
    )

    assert detail.status_code == 200, detail.text
    payment = detail.json()["data"]["payment"]
    assert payment["authorization_status"] == "reissue_required"
    assert payment["capabilities"] == {"can_pay": False}
    assert "authorization_signature" not in payment
    assert "authorization_typed_data" not in payment


def test_contract_purchase_detail_preserves_ownership_and_legacy_shape() -> None:
    client, _ = _contract_client()
    owner = _login(client, 1137, "contract_resume_owner")
    _create_business(client, owner, "contract_resume_owner")
    created = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, "contract_resume_owner_create"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )
    purchase_id = created.json()["data"]["purchase"]["id"]
    other_owner = _login(client, 1138, "contract_resume_other")
    _create_business(client, other_owner, "contract_resume_other")

    forbidden = client.get(
        f"/api/v1/business/credits/purchases/{purchase_id}",
        headers=_bearer(other_owner, "contract_resume_other_detail"),
    )
    assert forbidden.status_code == 404
    assert forbidden.json()["error"]["code"] == "PURCHASE_NOT_FOUND"

    legacy_client = _client()
    legacy_owner = _login(legacy_client, 1139, "legacy_resume")
    _create_business(legacy_client, legacy_owner, "legacy_resume")
    legacy = _base_payment(legacy_client, legacy_owner, key="legacy_resume_create")
    legacy_detail = legacy_client.get(
        f"/api/v1/business/credits/purchases/{legacy['purchase']['id']}",
        headers=_bearer(legacy_owner, "legacy_resume_detail"),
    )
    assert legacy_detail.status_code == 200, legacy_detail.text
    assert legacy_detail.json()["data"]["purchase"]["payment_method"] == "base_usdc_onchain"
    assert "payment" not in legacy_detail.json()["data"]


def test_contract_authorization_expiration_uses_strict_boundary() -> None:
    boundary = datetime(2026, 8, 22, 12, 0, tzinfo=timezone.utc)

    assert authorization_is_expired(valid_until=int(boundary.timestamp()), now=boundary) is True
    assert authorization_is_expired(valid_until=int(boundary.timestamp()), now=boundary - timedelta(seconds=1)) is False


@pytest.mark.parametrize("gate", ["not_approved", "business_blocked", "owner_link_missing"])
def test_contract_payment_requires_full_business_owner_access(gate: str) -> None:
    client, _ = _contract_client()
    owner = _login(client, {"not_approved": 1140, "business_blocked": 1141, "owner_link_missing": 1142}[gate], f"contract_{gate}")
    business = _create_business(client, owner, f"contract_{gate}", approved=gate != "not_approved")
    stored = client.app.state.business_repository.get_business(business["id"])
    if gate == "business_blocked":
        stored.verification_status = "blocked"
    if gate == "owner_link_missing":
        for link in client.app.state.business_repository.list_access_links_for_business(business["id"]):
            link.status = "revoked"

    response = client.post(
        "/api/v1/business/credits/base-payment",
        headers={**_headers(owner, f"contract_{gate}"), "Content-Type": "application/json"},
        json={"package_code": "starter", "payer_wallet_address": PAYER_WALLET},
    )

    assert response.status_code in {403, 409}
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
    api_source = open("apps/web/src/api/credits.ts", encoding="utf-8").read()
    settings_source = open("apps/web/src/screens/business-app/BusinessSettingsScreen.tsx", encoding="utf-8").read()
    model_source = open("apps/web/src/hooks/useBusinessMiniAppModel.ts", encoding="utf-8").read()
    assert "Generando..." in source
    assert "Wallet pagadora" in source
    assert "Conectar wallet" in source
    assert "Conecta la wallet desde donde pagarás." in source
    assert "Esta wallet será la que firma y paga." in source
    assert "NODO no ve ni guarda tu clave privada." in source
    assert "Necesitas USDC y un poco de ETH en Base para gas." in source
    assert "priceUsdc" in source
    assert "{item.priceUsdc} USDC" in source
    assert 'priceUsdc: "10"' in source
    assert 'priceUsdc: "25"' in source
    assert 'priceUsdc: "75"' in source
    assert 'priceUsdc: "250"' in source
    assert "Pagarás ${selected.priceUsdc} USDC en red Base." in source
    assert "La autorizacion final confirma el monto antes de pagar." in source
    assert "NODO calcula el monto y prepara la autorizacion." not in source
    assert "No pegues hashes en este flujo." in source
    assert "authorization_status" in source
    assert "capabilities.can_pay" in source
    assert "Actualizar estado" in source
    assert "payer_wallet_address: payerWalletAddress" in api_source
    assert "token_symbol" not in api_source
    assert "submitBusinessBaseUsdcTxHash" not in api_source
    assert "/tx-hash" not in api_source
    assert "submitBusinessBaseUsdcTxHash" not in hook_source
    assert "credit_tx_submit" not in hook_source
    assert "baseUsdcTxHash" not in hook_source
    assert "Pegar tx hash" not in source
    assert "Verificar tx" not in source
    assert "Identificador de transaccion" not in source
    assert 'placeholder="0x..."' not in source
    assert "Pegar un hash" not in settings_source
    assert 'const action = "comprar creditos"' in hook_source
    assert "requireBusinessPinFor(action)" in hook_source
    assert "handleBusinessPinError(error, action)" in hook_source
    assert "BUSINESS_PIN_REQUIRED" in hook_source
    assert "useInjectedWallet" in hook_source
    assert "connectedWalletAddress" in hook_source
    assert "walletIsBase" in hook_source
    assert "setPayerWalletAddress" not in hook_source
    assert "useBusinessCreditsModel({ business: access.business" in model_source
    assert "startBusinessBaseUsdcPayment" in hook_source
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
    assert "disabled={generatingCreditPayment || !creditPackage || !connectedWalletAddress || !walletIsBase}" in source


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
