from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlencode

from fastapi.testclient import TestClient

from app.modules.orders.models import utc_now


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-10",
        "NODO_BUILD_ID": "pytest-jobs-notifications-build",
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


def _approved_business_with_method(client: TestClient, login: dict, *, credits: int = 5) -> tuple[dict, str]:
    business = _create_business(client, login, f"biz_{login['user']['id']}")
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
        method_type="zelle",
        network=None,
        account_value="owner@example.com",
        account_masked="***.com",
        holder_name="Owner Test",
    )
    payment.verified_status = "approved"
    payment.active = True
    if credits:
        client.app.state.ad_repository.grant_test_credits(business_id=business["id"], amount=credits, created_by=login["user"]["id"])
    return business, payment.id


def _create_ad(client: TestClient, owner: dict, payment_method_id: str, *, key: str = "ad") -> dict:
    response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment_method_id,
            "payment_method": "zelle",
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


def _upload_payment_evidence(client: TestClient, remitter: dict, order_id: str, key: str = "evidence") -> dict:
    response = client.post(
        f"/api/v1/orders/{order_id}/payment-evidence",
        headers=_headers(remitter, key),
        data={"file_type": "payment_evidence"},
        files={"file": ("proof.png", b"proof", "image/png")},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _report_payment(client: TestClient, remitter: dict, order: dict, *, key: str = "report") -> dict:
    evidence = _upload_payment_evidence(client, remitter, order["id"], key=f"{key}_evidence")
    response = client.post(
        f"/api/v1/orders/{order['id']}/payment-report",
        headers={**_headers(remitter, key), "Content-Type": "application/json"},
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
    assert response.status_code == 201, response.text
    return response.json()["data"]


def _seed_order(client: TestClient, *, owner_id: int, remitter_id: int) -> tuple[dict, dict, dict, dict, dict]:
    owner = _login(client, owner_id, f"owner_{owner_id}")
    business, method_id = _approved_business_with_method(client, owner, credits=3)
    ad = _create_ad(client, owner, method_id, key=f"ad_{owner_id}")
    remitter = _login(client, remitter_id, f"remitter_{remitter_id}")
    order = _create_order(client, remitter, ad["id"], key=f"order_{remitter_id}")
    return owner, business, ad, remitter, order


def _confirm_payment(client: TestClient, owner: dict, order_id: str, key: str) -> None:
    response = client.post(
        f"/api/v1/business/orders/{order_id}/confirm-payment",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={"reason": "Pago recibido"},
    )
    assert response.status_code == 200, response.text


def _mark_delivered(client: TestClient, owner: dict, order_id: str, key: str) -> None:
    response = client.post(
        f"/api/v1/business/orders/{order_id}/mark-delivered",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={"reason": "Pago movil enviado"},
    )
    assert response.status_code == 200, response.text


def _run_job(client: TestClient, now) -> dict:  # type: ignore[no-untyped-def]
    return client.app.state.expire_and_escalate_orders_worker.run(current_time=now, batch_size=100, dry_run=False, request_id="req_job_test")


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_waiting_payment_expiry_dry_run_is_non_mutating_then_cancels_and_keeps_ad_hold() -> None:
    client = _client()
    _, business, ad, remitter, order = _seed_order(client, owner_id=1000, remitter_id=1001)
    admin = _login(client, 1002, "admin")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    past = utc_now() - timedelta(minutes=5)
    client.app.state.order_repository.update_order(stored, payment_report_deadline_at=past, expires_at=past)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before = wallet_before.blocked_credits
    available_before = wallet_before.available_credits

    dry = client.post(
        "/api/v1/admin/jobs/expire-and-escalate-orders/dry-run",
        headers=_headers(admin, "dry_waiting"),
        params={"current_time": utc_now().isoformat()},
    )
    assert dry.status_code == 200, dry.text
    missing_idempotency = client.post(
        "/api/v1/admin/jobs/expire-and-escalate-orders/dry-run",
        headers=_bearer(admin, "req_dry_missing_idempotency"),
        params={"current_time": utc_now().isoformat()},
    )
    assert missing_idempotency.status_code == 400
    assert missing_idempotency.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "waiting_payment"
    assert client.app.state.ad_repository.get_wallet(business["id"]).blocked_credits == wallet_before.blocked_credits
    assert client.app.state.job_repository.notification_jobs == {}

    result = _run_job(client, utc_now())
    assert result["job_run"]["status"] == "finished"
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "cancelled"
    assert client.app.state.order_repository.get_by_id(order["id"]).cancel_reason == "payment_not_reported_in_time"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "active"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.blocked_credits == blocked_before
    assert wallet_after.available_credits == available_before
    assert "order_cancelled_payment_not_reported" in _event_types(client)
    cancelled_notifications = [
        n for n in client.app.state.job_repository.notification_jobs.values() if n.notification_type == "order_cancelled_payment_not_reported"
    ]
    business_owner_id = client.app.state.business_repository.get_business(business["id"]).owner_user_id
    assert len(cancelled_notifications) == 2
    assert {n.recipient_user_id for n in cancelled_notifications} == {remitter["user"]["id"], business_owner_id}
    combined = json.dumps([n.__dict__ for n in client.app.state.job_repository.notification_jobs.values()], default=str)
    assert "order_cancelled_payment_not_reported" in combined
    assert "owner@example.com" not in combined
    assert "storage_path" not in combined


def test_payment_reported_deadline_opens_dispute_and_keeps_credits_blocked_and_ad_in_order() -> None:
    client = _client()
    _, business, ad, remitter, order = _seed_order(client, owner_id=1010, remitter_id=1011)
    _report_payment(client, remitter, order, key="reported_deadline")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    past = utc_now() - timedelta(hours=7)
    client.app.state.order_repository.update_order(stored, business_response_deadline_at=past)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])

    _run_job(client, utc_now())

    updated = client.app.state.order_repository.get_by_id(order["id"])
    assert updated.status == "disputed"
    assert updated.dispute_reason == "business_no_payment_confirmation"
    assert client.app.state.dispute_repository.get_open_for_order(order["id"]) is not None
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    assert client.app.state.ad_repository.get_wallet(business["id"]).blocked_credits == wallet_before.blocked_credits
    assert "order_disputed_business_no_payment_confirmation" in _event_types(client)
    dispute_notifications = [
        n for n in client.app.state.job_repository.notification_jobs.values() if n.notification_type == "order_disputed_business_no_payment_confirmation"
    ]
    assert len(dispute_notifications) == 4
    assert {n.recipient_role for n in dispute_notifications if n.recipient_role} == {"admin", "support"}
    assert {n.recipient_user_id for n in dispute_notifications if n.recipient_user_id} == {
        remitter["user"]["id"],
        client.app.state.business_repository.get_business(business["id"]).owner_user_id,
    }


def test_business_response_and_delivery_warnings_are_deduped_with_canonical_audit_events() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_order(client, owner_id=1015, remitter_id=1016)
    _report_payment(client, remitter, order, key="reported_warning")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    now = utc_now()
    client.app.state.order_repository.update_order(
        stored,
        business_response_warning_at=now - timedelta(minutes=1),
        business_response_deadline_at=now + timedelta(hours=1),
    )

    _run_job(client, now)
    _run_job(client, now)

    assert client.app.state.order_repository.get_by_id(order["id"]).status == "payment_reported"
    response_warnings = [
        n for n in client.app.state.job_repository.notification_jobs.values() if n.notification_type == "order_business_response_warning"
    ]
    assert len(response_warnings) == 1
    assert _event_types(client).count("order_business_response_warning_sent") == 1

    _confirm_payment(client, owner, order["id"], "confirm_warning")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    client.app.state.order_repository.update_order(
        stored,
        delivery_warning_at=now - timedelta(minutes=1),
        delivery_deadline_at=now + timedelta(hours=1),
    )

    _run_job(client, now)
    _run_job(client, now)

    delivery_warnings = [n for n in client.app.state.job_repository.notification_jobs.values() if n.notification_type == "order_delivery_warning"]
    assert len(delivery_warnings) == 1
    assert _event_types(client).count("order_delivery_warning_sent") == 1


def test_payment_confirmed_delivery_deadline_opens_dispute_after_credits_consumed() -> None:
    client = _client()
    owner, business, ad, remitter, order = _seed_order(client, owner_id=1020, remitter_id=1021)
    _report_payment(client, remitter, order, key="confirmed_deadline")
    _confirm_payment(client, owner, order["id"], "confirm_deadline")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    past = utc_now() - timedelta(hours=3)
    client.app.state.order_repository.update_order(stored, delivery_deadline_at=past)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])

    _run_job(client, utc_now())

    updated = client.app.state.order_repository.get_by_id(order["id"])
    assert updated.status == "disputed"
    assert updated.dispute_reason == "business_confirmed_payment_but_not_delivered"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "archived"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.consumed_credits == wallet_before.consumed_credits
    assert wallet_after.blocked_credits == wallet_before.blocked_credits
    assert "order_disputed_business_confirmed_payment_but_not_delivered" in _event_types(client)
    dispute_notifications = [
        n
        for n in client.app.state.job_repository.notification_jobs.values()
        if n.notification_type == "order_disputed_business_confirmed_payment_but_not_delivered"
    ]
    assert len(dispute_notifications) == 4
    assert {n.recipient_role for n in dispute_notifications if n.recipient_role} == {"admin", "support"}


def test_delivered_reminders_are_deduped_and_auto_complete_skips_open_dispute() -> None:
    client = _client()
    owner, _, _, remitter, order = _seed_order(client, owner_id=1030, remitter_id=1031)
    _report_payment(client, remitter, order, key="delivered_reminder")
    _confirm_payment(client, owner, order["id"], "confirm_delivered")
    _mark_delivered(client, owner, order["id"], "mark_delivered")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    now = utc_now()
    client.app.state.order_repository.update_order(
        stored,
        delivered_at=now - timedelta(minutes=5),
        auto_complete_warning_12h_at=now + timedelta(hours=1),
        auto_complete_warning_23h_at=now + timedelta(hours=2),
        auto_complete_at=now + timedelta(hours=3),
    )

    _run_job(client, now)
    _run_job(client, now)
    reminders = [item for item in client.app.state.job_repository.notification_jobs.values() if item.notification_type.startswith("delivered_reminder")]
    assert len(reminders) == 1
    assert reminders[0].dedupe_key.endswith(":immediate")
    assert reminders[0].notification_type == "delivered_reminder_immediate"
    assert _event_types(client).count("delivered_reminder_sent") == 1

    client.app.state.order_repository.update_order(stored, auto_complete_warning_12h_at=now - timedelta(minutes=1))
    _run_job(client, now)
    client.app.state.order_repository.update_order(stored, auto_complete_warning_23h_at=now - timedelta(minutes=1))
    _run_job(client, now)
    reminder_types = {item.notification_type for item in client.app.state.job_repository.notification_jobs.values() if item.notification_type.startswith("delivered_reminder")}
    assert {"delivered_reminder_immediate", "delivered_reminder_12h", "delivered_reminder_23h"}.issubset(reminder_types)
    assert _event_types(client).count("delivered_reminder_sent") == 3

    client.app.state.order_repository.update_order(stored, auto_complete_at=now - timedelta(minutes=1))
    _run_job(client, now)
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "completed"
    assert client.app.state.order_repository.get_by_id(order["id"]).completion_reason == "auto_completed_after_24h"
    assert "order_auto_completed_after_24h" in _event_types(client)

    owner2, _, _, remitter2, order2 = _seed_order(client, owner_id=1032, remitter_id=1033)
    _report_payment(client, remitter2, order2, key="delivered_disputed")
    _confirm_payment(client, owner2, order2["id"], "confirm_disputed")
    _mark_delivered(client, owner2, order2["id"], "mark_disputed")
    stored2 = client.app.state.order_repository.get_by_id(order2["id"])
    client.app.state.dispute_repository.create_dispute(
        order_id=order2["id"],
        opened_by_user_id=remitter2["user"]["id"],
        opened_by_role="remitter",
        previous_order_status="delivered",
        reason="payment_mobile_not_received",
        description="No recibido",
    )
    client.app.state.order_repository.update_order(stored2, auto_complete_at=now - timedelta(minutes=1))
    _run_job(client, now)
    assert client.app.state.order_repository.get_by_id(order2["id"]).status == "delivered"


def test_ad_and_founder_expiration_admin_job_endpoints_and_lock_rbac() -> None:
    client = _client()
    owner, business, ad, _, _ = _seed_order(client, owner_id=1040, remitter_id=1041)
    active_ad = client.app.state.ad_repository.get_ad(ad["id"])
    client.app.state.ad_repository.set_status(active_ad, "active")
    active_ad.expires_at = utc_now() - timedelta(days=1)
    stored_business = client.app.state.business_repository.get_business(business["id"])
    stored_business.founder_status = "active"
    stored_business.founder_expires_at = utc_now() - timedelta(days=1)
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    blocked_before = wallet_before.blocked_credits
    consumed_before = wallet_before.consumed_credits

    _run_job(client, utc_now())

    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "archived"
    assert client.app.state.business_repository.get_business(business["id"]).founder_status == "expired"
    assert client.app.state.ad_repository.get_wallet(business["id"]).blocked_credits == blocked_before - 1
    assert client.app.state.ad_repository.get_wallet(business["id"]).consumed_credits == consumed_before + 1
    assert {"ad_expired", "credits_consumed", "founder_access_expired"}.issubset(set(_event_types(client)))
    notification_types = {item.notification_type for item in client.app.state.job_repository.notification_jobs.values()}
    assert {"ad_expired", "founder_access_expired"}.issubset(notification_types)
    assert {"job_started", "job_finished"}.issubset(set(_event_types(client)))

    admin = _login(client, 1042, "admin")
    support = _login(client, 1043, "support")
    business_owner = _login(client, 1044, "business_owner")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")
    client.app.state.user_repository.set_user_role(support["user"]["id"], "support")
    client.app.state.user_repository.set_user_role(business_owner["user"]["id"], "business_owner")
    listing = client.get("/api/v1/admin/jobs/runs?limit=10", headers=_bearer(support, "req_jobs_support"))
    assert listing.status_code == 200, listing.text
    run_id = listing.json()["data"]["items"][0]["id"]
    detail = client.get(f"/api/v1/admin/jobs/runs/{run_id}", headers=_bearer(admin, "req_jobs_admin_detail"))
    forbidden = client.post("/api/v1/admin/jobs/expire-and-escalate-orders/dry-run", headers=_headers(support, "dry_support"))
    owner_forbidden = client.get("/api/v1/admin/jobs/runs", headers=_bearer(business_owner, "req_jobs_owner"))
    assert detail.status_code == 200, detail.text
    assert forbidden.status_code == 403
    assert owner_forbidden.status_code == 403
    combined = listing.text + detail.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert "storage_path" not in combined
    assert "account_value" not in combined
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined

    client.app.state.job_lock_manager.acquire("jobs:expire_and_escalate_orders", "external", 300)
    locked = client.app.state.expire_and_escalate_orders_worker.run(current_time=utc_now(), dry_run=False, request_id="req_locked")
    assert locked["job_run"]["status"] == "lock_not_acquired"
    assert locked["job_run"]["error_code"] == "JOB_LOCK_NOT_ACQUIRED"
    assert "job_failed" in _event_types(client)


def test_slice_10_migration_contract_closes_indexes_constraints_and_canonical_names() -> None:
    root = Path(__file__).resolve().parents[3]
    up = (root / "database" / "migrations" / "0011_slice_10_jobs_notifications.up.sql").read_text(encoding="utf-8")
    down = (root / "database" / "migrations" / "0011_slice_10_jobs_notifications.down.sql").read_text(encoding="utf-8")

    for required in [
        "job_runs_attempts_non_negative_check",
        "job_runs_terminal_finished_at_check",
        "job_runs_failed_error_check",
        "notification_jobs_type_check",
        "notification_jobs_terminal_timestamp_check",
        "job_runs_job_type_status_created_idx",
        "job_runs_lock_key_idx",
        "notification_jobs_order_type_created_idx",
        "notification_jobs_business_type_created_idx",
        "notification_jobs_dispute_type_created_idx",
        "delivered_reminder_immediate",
        "delivered_reminder_12h",
        "delivered_reminder_23h",
    ]:
        assert required in up

    assert "job_name" not in up
    assert "event_type" not in up

    for reversible in [
        "drop index if exists job_runs_lock_key_idx",
        "drop index if exists notification_jobs_dispute_type_created_idx",
        "drop constraint if exists notification_jobs_type_check",
        "drop constraint if exists job_runs_failed_error_check",
    ]:
        assert reversible in down
