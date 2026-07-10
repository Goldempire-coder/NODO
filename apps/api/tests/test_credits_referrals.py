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
STRIPE_WEBHOOK_SECRET = "whsec_test_secret"


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
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402


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
        client.app.state.business_repository.create_access_link(
            business_id=business["id"],
            user_id=login["user"]["id"],
            telegram_id_snapshot=stored_user.telegram_id,
            role_in_business="owner",
            linked_by_admin_id=login["user"]["id"],
            reason="test_active_business_access",
        )
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
        files={"file": ("proof.pdf", b"proof-bytes", "application/pdf")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


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
        files={"file": ("proof.pdf", b"proof-bytes", "application/pdf")},
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


def test_referrals_prevent_self_referral_duplicate_and_award_bonus_once_after_purchase() -> None:
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
    applied = client.post(
        "/api/v1/business/referrals/apply",
        headers={**_headers(referred_login, "apply_ref"), "Content-Type": "application/json"},
        json={"referral_code": referrer_data["referral_code"]},
    )
    duplicate = client.post(
        "/api/v1/business/referrals/apply",
        headers={**_headers(referred_login, "apply_ref_2"), "Content-Type": "application/json"},
        json={"referral_code": referrer_data["referral_code"]},
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
    assert applied.status_code == 200, applied.text
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "REFERRAL_ALREADY_USED"
    assert credited.status_code == 200, credited.text
    assert duplicate_event.status_code == 200
    assert client.app.state.ad_repository.get_wallet(referred_business["id"]).available_credits == 5
    assert client.app.state.ad_repository.get_wallet(referrer_business["id"]).available_credits == 1
    referral_ledgers = [item for item in client.app.state.ad_repository.ledger.values() if item.business_id == referrer_business["id"] and item.type == "referral_bonus"]
    assert len(referral_ledgers) == 1


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
