from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlencode
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.modules.businesses.models import BusinessRecord
from app.modules.businesses.presenters import business_payload
from app.modules.notifications.attention import BUSINESS_ORDER_ATTENTION_STATUSES, CLIENT_ORDER_ATTENTION_STATUSES
from app.modules.notifications.notification_types import TELEGRAM_NOTIFICATION_TYPES
from app.modules.orders import ratings_repository as ratings_repository_module
from app.modules.orders.models import OrderRecord, utc_now
from app.modules.orders.serializers import business_order_payload


BOT_TOKEN = "123456:test-bot-token"
ROOT = Path(__file__).resolve().parents[3]


def _set_env() -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-42b",
        "NODO_BUILD_ID": "pytest-order-ratings-build",
        "DATABASE_URL": "postgresql://127.0.0.1:1/nodo",
        "REDIS_URL": "redis://127.0.0.1:1/0",
        "API_CORS_ORIGINS": "http://localhost:3000",
        "BOT_TOKEN": BOT_TOKEN,
        "JWT_SECRET": "test-access-secret",
        "JWT_REFRESH_SECRET": "test-refresh-secret",
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

from app.main import create_app  # noqa: E402


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
    return response.json()["data"]


def _headers(login: dict, key: str | None = "rating") -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {login['access_token']}",
        "X-Request-Id": f"req_{key or 'missing'}",
        "Content-Type": "application/json",
    }
    if key is not None:
        headers["Idempotency-Key"] = key
    return headers


def _login_as(client: TestClient, telegram_id: int, username: str, role: str) -> dict:
    first = _login(client, telegram_id, username)
    user = client.app.state.user_repository.get_user_by_id(first["user"]["id"])
    user.role = role
    return _login(client, telegram_id, username)


def _seed_completed_order(
    client: TestClient,
    *,
    telegram_id: int = 42001,
    completion_reason: str | None = "manual_confirmed",
) -> tuple[dict, BusinessRecord, OrderRecord]:
    remitter = _login(client, telegram_id, f"remitter_{telegram_id}")
    business = BusinessRecord(
        id=str(uuid4()),
        owner_user_id=str(uuid4()),
        business_name="Casa Rating",
        rif=None,
        address=None,
        phone=None,
        verification_status="approved",
        trust_level="pro",
        risk_level="under_review",
    )
    client.app.state.business_repository.businesses[business.id] = business
    order = _seed_completed_order_for_business(
        client,
        remitter=remitter,
        business=business,
        completion_reason=completion_reason,
    )
    return remitter, business, order


def _seed_completed_order_for_business(
    client: TestClient,
    *,
    remitter: dict,
    business: BusinessRecord,
    completion_reason: str | None = "manual_confirmed",
) -> OrderRecord:
    now = utc_now()
    order = OrderRecord(
        id=str(uuid4()),
        public_order_code=f"NODO-{str(uuid4())[:8].upper()}",
        ad_id=str(uuid4()),
        business_id=business.id,
        remitter_user_id=remitter["user"]["id"],
        status="completed",
        idempotency_key=f"seed_{uuid4()}",
        amount_usd=Decimal("50.00"),
        rate_snapshot=Decimal("40.00"),
        amount_bs_calculated=Decimal("2000.00"),
        business_name_snapshot=business.business_name,
        payment_method_snapshot="zelle",
        delivery_method_snapshot="pago_movil_ve",
        min_amount_snapshot=Decimal("20.00"),
        max_amount_snapshot=Decimal("100.00"),
        payment_instructions_snapshot={"method_type": "zelle", "account_masked": "***.com"},
        receiver_data_json={"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Cliente"},
        payment_report_deadline_at=now + timedelta(minutes=30),
        expires_at=now + timedelta(minutes=30),
        completion_reason=completion_reason,
        payment_confirmed_at=now - timedelta(minutes=10),
        delivered_at=now - timedelta(minutes=1),
        completed_at=now,
    )
    client.app.state.order_repository.orders[order.id] = order
    return order


def _post_rating(client: TestClient, login: dict, order_id: str, stars: object, key: str | None = "rating"):
    return client.post(
        f"/api/v1/orders/{order_id}/rating",
        headers=_headers(login, key),
        json={"stars": stars},
    )


@pytest.mark.parametrize("stars", [1, 2, 3, 4, 5])
def test_every_valid_rating_starts_fifteen_minute_publication_pause(stars: int) -> None:
    client = _client()
    remitter, business, order = _seed_completed_order(client, telegram_id=42400 + stars)
    started_at = utc_now()

    response = _post_rating(client, remitter, order.id, stars, f"pause_{stars}")

    finished_at = utc_now()
    assert response.status_code == 201, response.text
    stored = client.app.state.business_repository.get_business(business.id)
    assert stored.ad_publication_paused_until is not None
    assert started_at + timedelta(minutes=15) <= stored.ad_publication_paused_until
    assert stored.ad_publication_paused_until <= finished_at + timedelta(minutes=15)
    assert "ad_publication_paused_until" not in response.text
    assert "business_publication_pause" not in response.text


def test_rating_replay_does_not_extend_publication_pause_or_duplicate_audit() -> None:
    client = _client()
    remitter, business, order = _seed_completed_order(client, telegram_id=42410)

    first = _post_rating(client, remitter, order.id, 4, "pause_replay")
    first_pause = client.app.state.business_repository.get_business(business.id).ad_publication_paused_until
    replay = _post_rating(client, remitter, order.id, 4, "pause_replay")

    assert first.status_code == replay.status_code == 201
    assert client.app.state.business_repository.get_business(business.id).ad_publication_paused_until == first_pause
    pause_events = [
        event
        for event in client.app.state.audit_writer.events
        if event.event_type == "business_publication_pause_started"
    ]
    assert len(pause_events) == 1
    assert pause_events[0].actor_user_id is None
    assert pause_events[0].actor_role is None
    assert pause_events[0].resource_type == "business"
    assert pause_events[0].resource_id == business.id
    assert pause_events[0].metadata_json is None


def test_second_distinct_rating_uses_later_publication_pause_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _client()
    first_remitter, business, first_order = _seed_completed_order(client, telegram_id=42420)
    second_remitter = _login(client, 42421, "remitter_42421")
    second_order = _seed_completed_order_for_business(
        client,
        remitter=second_remitter,
        business=business,
    )
    first_time = utc_now()
    second_time = first_time + timedelta(minutes=2)
    times = iter((first_time, second_time))
    monkeypatch.setattr(ratings_repository_module, "utc_now", lambda: next(times))

    first = _post_rating(client, first_remitter, first_order.id, 5, "first_business_pause")
    second = _post_rating(client, second_remitter, second_order.id, 5, "second_business_pause")

    assert first.status_code == second.status_code == 201
    stored = client.app.state.business_repository.get_business(business.id)
    assert stored.ad_publication_paused_until == second_time + timedelta(minutes=15)


def test_concurrent_distinct_ratings_do_not_lose_business_publication_pause() -> None:
    client = _client()
    first_remitter, business, first_order = _seed_completed_order(client, telegram_id=42430)
    second_remitter = _login(client, 42431, "remitter_42431")
    second_order = _seed_completed_order_for_business(
        client,
        remitter=second_remitter,
        business=business,
    )
    started_at = utc_now()

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda args: _post_rating(client, args[0], args[1], 5, args[2]),
                (
                    (first_remitter, first_order.id, "parallel_pause_a"),
                    (second_remitter, second_order.id, "parallel_pause_b"),
                ),
            )
        )

    assert [response.status_code for response in responses].count(201) == 2
    assert len(client.app.state.rating_repository.ratings) == 2
    stored = client.app.state.business_repository.get_business(business.id)
    assert stored.ad_publication_paused_until is not None
    assert stored.ad_publication_paused_until >= started_at + timedelta(minutes=15)


def test_rejected_rating_attempts_do_not_start_publication_pause() -> None:
    client = _client()
    remitter, business, order = _seed_completed_order(client, telegram_id=42440)
    order.status = "payment_confirmed"

    not_completed = _post_rating(client, remitter, order.id, 4, "pause_not_completed")
    invalid_stars = _post_rating(client, remitter, order.id, 6, "pause_invalid_stars")
    foreign = _login(client, 42441, "foreign_42441")
    foreign_order = _post_rating(client, foreign, order.id, 4, "pause_foreign")

    assert not_completed.status_code == 409
    assert invalid_stars.status_code == 422
    assert foreign_order.status_code == 404
    assert client.app.state.business_repository.get_business(business.id).ad_publication_paused_until is None


def test_rating_pause_migration_and_postgres_update_contract_are_reversible_and_atomic() -> None:
    migration_up = (
        ROOT / "database" / "migrations" / "0050_business_ad_publication_pause.up.sql"
    ).read_text(encoding="utf-8").lower()
    migration_down = (
        ROOT / "database" / "migrations" / "0050_business_ad_publication_pause.down.sql"
    ).read_text(encoding="utf-8").lower()
    repository = (
        ROOT / "apps" / "api" / "app" / "modules" / "orders" / "ratings_repository.py"
    ).read_text(encoding="utf-8").lower()

    assert "add column if not exists ad_publication_paused_until timestamptz null" in migration_up
    assert "drop column if exists ad_publication_paused_until" in migration_down
    assert "ad_publication_paused_until = greatest(" in repository
    assert "interval '15 minutes'" in repository
    assert "select * from businesses where id = %s for update" in repository


def test_owned_completed_order_rating_recalculates_public_reputation_once() -> None:
    client = _client()
    remitter, business, order = _seed_completed_order(client)
    public_reputation_before = business_payload(business)["reputation"]

    detail_before = client.get(f"/api/v1/orders/{order.id}", headers=_headers(remitter, "detail"))
    assert detail_before.status_code == 200
    assert detail_before.json()["data"]["order"]["rating"] == {
        "can_rate": True,
        "already_rated": False,
        "stars": None,
    }

    response = _post_rating(client, remitter, order.id, 5)

    assert response.status_code == 201, response.text
    data = response.json()["data"]
    assert data["rating"]["stars"] == 5
    assert data["rating"]["order_id"] == order.id
    assert data["business_reputation"] == {
        "publication_status": "withheld_pending_snapshot",
        "label": "Reputación aún no publicada",
    }
    assert not ({"risk_level", "trust_level", "business_failure_orders_count", "lost_disputes_count"} & set(data["business_reputation"]))

    stored = client.app.state.business_repository.get_business(business.id)
    assert stored.rating_avg == Decimal("5.00")
    assert stored.ratings_count == 1
    assert stored.completed_orders_count == 1

    business_owner = _login_as(client, 42013, "business_rating_owner", "business_owner")
    stored.owner_user_id = business_owner["user"]["id"]
    business_response = client.get("/api/v1/businesses/me", headers=_headers(business_owner, "business_me_after_rating"))
    assert business_response.status_code == 200
    business_reputation = business_response.json()["data"]["business"]["reputation"]
    assert business_reputation == public_reputation_before
    assert "rating_avg" not in business_reputation
    assert "ratings_count" not in business_reputation
    business_order = business_order_payload(order)
    assert "rating" not in business_order
    assert "stars" not in json.dumps(business_order).lower()

    detail_after = client.get(f"/api/v1/orders/{order.id}", headers=_headers(remitter, "detail_after"))
    assert detail_after.json()["data"]["order"]["rating"] == {
        "can_rate": False,
        "already_rated": True,
        "stars": 5,
    }


def test_admin_resolved_completed_order_requires_closed_dispute() -> None:
    client = _client()
    remitter, _, order = _seed_completed_order(client, telegram_id=42002, completion_reason="admin_resolved")

    without_dispute = _post_rating(client, remitter, order.id, 4, "missing_dispute")
    assert without_dispute.status_code == 409
    assert without_dispute.json()["error"]["code"] == "RATING_NOT_ALLOWED"

    dispute = client.app.state.dispute_repository.create_dispute(
        order_id=order.id,
        opened_by_user_id=remitter["user"]["id"],
        opened_by_role="remitter",
        previous_order_status="delivered",
        reason="payment_mobile_not_received",
        description=None,
    )

    blocked = _post_rating(client, remitter, order.id, 4, "open_dispute")
    assert blocked.status_code == 409
    assert blocked.json()["error"]["code"] == "RATING_NOT_ALLOWED"

    client.app.state.dispute_repository.update_dispute(
        dispute,
        status="resolved",
        resolution_type="business_favored",
        resolved_at=utc_now(),
    )
    allowed = _post_rating(client, remitter, order.id, 4, "closed_dispute")
    assert allowed.status_code == 201, allowed.text


@pytest.mark.parametrize("completion_reason", [None, "auto_completed", "legacy_completed"])
def test_rating_rejects_completed_order_with_unapproved_completion_reason(completion_reason: str | None) -> None:
    client = _client()
    remitter, _, order = _seed_completed_order(
        client,
        telegram_id=42300 + len(completion_reason or "none"),
        completion_reason=completion_reason,
    )

    detail = client.get(f"/api/v1/orders/{order.id}", headers=_headers(remitter, "invalid_reason_detail"))
    response = _post_rating(client, remitter, order.id, 3, "invalid_reason_submit")

    assert detail.status_code == 200
    assert detail.json()["data"]["order"]["rating"]["can_rate"] is False
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RATING_NOT_ALLOWED"
    assert client.app.state.rating_repository.get_for_order(order.id) is None


def test_automatic_completion_reason_can_be_rated() -> None:
    client = _client()
    remitter, _, order = _seed_completed_order(
        client,
        telegram_id=42320,
        completion_reason="auto_completed_after_24h",
    )

    response = _post_rating(client, remitter, order.id, 4, "automatic_completion")

    assert response.status_code == 201, response.text


@pytest.mark.parametrize("status", ["waiting_payment", "payment_reported", "payment_confirmed", "delivered", "cancelled", "disputed"])
def test_rating_rejects_orders_not_completed(status: str) -> None:
    client = _client()
    remitter, _, order = _seed_completed_order(client, telegram_id=42100 + len(status))
    order.status = status

    response = _post_rating(client, remitter, order.id, 3, f"invalid_{status}")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RATING_NOT_ALLOWED"


def test_foreign_business_admin_and_support_actors_cannot_create_rating() -> None:
    client = _client()
    owner, _, order = _seed_completed_order(client, telegram_id=42003)
    foreign = _login(client, 42004, "foreign")
    business = _login_as(client, 42005, "business", "business_owner")
    admin = _login_as(client, 42006, "admin", "admin")
    support = _login_as(client, 42012, "support", "support")

    foreign_response = _post_rating(client, foreign, order.id, 5, "foreign")
    assert foreign_response.status_code == 404
    assert foreign_response.json()["error"]["code"] == "ORDER_NOT_FOUND"
    assert _post_rating(client, business, order.id, 5, "business").status_code == 403
    assert _post_rating(client, admin, order.id, 5, "admin").status_code == 403
    assert _post_rating(client, support, order.id, 5, "support").status_code == 403
    assert _post_rating(client, owner, str(uuid4()), 5, "missing").status_code == 404


def test_client_cannot_rate_a_business_owned_by_the_same_user() -> None:
    client = _client()
    remitter, business, order = _seed_completed_order(client, telegram_id=42011)
    business.owner_user_id = remitter["user"]["id"]

    response = _post_rating(client, remitter, order.id, 5, "self_rating")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RATING_NOT_ALLOWED"
    assert client.app.state.rating_repository.get_for_order(order.id) is None


@pytest.mark.parametrize("stars", [0, 6, 1.5, "5", True, None])
def test_rating_payload_requires_strict_integer_1_to_5(stars: object) -> None:
    client = _client()
    remitter, _, order = _seed_completed_order(client, telegram_id=42200 + len(str(stars)))

    response = _post_rating(client, remitter, order.id, stars, f"payload_{stars}")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_rating_payload_forbids_comments_and_server_owned_fields() -> None:
    client = _client()
    remitter, business, order = _seed_completed_order(client, telegram_id=42007)

    for extra in (
        {"comment": "texto"},
        {"rating_type": "business"},
        {"business_id": business.id},
        {"rater_user_id": remitter["user"]["id"]},
    ):
        response = client.post(
            f"/api/v1/orders/{order.id}/rating",
            headers=_headers(remitter, f"extra_{next(iter(extra))}"),
            json={"stars": 5, **extra},
        )
        assert response.status_code == 422


def test_rating_idempotency_replay_mismatch_and_duplicate_are_distinct() -> None:
    client = _client()
    remitter, _, order = _seed_completed_order(client, telegram_id=42008)

    first = _post_rating(client, remitter, order.id, 4, "same_key")
    replay = _post_rating(client, remitter, order.id, 4, "same_key")
    mismatch = _post_rating(client, remitter, order.id, 5, "same_key")
    duplicate = _post_rating(client, remitter, order.id, 4, "other_key")
    missing_key = _post_rating(client, remitter, order.id, 4, None)

    assert first.status_code == replay.status_code == 201
    assert first.json()["data"]["rating"]["id"] == replay.json()["data"]["rating"]["id"]
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "RATING_ALREADY_EXISTS"
    assert missing_key.status_code == 400
    assert missing_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"


def test_concurrent_rating_attempts_create_one_rating_and_one_aggregate_effect() -> None:
    client = _client()
    remitter, business, order = _seed_completed_order(client, telegram_id=42009)

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(
            executor.map(
                lambda key: _post_rating(client, remitter, order.id, 5, key),
                ["race_a", "race_b"],
            )
        )

    assert sorted(response.status_code for response in responses) == [201, 409]
    assert len(client.app.state.rating_repository.ratings) == 1
    stored = client.app.state.business_repository.get_business(business.id)
    assert stored.ratings_count == 1
    assert stored.rating_avg == Decimal("5.00")


def test_rating_audit_and_response_are_minimal_and_private() -> None:
    client = _client()
    remitter, _, order = _seed_completed_order(client, telegram_id=42010)

    response = _post_rating(client, remitter, order.id, 2, "private")
    assert response.status_code == 201

    serialized = json.dumps(response.json()).lower()
    for forbidden in ("risk_level", "trust_level", "storage_path", "account_value", "comment", "review_body"):
        assert forbidden not in serialized
    audit = next(event for event in client.app.state.audit_writer.events if event.event_type == "rating_created")
    assert set(audit.metadata_json or {}) == {"order_id", "business_id"}
    assert "stars" not in (audit.metadata_json or {})
    assert client.app.state.chat_repository.messages == {}
    assert not any(
        "rating" in job.notification_type
        for job in client.app.state.job_repository.notification_jobs.values()
    )
    assert not any("rating" in notification_type for notification_type in TELEGRAM_NOTIFICATION_TYPES)
    assert "completed" not in BUSINESS_ORDER_ATTENTION_STATUSES
    assert "completed" not in CLIENT_ORDER_ATTENTION_STATUSES


def test_frontend_rating_is_backend_authoritative_and_has_own_action_state() -> None:
    api = (ROOT / "apps" / "web" / "src" / "api" / "orders.ts").read_text(encoding="utf-8")
    types = (ROOT / "apps" / "web" / "src" / "types" / "orders.ts").read_text(encoding="utf-8")
    actions = (ROOT / "apps" / "web" / "src" / "hooks" / "workspace" / "useClientActionState.ts").read_text(encoding="utf-8")
    model = (ROOT / "apps" / "web" / "src" / "hooks" / "workspace" / "useRemitterOrdersModel.ts").read_text(encoding="utf-8")
    screen = (ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientOrderScreens.tsx").read_text(encoding="utf-8")
    chat_model = (ROOT / "apps" / "web" / "src" / "hooks" / "workspace" / "useClientChatDisputesModel.ts").read_text(encoding="utf-8")
    chat_screen = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            ROOT / "apps" / "web" / "src" / "screens" / "client" / "ClientOrderChatScreen.tsx",
            ROOT / "apps" / "web" / "src" / "screens" / "client" / "chat" / "ClientOrderRatingBubble.tsx",
        )
    )

    assert "/api/v1/orders/${orderId}/rating" in api
    assert "can_rate" in types and "already_rated" in types and "stars" in types
    assert "submittingRatingOrderId" in actions
    assert 'recordActionStarted("client_order_rating_submit"' in model
    assert "setSubmittingRatingOrderId(orderId)" in model
    assert "Calificar negocio" in screen
    assert "rating?: OrderSummary[\"rating\"]" in chat_model
    assert "rating: data.rating" in chat_model
    assert "getOrder" in chat_model
    assert "¿Cómo fue esta operación?" in chat_screen
    assert "Calificaste" in chat_screen
    assert "submitOrderRating" in chat_screen
    assert 'setView("order-summary")' not in chat_screen
    rating_submit_block = model.split("async function submitRating", 1)[1].split("async function prefetchMyOrders", 1)[0]
    assert "setSelectedRatingStars(0)" not in rating_submit_block
    assert "calculateReputation" not in model
    assert "computeReputation" not in model
    assert "comment" not in api.lower()
