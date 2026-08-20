from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode

import pytest
from fastapi.testclient import TestClient

BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"
ROOT = Path(__file__).resolve().parents[3]


def _set_env() -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-45",
        "NODO_BUILD_ID": "pytest-capacity-build",
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
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.core.errors import ApiError  # noqa: E402
from app.main import create_app  # noqa: E402
from app.modules.business_capacity.memory_repository import InMemoryBusinessCapacityRepository  # noqa: E402
from app.modules.business_capacity.models import BusinessCapacityReservationRecord  # noqa: E402
from app.modules.businesses.models import BusinessRecord, utc_now  # noqa: E402
from app.modules.businesses.pin_security import hash_pin  # noqa: E402


def _client() -> TestClient:
    _set_env()
    return TestClient(create_app())


def _signed_init_data(telegram_id: int, username: str) -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps(
            {"id": telegram_id, "username": username, "first_name": username},
            separators=(",", ":"),
            sort_keys=True,
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
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
        headers={
            "Authorization": f"Bearer {login['access_token']}",
            "X-Request-Id": f"req_terms_{telegram_id}",
        },
        json={"terms_version": "2026-07-06"},
    )
    assert terms.status_code == 200, terms.text
    login["user"] = terms.json()["data"]
    return login


def _headers(login: dict, key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key}",
        "Idempotency-Key": key,
    }


def _approved_business(client: TestClient, owner: dict) -> tuple[BusinessRecord, str]:
    repository = client.app.state.business_repository
    created = client.post(
        "/api/v1/businesses",
        headers={
            **_headers(owner, f"business_{owner['user']['id']}"),
            "Content-Type": "application/json",
            "X-NODO-Test-Fixture": "business_create",
        },
        json={
            "business_name": "Casa Capacidad",
            "rif": "J-12345678-9",
            "address": "Av Principal",
            "phone": "+584121234567",
            "country": "VE",
        },
    )
    assert created.status_code == 201, created.text
    business = repository.get_business(created.json()["data"]["business"]["id"])
    assert business is not None
    business.verification_status = "approved"
    business.approved_at = business.updated_at
    business.max_order_amount_usd = Decimal("2000.00")
    user = client.app.state.user_repository.get_user_by_id(owner["user"]["id"])
    link = repository.create_access_link(
        business_id=business.id,
        user_id=owner["user"]["id"],
        telegram_id_snapshot=user.telegram_id,
        role_in_business="owner",
        linked_by_admin_id=owner["user"]["id"],
        reason="slice_45_test",
    )
    repository.set_access_link_pin_hash(link_id=link.id, pin_hash=hash_pin("1234"))
    repository.mark_access_link_pin_verified(
        link_id=link.id,
        unlocked_until=utc_now() + timedelta(minutes=15),
    )
    payment = repository.add_payment_method(
        business_id=business.id,
        method_type="zelle",
        network=None,
        account_value="owner@example.com",
        account_masked="ow***@example.com",
        holder_name="Owner Test",
    )
    payment.verified_status = "approved"
    payment.active = True
    client.app.state.ad_repository.grant_test_credits(
        business_id=business.id,
        amount=5,
        created_by=owner["user"]["id"],
    )
    return business, payment.id


def _create_ad(
    client: TestClient,
    owner: dict,
    payment_method_id: str,
    key: str,
    *,
    amount_min_usd: str = "20.00",
    amount_max_usd: str = "100.00",
    payment_method: str = "zelle",
) -> dict:
    response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment_method_id,
            "payment_method": payment_method,
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": amount_min_usd,
            "amount_max_usd": amount_max_usd,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["ad"]


def _add_approved_usdt_method(client: TestClient, *, business_id: str, suffix: str) -> str:
    method = client.app.state.business_repository.add_payment_method(
        business_id=business_id,
        method_type="usdt_trc20",
        network="trc20",
        account_value=f"T{suffix}WalletAddress",
        account_masked=f"T{suffix[:4]}...ress",
        holder_name="Owner Test",
    )
    method.verified_status = "approved"
    method.active = True
    return method.id


def _create_order(client: TestClient, remitter: dict, ad_id: str, amount: str, key: str):
    return client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, key), "Content-Type": "application/json"},
        json={
            "ad_id": ad_id,
            "amount_usd": amount,
            "receiver_data": {
                "bank": "Banco",
                "phone": "+584121234567",
                "document": "V12345678",
                "holder": "Receptor Test",
            },
        },
    )


def test_unconfigured_business_capacity_defaults_to_zero() -> None:
    repository = InMemoryBusinessCapacityRepository()
    business = BusinessRecord(
        id="business-1",
        owner_user_id="owner-1",
        business_name="Casa Uno",
        rif=None,
        address=None,
        phone=None,
        country="VE",
        verification_status="approved",
        is_accepting_orders=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )

    snapshot = repository.get_snapshot(business=business)

    assert snapshot.declared_available_capacity_usd == Decimal("0.00")
    assert snapshot.reserved_capacity_usd == Decimal("0.00")
    assert snapshot.effective_available_capacity_usd == Decimal("0.00")


def test_business_can_update_capacity_but_not_below_reserved() -> None:
    client = _client()
    owner = _login(client, 45001, "capacity_owner")
    business, _ = _approved_business(client, owner)
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("40.00"),
        actor_user_id=owner["user"]["id"],
    )
    client.app.state.capacity_repository.reserve(
        order_id="00000000-0000-0000-0000-000000000451",
        business=business,
        amount_usd=Decimal("30.00"),
        reason="order_created",
    )

    rejected = client.put(
        "/api/v1/business/capacity",
        headers={**_headers(owner, "capacity_too_low"), "Content-Type": "application/json"},
        json={
            "availability_status": "online",
            "declared_available_capacity_usd": "20.00",
        },
    )
    accepted = client.put(
        "/api/v1/business/capacity",
        headers={**_headers(owner, "capacity_valid"), "Content-Type": "application/json"},
        json={
            "availability_status": "online",
            "declared_available_capacity_usd": "50.00",
        },
    )

    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "BUSINESS_CAPACITY_BELOW_RESERVED"
    assert accepted.status_code == 200
    assert accepted.json()["data"]["declared_available_capacity_usd"] == "50.00"
    assert accepted.json()["data"]["reserved_capacity_usd"] == "30.00"
    assert accepted.json()["data"]["effective_available_capacity_usd"] == "20.00"
    assert accepted.json()["data"]["daily_limit_usd"] == "1000.00"
    assert accepted.json()["data"]["daily_reserved_usd"] == "30.00"
    assert accepted.json()["data"]["daily_consumed_usd"] == "0.00"
    assert accepted.json()["data"]["daily_remaining_usd"] == "970.00"
    assert accepted.json()["data"]["daily_window"]["timezone"] == "UTC"
    assert accepted.json()["data"]["capabilities"]["daily_limit_reached"] is False
    assert "updated_by_user_id" not in accepted.json()["data"]


def test_marketplace_filters_capacity_and_does_not_expose_exact_amounts() -> None:
    client = _client()
    owner = _login(client, 45002, "market_owner")
    remitter = _login(client, 45003, "market_remitter")
    business, payment_method_id = _approved_business(client, owner)
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("40.00"),
        actor_user_id=owner["user"]["id"],
    )
    ad = _create_ad(
        client,
        owner,
        payment_method_id,
        "capacity_ad",
        amount_max_usd="40.00",
    )

    covered = client.get(
        "/api/v1/ads/search?amount_usd=30.00&limit=20",
        headers={"Authorization": f"Bearer {remitter['access_token']}", "X-Request-Id": "req_cover"},
    )
    not_covered = client.get(
        "/api/v1/ads/search?amount_usd=80.00&limit=20",
        headers={"Authorization": f"Bearer {remitter['access_token']}", "X-Request-Id": "req_no_cover"},
    )
    no_requested_amount = client.get(
        "/api/v1/ads/search?limit=20",
        headers={"Authorization": f"Bearer {remitter['access_token']}", "X-Request-Id": "req_no_requested_amount"},
    )

    assert covered.status_code == 200
    assert [item["id"] for item in covered.json()["data"]["items"]] == [ad["id"]]
    availability = covered.json()["data"]["items"][0]["business"]["availability"]
    assert availability["can_cover_requested_amount"] is True
    serialized = json.dumps(covered.json())
    for private_field in {
        "daily_limit_usd",
        "daily_reserved_usd",
        "daily_consumed_usd",
        "daily_remaining_usd",
        "declared_available_capacity_usd",
        "reserved_capacity_usd",
        "effective_available_capacity_usd",
        "risk_level",
        "trust_level",
    }:
        assert private_field not in serialized
    assert not_covered.status_code == 200
    assert not_covered.json()["data"]["items"] == []
    assert no_requested_amount.status_code == 200
    assert "can_cover_requested_amount" not in no_requested_amount.json()["data"]["items"][0]["business"]["availability"]


def test_admin_can_view_and_adjust_exact_operational_capacity() -> None:
    client = _client()
    owner = _login(client, 45010, "admin_capacity_owner")
    admin = _login(client, 45011, "capacity_admin")
    outsider = _login(client, 45012, "capacity_outsider")
    business, _ = _approved_business(client, owner)
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "admin")

    denied = client.get(
        f"/api/v1/admin/businesses/{business.id}/capacity",
        headers=_headers(outsider, "capacity_admin_denied"),
    )
    updated = client.put(
        f"/api/v1/admin/businesses/{business.id}/capacity",
        headers={
            **_headers(admin, "capacity_admin_update"),
            "Content-Type": "application/json",
        },
        json={
            "declared_available_capacity_usd": "80.00",
            "reason": "Ajuste operativo de prueba",
        },
    )
    assert denied.status_code == 403
    assert updated.status_code == 200, updated.text
    client.app.state.capacity_repository.reserve(
        order_id="00000000-0000-0000-0000-000000000452",
        business=business,
        amount_usd=Decimal("20.00"),
        reason="order_created",
    )
    viewed = client.get(
        f"/api/v1/admin/businesses/{business.id}/capacity",
        headers=_headers(admin, "capacity_admin_view_with_daily"),
    )
    assert viewed.status_code == 200, viewed.text
    assert viewed.headers["cache-control"] == "private, no-store"
    assert viewed.json()["data"]["declared_available_capacity_usd"] == "80.00"
    assert viewed.json()["data"]["reserved_capacity_usd"] == "20.00"
    assert viewed.json()["data"]["daily_reserved_usd"] == "20.00"
    assert viewed.json()["data"]["daily_consumed_usd"] == "0.00"
    assert viewed.json()["data"]["daily_remaining_usd"] == "980.00"
    assert viewed.json()["data"]["daily_orders"] == [
        {
            "order_id": "00000000-0000-0000-0000-000000000452",
            "amount_usd": "20.00",
            "capacity_status": "reserved",
            "created_at": viewed.json()["data"]["daily_orders"][0]["created_at"],
            "consumed_at": None,
        }
    ]
    assert viewed.json()["data"]["daily_orders_truncated"] is False
    assert viewed.json()["data"]["updated_by_user_id"] == admin["user"]["id"]


def test_create_order_reserves_and_idempotency_does_not_duplicate() -> None:
    client = _client()
    owner = _login(client, 45004, "reserve_owner")
    remitter = _login(client, 45005, "reserve_remitter")
    business, payment_method_id = _approved_business(client, owner)
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("40.00"),
        actor_user_id=owner["user"]["id"],
    )
    ad = _create_ad(
        client,
        owner,
        payment_method_id,
        "reserve_ad",
        amount_max_usd="40.00",
    )

    first = _create_order(client, remitter, ad["id"], "30.00", "reserve_order")
    replay = _create_order(client, remitter, ad["id"], "30.00", "reserve_order")
    snapshot = client.app.state.capacity_repository.get_snapshot(business=business)

    assert first.status_code == 201, first.text
    assert replay.status_code == 201, replay.text
    assert first.json()["data"]["order"]["id"] == replay.json()["data"]["order"]["id"]
    assert snapshot.reserved_capacity_usd == Decimal("30.00")
    assert len(client.app.state.capacity_repository.reservations) == 1


def test_active_order_limit_counts_all_open_obligations() -> None:
    client = _client()
    owner = _login(client, 45015, "active_limit_owner")
    remitter = _login(client, 45016, "active_limit_remitter")
    business, payment_method_id = _approved_business(client, owner)
    business.active_order_limit = 1
    usdt_method_id = _add_approved_usdt_method(
        client,
        business_id=business.id,
        suffix="ActiveLimit",
    )
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("200.00"),
        actor_user_id=owner["user"]["id"],
    )
    first_ad = _create_ad(
        client,
        owner,
        payment_method_id,
        "active_limit_first_ad",
        amount_min_usd="20.00",
        amount_max_usd="40.00",
    )
    first_order = _create_order(
        client,
        remitter,
        first_ad["id"],
        "30.00",
        "active_limit_first_order",
    ).json()["data"]["order"]
    stored_order = client.app.state.order_repository.get_by_id(first_order["id"])
    client.app.state.order_repository.update_order(stored_order, status="payment_reported")
    second_ad = _create_ad(
        client,
        owner,
        usdt_method_id,
        "active_limit_second_ad",
        amount_min_usd="50.00",
        amount_max_usd="70.00",
        payment_method="usdt_trc20",
    )

    second_order = _create_order(
        client,
        remitter,
        second_ad["id"],
        "60.00",
        "active_limit_second_order",
    )

    assert second_order.status_code == 409
    assert second_order.json()["error"]["code"] == "AD_NOT_AVAILABLE"


def test_order_lifecycle_releases_keeps_or_consumes_capacity_once() -> None:
    client = _client()
    owner = _login(client, 45006, "lifecycle_owner")
    remitter = _login(client, 45007, "lifecycle_remitter")
    business, payment_method_id = _approved_business(client, owner)
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("60.00"),
        actor_user_id=owner["user"]["id"],
    )

    cancel_ad = _create_ad(
        client,
        owner,
        payment_method_id,
        "cancel_capacity_ad",
        amount_min_usd="20.00",
        amount_max_usd="40.00",
    )
    cancelled_order = _create_order(
        client,
        remitter,
        cancel_ad["id"],
        "20.00",
        "cancel_capacity_order",
    ).json()["data"]["order"]
    cancelled = client.post(
        f"/api/v1/orders/{cancelled_order['id']}/cancel",
        headers=_headers(remitter, "cancel_capacity"),
        json={"reason": "customer_mistake"},
    )
    assert cancelled.status_code == 200, cancelled.text
    assert client.app.state.capacity_repository.get_reservation(cancelled_order["id"]).status == "released"
    client.app.state.ad_repository.set_status(
        client.app.state.ad_repository.get_ad(cancel_ad["id"]),
        "paused",
    )

    completed_ad = _create_ad(
        client,
        owner,
        payment_method_id,
        "completed_capacity_ad",
        amount_min_usd="50.00",
        amount_max_usd="60.00",
    )
    completed_order = _create_order(
        client,
        remitter,
        completed_ad["id"],
        "50.00",
        "completed_capacity_order",
    ).json()["data"]["order"]
    stored_order = client.app.state.order_repository.get_by_id(completed_order["id"])
    client.app.state.order_repository.update_order(
        stored_order,
        status="disputed",
        dispute_reason="test_dispute",
    )
    assert client.app.state.capacity_repository.get_reservation(completed_order["id"]).status == "reserved"
    client.app.state.order_repository.update_order(
        stored_order,
        status="completed",
        completion_reason="admin_resolved",
        completed_at=utc_now(),
        capacity_event_context={
            "actor_user_id": owner["user"]["id"],
            "actor_role": "admin",
            "request_id": "req_capacity_complete",
            "reason": "admin_resolved",
        },
    )
    client.app.state.order_repository.update_order(
        stored_order,
        status="completed",
        capacity_event_context={
            "actor_user_id": owner["user"]["id"],
            "actor_role": "admin",
            "request_id": "req_capacity_complete_replay",
            "reason": "admin_resolved",
        },
    )
    snapshot = client.app.state.capacity_repository.get_snapshot(business=business)

    assert client.app.state.capacity_repository.get_reservation(completed_order["id"]).status == "consumed"
    assert snapshot.declared_available_capacity_usd == Decimal("10.00")
    assert snapshot.reserved_capacity_usd == Decimal("0.00")
    assert [
        event.event_type
        for event in client.app.state.audit_writer.events
        if event.event_type == "business_capacity_consumed"
    ] == ["business_capacity_consumed"]


def test_expired_order_releases_capacity_once() -> None:
    client = _client()
    owner = _login(client, 45013, "expiry_capacity_owner")
    remitter = _login(client, 45014, "expiry_capacity_remitter")
    business, payment_method_id = _approved_business(client, owner)
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("40.00"),
        actor_user_id=owner["user"]["id"],
    )
    ad = _create_ad(
        client,
        owner,
        payment_method_id,
        "expiry_capacity_ad",
        amount_max_usd="40.00",
    )
    order = _create_order(
        client,
        remitter,
        ad["id"],
        "20.00",
        "expiry_capacity_order",
    ).json()["data"]["order"]
    stored_order = client.app.state.order_repository.get_by_id(order["id"])
    stored_order.payment_report_deadline_at = utc_now() - timedelta(seconds=1)
    stored_order.expires_at = stored_order.payment_report_deadline_at

    materialized = client.get(
        f"/api/v1/orders/{order['id']}",
        headers=_headers(remitter, "expiry_capacity_materialize"),
    )
    replay = client.get(
        f"/api/v1/orders/{order['id']}",
        headers=_headers(remitter, "expiry_capacity_replay"),
    )

    assert materialized.status_code == 200, materialized.text
    assert materialized.json()["data"]["order"]["status"] == "cancelled"
    assert replay.status_code == 200
    assert client.app.state.capacity_repository.get_reservation(order["id"]).status == "released"
    assert client.app.state.capacity_repository.get_snapshot(
        business=business
    ).effective_available_capacity_usd == Decimal("40.00")
    assert [
        event.event_type
        for event in client.app.state.audit_writer.events
        if event.event_type == "business_capacity_released"
    ] == ["business_capacity_released"]


def test_create_order_above_effective_capacity_returns_specific_error() -> None:
    client = _client()
    owner = _login(client, 45008, "insufficient_owner")
    remitter = _login(client, 45009, "insufficient_remitter")
    business, payment_method_id = _approved_business(client, owner)
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("100.00"),
        actor_user_id=owner["user"]["id"],
    )
    ad = _create_ad(client, owner, payment_method_id, "insufficient_ad")
    client.app.state.capacity_repository.reserve(
        order_id="capacity-preexisting-reservation",
        business=business,
        amount_usd=Decimal("75.00"),
        reason="test_existing_obligation",
    )

    response = _create_order(
        client,
        remitter,
        ad["id"],
        "30.00",
        "insufficient_order",
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "BUSINESS_CAPACITY_INSUFFICIENT"
    assert set(client.app.state.capacity_repository.reservations) == {
        "capacity-preexisting-reservation"
    }


def test_two_concurrent_reservations_cannot_spend_same_capacity() -> None:
    repository = InMemoryBusinessCapacityRepository()
    business = BusinessRecord(
        id="business-race",
        owner_user_id="owner-race",
        business_name="Casa Race",
        rif=None,
        address=None,
        phone=None,
        country="VE",
        verification_status="approved",
        is_accepting_orders=True,
        daily_limit_usd=Decimal("1000.00"),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("40.00"),
        actor_user_id=business.owner_user_id,
    )

    def reserve(order_id: str) -> str:
        try:
            repository.reserve(
                order_id=order_id,
                business=business,
                amount_usd=Decimal("30.00"),
                reason="order_created",
            )
            return "reserved"
        except ApiError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, ["order-a", "order-b"]))

    assert sorted(results) == ["BUSINESS_CAPACITY_INSUFFICIENT", "reserved"]
    assert repository.get_snapshot(business=business).reserved_capacity_usd == Decimal("30.00")


def test_slice_49a_concurrent_orders_revalidate_active_limit_inside_final_write() -> None:
    client = _client()
    owner = _login(client, 45017, "active_limit_race_owner")
    first_remitter = _login(client, 45018, "active_limit_race_first")
    second_remitter = _login(client, 45019, "active_limit_race_second")
    business, payment_method_id = _approved_business(client, owner)
    business.active_order_limit = 1
    usdt_method_id = _add_approved_usdt_method(
        client,
        business_id=business.id,
        suffix="ActiveLimitRace",
    )
    client.app.state.capacity_repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("200.00"),
        actor_user_id=owner["user"]["id"],
    )
    first_ad = _create_ad(
        client,
        owner,
        payment_method_id,
        "active_limit_race_first_ad",
        amount_min_usd="20.00",
        amount_max_usd="40.00",
    )
    second_ad = _create_ad(
        client,
        owner,
        usdt_method_id,
        "active_limit_race_second_ad",
        amount_min_usd="50.00",
        amount_max_usd="70.00",
        payment_method="usdt_trc20",
    )

    def create(args: tuple[dict, str, str, str]):  # type: ignore[no-untyped-def]
        remitter, ad_id, amount, key = args
        response = _create_order(client, remitter, ad_id, amount, key)
        return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                create,
                [
                    (first_remitter, first_ad["id"], "30.00", "active_limit_race_first"),
                    (second_remitter, second_ad["id"], "60.00", "active_limit_race_second"),
                ],
            )
        )

    assert sorted(status for status, _ in results) == [201, 409]
    rejected = next(body for status, body in results if status == 409)
    assert rejected["error"]["code"] == "AD_NOT_AVAILABLE"
    assert client.app.state.order_repository.count_active_for_business(business.id) == 1
    assert len(client.app.state.capacity_repository.reservations) == 1


def test_daily_limit_caps_gross_order_reservations_not_ad_ranges() -> None:
    repository = InMemoryBusinessCapacityRepository()
    business = BusinessRecord(
        id="business-daily",
        owner_user_id="owner-daily",
        business_name="Casa Daily",
        rif=None,
        address=None,
        phone=None,
        country="VE",
        verification_status="approved",
        is_accepting_orders=True,
        daily_limit_usd=Decimal("50.00"),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("100.00"),
        actor_user_id=business.owner_user_id,
    )
    repository.reserve(
        order_id="00000000-0000-0000-0000-000000000461",
        business=business,
        amount_usd=Decimal("30.00"),
        reason="order_created",
    )

    with pytest.raises(ApiError) as caught:
        repository.reserve(
            order_id="00000000-0000-0000-0000-000000000462",
            business=business,
            amount_usd=Decimal("30.00"),
            reason="order_created",
        )

    assert caught.value.code == "BUSINESS_DAILY_LIMIT_EXCEEDED"


def test_open_reservation_created_yesterday_counts_against_today() -> None:
    repository = InMemoryBusinessCapacityRepository()
    now = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
    business = BusinessRecord(
        id="business-carryover",
        owner_user_id="owner-carryover",
        business_name="Casa Carryover",
        rif=None,
        address=None,
        phone=None,
        country="VE",
        verification_status="approved",
        is_accepting_orders=True,
        daily_limit_usd=Decimal("1000.00"),
        created_at=now,
        updated_at=now,
    )
    repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("1000.00"),
        actor_user_id=business.owner_user_id,
    )
    repository.reservations["order-carryover"] = BusinessCapacityReservationRecord(
        id="reservation-carryover",
        order_id="order-carryover",
        business_id=business.id,
        amount_usd=Decimal("300.00"),
        status="reserved",
        reason="order_created",
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(days=1),
    )

    snapshot = repository.get_snapshot(business=business, now=now)

    assert snapshot.daily_reserved_usd == Decimal("300.00")
    assert snapshot.daily_consumed_usd == Decimal("0.00")
    assert snapshot.daily_remaining_usd == Decimal("700.00")
    assert snapshot.daily_window_starts_at == datetime(2026, 7, 27, tzinfo=timezone.utc)
    assert snapshot.daily_window_ends_at == datetime(2026, 7, 28, tzinfo=timezone.utc)


def test_reservation_created_yesterday_and_consumed_today_counts_today() -> None:
    repository = InMemoryBusinessCapacityRepository()
    now = datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
    business = BusinessRecord(
        id="business-consumed-today",
        owner_user_id="owner-consumed-today",
        business_name="Casa Consumed Today",
        rif=None,
        address=None,
        phone=None,
        country="VE",
        verification_status="approved",
        is_accepting_orders=True,
        daily_limit_usd=Decimal("1000.00"),
        created_at=now,
        updated_at=now,
    )
    repository.reservations["order-consumed-today"] = BusinessCapacityReservationRecord(
        id="reservation-consumed-today",
        order_id="order-consumed-today",
        business_id=business.id,
        amount_usd=Decimal("250.00"),
        status="consumed",
        reason="completed",
        created_at=now - timedelta(days=1),
        updated_at=now - timedelta(hours=1),
        consumed_at=now - timedelta(hours=1),
    )

    snapshot = repository.get_snapshot(business=business, now=now)

    assert snapshot.daily_reserved_usd == Decimal("0.00")
    assert snapshot.daily_consumed_usd == Decimal("250.00")
    assert snapshot.daily_remaining_usd == Decimal("750.00")


def test_released_reservation_does_not_consume_daily_limit() -> None:
    repository = InMemoryBusinessCapacityRepository()
    business = BusinessRecord(
        id="business-daily-release",
        owner_user_id="owner-daily-release",
        business_name="Casa Daily Release",
        rif=None,
        address=None,
        phone=None,
        country="VE",
        verification_status="approved",
        is_accepting_orders=True,
        daily_limit_usd=Decimal("50.00"),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("100.00"),
        actor_user_id=business.owner_user_id,
    )
    repository.reserve(
        order_id="00000000-0000-0000-0000-000000000463",
        business=business,
        amount_usd=Decimal("30.00"),
        reason="order_created",
    )
    assert repository.release(
        order_id="00000000-0000-0000-0000-000000000463",
        reason="remitter_cancelled_before_payment",
    ) is True

    snapshot = repository.get_snapshot(business=business)
    repository.reserve(
        order_id="00000000-0000-0000-0000-000000000464",
        business=business,
        amount_usd=Decimal("30.00"),
        reason="order_created",
    )

    assert snapshot.daily_reserved_usd == Decimal("0.00")
    assert snapshot.daily_consumed_usd == Decimal("0.00")
    assert repository.get_snapshot(business=business).daily_reserved_usd == Decimal("30.00")


def test_release_and_consume_are_idempotent_and_consumption_reduces_declared() -> None:
    repository = InMemoryBusinessCapacityRepository()
    business = BusinessRecord(
        id="business-lifecycle",
        owner_user_id="owner-lifecycle",
        business_name="Casa Lifecycle",
        rif=None,
        address=None,
        phone=None,
        country="VE",
        verification_status="approved",
        is_accepting_orders=True,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("60.00"),
        actor_user_id=business.owner_user_id,
    )
    repository.reserve(
        order_id="order-released",
        business=business,
        amount_usd=Decimal("20.00"),
        reason="order_created",
    )
    assert repository.release(order_id="order-released", reason="cancelled") is True
    assert repository.release(order_id="order-released", reason="cancelled") is False

    repository.reserve(
        order_id="order-consumed",
        business=business,
        amount_usd=Decimal("30.00"),
        reason="order_created",
    )
    assert repository.consume(order_id="order-consumed", reason="completed") is True
    assert repository.consume(order_id="order-consumed", reason="completed") is False
    snapshot = repository.get_snapshot(business=business)

    assert snapshot.declared_available_capacity_usd == Decimal("30.00")
    assert snapshot.reserved_capacity_usd == Decimal("0.00")
    assert snapshot.effective_available_capacity_usd == Decimal("30.00")
    assert snapshot.daily_reserved_usd == Decimal("0.00")
    assert snapshot.daily_consumed_usd == Decimal("30.00")


def test_concurrent_orders_compete_for_last_daily_capacity() -> None:
    repository = InMemoryBusinessCapacityRepository()
    business = BusinessRecord(
        id="business-daily-race",
        owner_user_id="owner-daily-race",
        business_name="Casa Daily Race",
        rif=None,
        address=None,
        phone=None,
        country="VE",
        verification_status="approved",
        is_accepting_orders=True,
        daily_limit_usd=Decimal("50.00"),
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    repository.set_declared_capacity(
        business_id=business.id,
        amount_usd=Decimal("100.00"),
        actor_user_id=business.owner_user_id,
    )

    def reserve(order_id: str) -> str:
        try:
            repository.reserve(
                order_id=order_id,
                business=business,
                amount_usd=Decimal("30.00"),
                reason="order_created",
            )
            return "reserved"
        except ApiError as exc:
            return exc.code

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reserve, ["daily-order-a", "daily-order-b"]))

    assert sorted(results) == ["BUSINESS_DAILY_LIMIT_EXCEEDED", "reserved"]
    snapshot = repository.get_snapshot(business=business)
    assert snapshot.daily_reserved_usd == Decimal("30.00")
    assert snapshot.daily_remaining_usd == Decimal("20.00")


def test_migration_and_frontend_contracts_are_safe() -> None:
    migration = (ROOT / "database/migrations/0035_business_available_capacity_matching.up.sql").read_text()
    down = (ROOT / "database/migrations/0035_business_available_capacity_matching.down.sql").read_text()
    presenter = (ROOT / "apps/api/app/modules/ads/presenters.py").read_text()
    client_orders = (ROOT / "apps/web/src/hooks/workspace/useRemitterOrdersModel.ts").read_text()
    business_capacity_hook = (
        ROOT
        / "apps/web/src/hooks/business-mini-app/useBusinessCapacityModel.ts"
    ).read_text()
    business_access_model = (
        ROOT / "apps/web/src/hooks/business-mini-app/useBusinessAccessModel.ts"
    ).read_text()
    business_dashboard = (
        ROOT / "apps/web/src/screens/business-app/BusinessDashboardScreen.tsx"
    ).read_text()
    admin_businesses = (
        ROOT / "apps/web/src/screens/admin-web/AdminBusinessScreens.tsx"
    ).read_text()

    assert "numeric(12,2)" in migration
    assert "business_capacity_reservations_order_id_key" in migration
    assert "where status = 'reserved'" in migration
    assert "drop table if exists business_capacity_reservations" in down
    assert "can_cover_requested_amount" in presenter
    assert "BUSINESS_CAPACITY_INSUFFICIENT" in client_orders
    assert "getBusinessCapacity" in business_capacity_hook
    assert "savingBusinessCapacity" in business_capacity_hook
    assert "syncBusinessAvailability(data.availability_status)" in business_capacity_hook
    assert "businessCapacity?.availability_status" in business_capacity_hook
    assert "setBusiness:" in business_capacity_hook
    assert "setBusiness," in business_access_model
    assert "Reservado activo" in business_dashboard
    assert "Consumido hoy" in business_dashboard
    assert "Reinicio diario: 00:00 UTC" in business_dashboard
    assert "Reservado activo" in admin_businesses
    assert "Consumido hoy" in admin_businesses
    assert "Ordenes que explican el limite diario" in admin_businesses
    assert "float" not in migration.casefold()
    postgres_create = (
        ROOT / "apps/api/app/modules/orders/postgres_create_order.py"
    ).read_text()
    postgres_marketplace = (
        ROOT / "apps/api/app/modules/ads/postgres_repository.py"
    ).read_text()
    postgres_capacity = (
        ROOT / "apps/api/app/modules/business_capacity/postgres_repository.py"
    ).read_text()
    assert "reserve_in_transaction" in postgres_create
    assert postgres_create.index("reserve_in_transaction") < postgres_create.index("conn.commit()")
    active_order_count_sql = postgres_create.split("select count(*)", 1)[1].split(
        ") as active_order_count",
        1,
    )[0]
    assert "'payment_reported'" in active_order_count_sql
    assert "'payment_confirmed'" in active_order_count_sql
    assert "'disputed'" in active_order_count_sql
    optimized_query = postgres_marketplace.split(
        "def list_marketplace_ads_with_businesses", 1
    )[1].split("def list_business_ads", 1)[0]
    assert "left join lateral" in optimized_query
    assert "where business_id = businesses.id" in optimized_query
    assert "business_capacity_reservations" in optimized_query
    assert "consumed_at >=" in optimized_query
    assert "status = 'reserved'" in optimized_query
    assert optimized_query.index("business_capacity_reservations") < optimized_query.index("limit %s")
    snapshot_query = postgres_capacity.split("def get_snapshot", 1)[1].split(
        "def set_declared_capacity",
        1,
    )[0]
    assert "reservation.consumed_at >=" in snapshot_query
    assert "reservation.status = 'reserved'" in snapshot_query
    assert "reservation.created_at >=" not in snapshot_query


def test_daily_limit_index_migration_supports_consumed_at_queries() -> None:
    migration = (
        ROOT / "database/migrations/0036_business_daily_limit_query_indexes.up.sql"
    ).read_text().casefold()
    down = (
        ROOT / "database/migrations/0036_business_daily_limit_query_indexes.down.sql"
    ).read_text().casefold()

    assert "business_capacity_reservations_consumed_daily_idx" in migration
    assert "on business_capacity_reservations (business_id, consumed_at)" in migration
    assert "where status = 'consumed'" in migration
    assert "consumed_at is not null" in migration
    assert "include (amount_usd, order_id, created_at)" in migration
    assert "drop index if exists business_capacity_reservations_consumed_daily_idx" in down
