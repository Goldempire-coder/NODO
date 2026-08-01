from __future__ import annotations

from dataclasses import replace
import hashlib
import hmac
import inspect
import json
import os
import time
from datetime import timedelta
from urllib.parse import urlencode
from uuid import uuid4

from fastapi.testclient import TestClient


BOT_TOKEN = "123456:test-bot-token"
JWT_SECRET = "test-access-secret"
JWT_REFRESH_SECRET = "test-refresh-secret"


def _set_env(**overrides: str) -> None:
    values = {
        "APP_ENV": "test",
        "APP_NAME": "NODO",
        "APP_VERSION": "0.0.0-slice-04",
        "NODO_BUILD_ID": "pytest-orders-build",
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
        "NODO_INTERNAL_PROFILING": "0",
    }
    values.update(overrides)
    for key, value in values.items():
        os.environ[key] = value


_set_env()

from app.main import create_app  # noqa: E402
from app.modules.businesses.models import utc_now  # noqa: E402
from app.modules.businesses.pin_security import hash_pin  # noqa: E402
from app.modules.orders.postgres_create_order import PostgresCreateOrderMixin  # noqa: E402
from app.modules.orders.postgres_queries import PostgresOrderQueriesMixin  # noqa: E402


def _client(**env_overrides: str) -> TestClient:
    _set_env(**env_overrides)
    return TestClient(create_app())


def test_postgres_order_create_uses_combined_start_context_and_transactional_audit() -> None:
    assert hasattr(PostgresCreateOrderMixin, "get_order_create_start_context")
    assert PostgresCreateOrderMixin.creates_audit_events_on_create_order is True
    assert PostgresCreateOrderMixin.skips_idempotency_precheck_on_create_order is True
    create_order_source = inspect.getsource(PostgresCreateOrderMixin.create_order)
    start_context_source = inspect.getsource(PostgresCreateOrderMixin.get_order_create_start_context)

    assert "audit_events = fields.pop" in create_order_source
    assert "_insert_create_order_audit_events" in create_order_source
    assert "conn.commit()" in create_order_source
    assert "select * from orders where remitter_user_id" in start_context_source
    assert "_order_create_context_sql" in start_context_source


def _signed_init_data(telegram_id: int = 901, username: str = "user") -> str:
    payload = {
        "auth_date": str(int(time.time())),
        "user": json.dumps({"id": telegram_id, "username": username, "first_name": username}, separators=(",", ":"), sort_keys=True),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(payload.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    payload["hash"] = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    return urlencode(payload)


def _login_without_terms(client: TestClient, telegram_id: int = 901, username: str = "user") -> dict:
    response = client.post(
        "/api/v1/auth/telegram",
        headers={"X-Request-Id": f"req_login_{telegram_id}"},
        json={"init_data": _signed_init_data(telegram_id=telegram_id, username=username)},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _login(client: TestClient, telegram_id: int = 901, username: str = "user") -> dict:
    login = _login_without_terms(client, telegram_id, username)
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


def _create_business(client: TestClient, login: dict, key: str = "create") -> dict:
    response = client.post(
        "/api/v1/businesses",
        headers={**_headers(login, key), "Content-Type": "application/json", "X-NODO-Test-Fixture": "business_create"},
        json={"business_name": f"Casa {key}", "rif": "J-12345678-9", "address": "Av Principal", "phone": "+584121234567", "country": "VE"},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["business"]


def _approved_business_with_method(client: TestClient, login: dict, *, credits: int = 5, approved: bool = True) -> tuple[dict, str]:
    business = _create_business(client, login, f"biz_{login['user']['id']}")
    stored_business = client.app.state.business_repository.get_business(business["id"])
    if approved:
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


def _create_ad(client: TestClient, owner: dict, payment_method_id: str, *, key: str = "ad", amount_min: str = "20.00", amount_max: str = "100.00") -> dict:
    response = client.post(
        "/api/v1/business/ads",
        headers={**_headers(owner, key), "Content-Type": "application/json"},
        json={
            "payment_method_id": payment_method_id,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": amount_min,
            "amount_max_usd": amount_max,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["ad"]


def _receiver() -> dict:
    return {"bank": "Banco", "phone": "+584121234567", "document": "V12345678", "holder": "Receptor Test"}


def _create_order(client: TestClient, remitter: dict, ad_id: str, *, key: str = "order", amount: str = "50.00") -> dict:
    response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, key), "Content-Type": "application/json"},
        json={"ad_id": ad_id, "amount_usd": amount, "receiver_data": _receiver()},
    )
    assert response.status_code == 201, response.text
    return response.json()["data"]["order"]


def test_slice_50a_create_order_allows_chat_first_flow_without_receiver_data() -> None:
    client = _client()
    owner = _login(client, 9851, "slice50a_owner")
    business, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="slice50a_ad")
    remitter = _login(client, 9852, "slice50a_client")

    response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "slice50a_create"), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "50.00"},
    )

    assert response.status_code == 201, response.text
    order = response.json()["data"]["order"]
    assert order["status"] == "waiting_payment"
    assert order["receiver_data_masked"] == {
        "bank": None,
        "phone": None,
        "document": None,
        "holder": None,
    }
    stored = client.app.state.order_repository.get_by_id(order["id"])
    assert stored.receiver_data_json == {}
    reservation = client.app.state.capacity_repository.get_reservation(order["id"])
    assert reservation is not None
    assert reservation.status == "reserved"
    assert business["id"] == stored.business_id


def test_slice_50a_chat_first_order_replays_without_receiver_data() -> None:
    client = _client()
    owner = _login(client, 9853, "slice50a_replay_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="slice50a_replay_ad")
    remitter = _login(client, 9854, "slice50a_replay_client")
    payload = {
        "ad_id": ad["id"],
        "amount_usd": "50.00",
        "expected_rate_bs_per_usd": ad["rate_bs_per_usd"],
    }

    first = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "slice50a_replay"), "Content-Type": "application/json"},
        json=payload,
    )
    replay = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "slice50a_replay"), "Content-Type": "application/json"},
        json=payload,
    )

    assert first.status_code == 201, first.text
    assert replay.status_code in {200, 201}, replay.text
    assert replay.json()["data"]["order"]["id"] == first.json()["data"]["order"]["id"]


def test_slice_50a_create_order_rejects_a_changed_quote() -> None:
    client = _client()
    owner = _login(client, 9855, "slice50a_quote_owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="slice50a_quote_ad")
    remitter = _login(client, 9856, "slice50a_quote_client")

    response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "slice50a_stale_quote"), "Content-Type": "application/json"},
        json={
            "ad_id": ad["id"],
            "amount_usd": "50.00",
            "expected_rate_bs_per_usd": "1.000000",
        },
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_QUOTE_CHANGED"
    assert client.app.state.order_repository.orders == {}
    assert client.app.state.capacity_repository.reservations == {}


def _event_types(client: TestClient) -> list[str]:
    return [event.event_type for event in client.app.state.audit_writer.events]


def test_surface_attention_summary_is_one_safe_request_for_orders_and_support() -> None:
    client = _client()
    owner = _login(client, 8901, "attention_owner")
    business, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="attention_ad")
    remitter = _login(client, 8902, "attention_client")
    order = _create_order(client, remitter, ad["id"], key="attention_order")
    support_response = client.post(
        "/api/v1/support/tickets",
        headers={
            **_headers(remitter, "attention_support"),
            "Content-Type": "application/json",
            "X-NODO-Surface": "client_mini_app",
        },
        json={
            "scope": "client_order",
            "category": "order_help",
            "subject": "Asunto privado no notificable",
            "message": "Cuerpo privado no notificable",
            "order_id": order["id"],
        },
    )
    assert support_response.status_code == 201, support_response.text
    ticket = client.app.state.support_repository.get_ticket(support_response.json()["data"]["id"])
    client.app.state.support_repository.update_ticket(ticket, status="waiting_user")

    client_summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(remitter, "attention_client_summary"),
            "X-NODO-Surface": "client_mini_app",
        },
    )
    assert client_summary.status_code == 200, client_summary.text
    assert client_summary.headers["cache-control"] == "private, no-store"
    data = client_summary.json()["data"]
    assert data["counts"] == {"orders": 1, "support": 1, "total": 2}
    assert {item["kind"] for item in data["items"]} == {"order", "support"}
    serialized = json.dumps(data).lower()
    assert "asunto privado" not in serialized
    assert "cuerpo privado" not in serialized
    for forbidden in [
        "body",
        "subject",
        "storage_path",
        "signed_url",
        "file_asset_id",
        "account_value",
        "token",
        "wallet",
        "pin",
    ]:
        assert forbidden not in serialized

    business_summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(owner, "attention_business_summary"),
            "X-NODO-Surface": "business_mini_app",
        },
    )
    assert business_summary.status_code == 200, business_summary.text
    assert business_summary.json()["data"]["counts"]["orders"] == 1
    assert business_summary.json()["data"]["counts"]["support"] == 0

    business_support_response = client.post(
        "/api/v1/support/tickets",
        headers={
            **_headers(owner, "attention_business_support"),
            "Content-Type": "application/json",
            "X-NODO-Surface": "business_mini_app",
        },
        json={
            "scope": "business_general",
            "category": "technical_issue",
            "subject": "Asunto privado del negocio",
            "message": "Cuerpo privado del negocio",
        },
    )
    assert business_support_response.status_code == 201, business_support_response.text
    business_ticket = client.app.state.support_repository.get_ticket(
        business_support_response.json()["data"]["id"]
    )
    client.app.state.support_repository.update_ticket(business_ticket, status="waiting_user")
    business_support_summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(owner, "attention_business_support_summary"),
            "X-NODO-Surface": "business_mini_app",
        },
    )
    assert business_support_summary.status_code == 200, business_support_summary.text
    assert business_support_summary.json()["data"]["counts"]["support"] == 1
    business_serialized = json.dumps(business_support_summary.json()["data"]).lower()
    assert "asunto privado del negocio" not in business_serialized
    assert "cuerpo privado del negocio" not in business_serialized

    wrong_surface = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(remitter, "attention_wrong_surface"),
            "X-NODO-Surface": "business_mini_app",
        },
    )
    assert wrong_surface.status_code == 403
    assert business["id"] not in serialized


def test_surface_attention_acknowledgement_is_durable_and_reopens_on_new_order_message() -> None:
    client = _client()
    owner = _login(client, 8921, "attention_ack_owner")
    _business, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="attention_ack_ad")
    remitter = _login(client, 8922, "attention_ack_client")
    order = _create_order(client, remitter, ad["id"], key="attention_ack_order")
    stored_order = client.app.state.order_repository.get_by_id(order["id"])
    stored_order.status = "payment_reported"

    first_summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(owner, "attention_ack_summary"),
            "X-NODO-Surface": "business_mini_app",
        },
    )
    assert first_summary.status_code == 200, first_summary.text
    order_item = next(item for item in first_summary.json()["data"]["items"] if item["kind"] == "order")

    acknowledged = client.post(
        "/api/v1/notifications/attention/acknowledge",
        headers={
            **_bearer(owner, "attention_ack_post"),
            "Content-Type": "application/json",
            "X-NODO-Surface": "business_mini_app",
        },
        json={
            "kind": "order",
            "resource_id": order["id"],
            "signature": order_item["signature"],
        },
    )
    assert acknowledged.status_code == 200, acknowledged.text
    assert acknowledged.json()["data"] == {"acknowledged": True}

    hidden_summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(owner, "attention_ack_hidden"),
            "X-NODO-Surface": "business_mini_app",
        },
    )
    assert hidden_summary.status_code == 200, hidden_summary.text
    assert order["id"] not in [item["resource_id"] for item in hidden_summary.json()["data"]["items"]]

    message = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers={**_headers(remitter, "attention_ack_message"), "Content-Type": "application/json"},
        json={"body": "Mensaje privado que no debe estar en awareness", "attachment_ids": []},
    )
    assert message.status_code == 201, message.text

    stale_ack = client.post(
        "/api/v1/notifications/attention/acknowledge",
        headers={
            **_bearer(owner, "attention_ack_stale"),
            "Content-Type": "application/json",
            "X-NODO-Surface": "business_mini_app",
        },
        json={
            "kind": "order",
            "resource_id": order["id"],
            "signature": order_item["signature"],
        },
    )
    assert stale_ack.status_code == 409
    assert stale_ack.json()["error"]["code"] == "ATTENTION_SIGNATURE_STALE"

    reopened_summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(owner, "attention_ack_reopened"),
            "X-NODO-Surface": "business_mini_app",
        },
    )
    assert reopened_summary.status_code == 200, reopened_summary.text
    reopened_item = next(item for item in reopened_summary.json()["data"]["items"] if item["resource_id"] == order["id"])
    serialized = json.dumps(reopened_summary.json()["data"]).lower()
    assert reopened_item["signature"] != order_item["signature"]
    assert "mensaje privado" not in serialized
    assert message.json()["data"]["message"]["id"] not in serialized


def test_surface_attention_tells_business_when_client_cancelled_order() -> None:
    client = _client()
    owner = _login(client, 8925, "attention_cancel_owner")
    business, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="attention_cancel_ad")
    remitter = _login(client, 8926, "attention_cancel_client")
    order = _create_order(client, remitter, ad["id"], key="attention_cancel_order")

    cancelled = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={**_headers(remitter, "attention_cancel"), "Content-Type": "application/json"},
        json={"reason": "choose_another_business", "payment_not_sent_confirmed": True},
    )
    summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(owner, "attention_cancel_business_summary"),
            "X-NODO-Surface": "business_mini_app",
        },
    )
    client_summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(remitter, "attention_cancel_client_summary"),
            "X-NODO-Surface": "client_mini_app",
        },
    )

    assert cancelled.status_code == 200, cancelled.text
    assert summary.status_code == 200, summary.text
    data = summary.json()["data"]
    assert data["counts"]["orders"] == 1
    item = next(item for item in data["items"] if item["kind"] == "order")
    assert item["resource_id"] == order["id"]
    assert "cancelada por el cliente" in item["message"]
    assert client_summary.status_code == 200, client_summary.text
    assert order["id"] not in [
        item["resource_id"] for item in client_summary.json()["data"]["items"]
    ]
    serialized = json.dumps(data).lower()
    assert business["id"] not in serialized
    assert "owner@example.com" not in serialized
    assert "account_value" not in serialized
    assert "storage_path" not in serialized


def test_surface_attention_acknowledgement_is_durable_for_support_updates() -> None:
    client = _client()
    remitter = _login(client, 8931, "attention_support_ack_client")
    support_response = client.post(
        "/api/v1/support/tickets",
        headers={
            **_headers(remitter, "attention_support_ack_ticket"),
            "Content-Type": "application/json",
            "X-NODO-Surface": "client_mini_app",
        },
        json={
            "scope": "client_general",
            "category": "technical_issue",
            "subject": "Asunto privado",
            "message": "Cuerpo privado",
        },
    )
    assert support_response.status_code == 201, support_response.text
    ticket = client.app.state.support_repository.get_ticket(support_response.json()["data"]["id"])
    client.app.state.support_repository.update_ticket(ticket, status="waiting_user")

    first_summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(remitter, "attention_support_ack_summary"),
            "X-NODO-Surface": "client_mini_app",
        },
    )
    assert first_summary.status_code == 200, first_summary.text
    support_item = next(item for item in first_summary.json()["data"]["items"] if item["kind"] == "support")

    acknowledged = client.post(
        "/api/v1/notifications/attention/acknowledge",
        headers={
            **_bearer(remitter, "attention_support_ack_post"),
            "Content-Type": "application/json",
            "X-NODO-Surface": "client_mini_app",
        },
        json={
            "kind": "support",
            "resource_id": ticket.id,
            "signature": support_item["signature"],
        },
    )
    assert acknowledged.status_code == 200, acknowledged.text

    hidden_summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(remitter, "attention_support_ack_hidden"),
            "X-NODO-Surface": "client_mini_app",
        },
    )
    assert hidden_summary.status_code == 200, hidden_summary.text
    assert ticket.id not in [item["resource_id"] for item in hidden_summary.json()["data"]["items"]]

    client.app.state.support_repository.create_message(
        ticket_id=ticket.id,
        sender_user_id="00000000-0000-0000-0000-000000000001",
        sender_role="support",
        body="Respuesta privada que no debe salir",
        visibility="participants",
    )
    client.app.state.support_repository.update_ticket(ticket, status="waiting_user")

    reopened_summary = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(remitter, "attention_support_ack_reopened"),
            "X-NODO-Surface": "client_mini_app",
        },
    )
    assert reopened_summary.status_code == 200, reopened_summary.text
    reopened_item = next(item for item in reopened_summary.json()["data"]["items"] if item["resource_id"] == ticket.id)
    serialized = json.dumps(reopened_summary.json()["data"]).lower()
    assert reopened_item["signature"] != support_item["signature"]
    assert "respuesta privada" not in serialized


def test_surface_attention_orders_use_latest_operational_update_before_limit() -> None:
    client = _client()
    owner = _login(client, 8911, "attention_order_owner")
    _business, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="attention_order_ad")
    remitter = _login(client, 8912, "attention_order_client")
    order = _create_order(client, remitter, ad["id"], key="attention_order_old")
    stored_order = client.app.state.order_repository.get_by_id(order["id"])
    latest_update = stored_order.updated_at
    stored_order.created_at = latest_update - timedelta(days=2)
    stored_order.updated_at = latest_update + timedelta(seconds=1)
    for index in range(55):
        extra_order = replace(
            stored_order,
            id=str(uuid4()),
            public_order_code=f"NODO-ATTN-{index:03}",
            created_at=latest_update - timedelta(minutes=index),
            updated_at=latest_update - timedelta(hours=index + 1),
        )
        client.app.state.order_repository.orders[extra_order.id] = extra_order

    response = client.get(
        "/api/v1/notifications/attention-summary",
        headers={
            **_bearer(remitter, "attention_latest_update"),
            "X-NODO-Surface": "client_mini_app",
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()["data"]
    order_items = [item for item in data["items"] if item["kind"] == "order"]
    assert len(order_items) == 50
    assert data["truncated"]["orders"] is True
    assert order_items[0]["resource_id"] == order["id"]
    assert order["id"] in {item["resource_id"] for item in order_items}


def test_postgres_attention_queries_order_by_operational_update_before_limit() -> None:
    for method_name in (
        "list_attention_for_business",
        "list_attention_for_remitter",
    ):
        source = inspect.getsource(getattr(PostgresOrderQueriesMixin, method_name))
        assert "order by updated_at desc, id desc" in source
        assert "limit %s" in source


def test_create_order_requires_terms_but_user_can_accept_later() -> None:
    client = _client()
    owner = _login(client, 923, "owner_terms_gate")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="terms_gate_ad")
    remitter = _login_without_terms(client, 924, "remitter_terms_gate")

    blocked = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "terms_gate_blocked"), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "50.00", "receiver_data": _receiver()},
    )
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "TERMS_ACCEPTANCE_REQUIRED"

    accepted = client.post(
        "/api/v1/users/me/terms-acceptance",
        headers={"Authorization": f"Bearer {remitter['access_token']}", "X-Request-Id": "req_terms_gate_accept"},
        json={"terms_version": "2026-07-06"},
    )
    assert accepted.status_code == 200, accepted.text

    created = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "terms_gate_created"), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "50.00", "receiver_data": _receiver()},
    )
    assert created.status_code == 201, created.text
    assert created.json()["data"]["order"]["status"] == "waiting_payment"


def test_create_order_success_waiting_payment_snapshot_no_credit_consume_or_instruction_leak() -> None:
    client = _client()
    owner = _login(client, 901, "owner")
    business, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="order_ad")
    wallet_before = client.app.state.ad_repository.get_wallet(business["id"])
    remitter = _login(client, 902, "remitter")

    order = _create_order(client, remitter, ad["id"], key="create_order")

    assert order["status"] == "waiting_payment"
    assert order["amount_bs_calculated"] == "1975.00"
    assert order["payment_instructions_masked"]["account_masked"] == "***.com"
    assert order["can_view_payment_instructions"] is False
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "in_order"
    wallet_after = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet_after.available_credits == wallet_before.available_credits
    assert wallet_after.blocked_credits == wallet_before.blocked_credits
    stored = client.app.state.order_repository.get_by_id(order["id"])
    assert stored.payment_instructions_snapshot["account_value"] == "owner@example.com"
    response_text = json.dumps(order)
    assert "owner@example.com" not in response_text
    assert "account_value" not in response_text
    assert {"order_created", "ad_moved_in_order"}.issubset(set(_event_types(client)))


def test_create_order_invalidates_marketplace_cache_for_reserved_ad() -> None:
    client = _client()
    owner = _login(client, 903, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="cache_order_ad")
    remitter = _login(client, 904, "remitter")
    query = "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&sort=rate"

    before_order = client.get(query, headers=_bearer(remitter, "req_search_before_order"))
    assert before_order.status_code == 200
    assert ad["id"] in [item["id"] for item in before_order.json()["data"]["items"]]

    _create_order(client, remitter, ad["id"], key="cache_order")
    after_order = client.get(query, headers=_bearer(remitter, "req_search_after_order"))

    assert after_order.status_code == 200
    assert ad["id"] not in [item["id"] for item in after_order.json()["data"]["items"]]


def test_create_order_filters_reserved_ad_from_warm_marketplace_cache_without_second_reheat() -> None:
    client = _client()
    owner_one = _login(client, 913, "owner_one")
    _, method_one = _approved_business_with_method(client, owner_one, credits=1)
    ad_one = _create_ad(client, owner_one, method_one, key="cache_order_ad_one")
    owner_two = _login(client, 914, "owner_two")
    _, method_two = _approved_business_with_method(client, owner_two, credits=1)
    ad_two = _create_ad(client, owner_two, method_two, key="cache_order_ad_two")
    remitter_one = _login(client, 915, "remitter_one")
    remitter_two = _login(client, 916, "remitter_two")
    query = "/api/v1/ads/search?amount_usd=50.00&payment_method=zelle&delivery_method=pago_movil_ve&sort=rate"
    original_list = client.app.state.ad_repository.list_marketplace_ads
    calls = {"count": 0}

    def counted_list_marketplace_ads(**kwargs):  # type: ignore[no-untyped-def]
        calls["count"] += 1
        return original_list(**kwargs)

    client.app.state.ad_repository.list_marketplace_ads = counted_list_marketplace_ads

    warm = client.get(query, headers=_bearer(remitter_one, "req_cache_warm_two_ads"))
    assert warm.status_code == 200
    assert {ad_one["id"], ad_two["id"]}.issubset({item["id"] for item in warm.json()["data"]["items"]})
    assert calls["count"] == 1

    _create_order(client, remitter_one, ad_one["id"], key="cache_order_one")
    after_first_order = client.get(query, headers=_bearer(remitter_two, "req_cache_after_first_order"))
    assert after_first_order.status_code == 200
    assert ad_one["id"] not in [item["id"] for item in after_first_order.json()["data"]["items"]]
    assert ad_two["id"] in [item["id"] for item in after_first_order.json()["data"]["items"]]
    assert calls["count"] == 2

    _create_order(client, remitter_two, ad_two["id"], key="cache_order_two")
    after_second_order = client.get(query, headers=_bearer(remitter_one, "req_cache_after_second_order"))
    assert after_second_order.status_code == 200
    assert ad_one["id"] not in [item["id"] for item in after_second_order.json()["data"]["items"]]
    assert ad_two["id"] not in [item["id"] for item in after_second_order.json()["data"]["items"]]
    assert calls["count"] == 2


def test_create_order_internal_profile_reports_required_stages() -> None:
    client = _client(NODO_INTERNAL_PROFILING="1")
    owner = _login(client, 905, "owner_profile")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="profile_order_ad")
    remitter = _login(client, 906, "remitter_profile")

    response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "profile_order"), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "50.00", "receiver_data": _receiver()},
    )

    assert response.status_code == 201, response.text
    profile = response.json()["data"]["_profile"]
    stages = {entry["stage"] for entry in profile["stages"]}
    assert "auth:require_remitter" in stages
    assert "rate_limit:order_create" in stages
    assert "idempotency:get_existing" in stages
    assert "idempotency:store_response" in stages
    assert "transaction:create_order_and_move_ad" in stages
    assert "cache:marketplace_invalidation" in stages
    assert "audit:order_created_and_ad_moved" in stages
    assert "dependency" in profile
    assert "auth" in profile["dependency"]


def test_create_order_profile_requires_staging_env_flag_and_header() -> None:
    client = _client(ENABLE_STAGING_PROFILING="1")
    os.environ["APP_ENV"] = "staging"
    owner = _login(client, 917, "owner_staging_profile")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="staging_profile_order_ad")
    remitter = _login(client, 918, "remitter_staging_profile")

    no_header = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "staging_profile_no_header"), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "50.00", "receiver_data": _receiver()},
    )

    assert no_header.status_code == 201, no_header.text
    assert "_profile" not in no_header.json()["data"]

    owner_2 = _login(client, 919, "owner_staging_profile_2")
    _, method_id_2 = _approved_business_with_method(client, owner_2, credits=1)
    ad_2 = _create_ad(client, owner_2, method_id_2, key="staging_profile_order_ad_2")
    with_header = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "staging_profile_with_header"), "Content-Type": "application/json", "X-NODO-Profile": "1"},
        json={"ad_id": ad_2["id"], "amount_usd": "50.00", "receiver_data": _receiver()},
    )

    assert with_header.status_code == 201, with_header.text
    profile = with_header.json()["data"]["_profile"]
    stages = {entry["stage"] for entry in profile["stages"]}
    assert "transaction:create_order_and_move_ad" in stages
    assert "cache:marketplace_invalidation" in stages
    serialized = json.dumps(profile)
    forbidden = ["account_value", "storage_path", "Authorization", "Bearer", "JWT_SECRET", "BOT_TOKEN"]
    assert not any(value in serialized for value in forbidden)


def test_create_order_profile_is_not_returned_in_production_with_header() -> None:
    client = _client(ENABLE_STAGING_PROFILING="1")
    os.environ["APP_ENV"] = "production"
    owner = _login(client, 920, "owner_prod_profile")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="prod_profile_order_ad")
    remitter = _login(client, 921, "remitter_prod_profile")

    response = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "prod_profile_with_header"), "Content-Type": "application/json", "X-NODO-Profile": "1"},
        json={"ad_id": ad["id"], "amount_usd": "50.00", "receiver_data": _receiver()},
    )

    assert response.status_code == 201, response.text
    assert "_profile" not in response.json()["data"]


def test_create_order_rejects_invalid_ad_business_amount_and_requires_idempotency_key() -> None:
    client = _client()
    owner = _login(client, 911, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=2)
    ad = _create_ad(client, owner, method_id, key="invalid_ad")
    remitter = _login(client, 912, "remitter")

    no_key = client.post(
        "/api/v1/orders",
        headers={**_bearer(remitter, "req_no_key"), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "50.00", "receiver_data": _receiver()},
    )
    assert no_key.status_code == 400
    assert no_key.json()["error"]["code"] == "IDEMPOTENCY_KEY_REQUIRED"

    out_of_range = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "too_high"), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "101.00", "receiver_data": _receiver()},
    )
    assert out_of_range.status_code == 400
    assert out_of_range.json()["error"]["code"] == "AMOUNT_OUT_OF_RANGE"

    client.app.state.ad_repository.set_status(client.app.state.ad_repository.get_ad(ad["id"]), "paused")
    inactive = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "inactive"), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "50.00", "receiver_data": _receiver()},
    )
    assert inactive.status_code == 409
    assert inactive.json()["error"]["code"] == "AD_NOT_AVAILABLE"

    other_owner = _login(client, 913, "not_approved")
    _, other_method = _approved_business_with_method(client, other_owner, credits=1)
    other_ad = _create_ad(client, other_owner, other_method, key="not_approved_seed")
    client.app.state.business_repository.get_business(other_ad["business_id"]).verification_status = "pending"
    not_approved = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "not_approved_order"), "Content-Type": "application/json"},
        json={"ad_id": other_ad["id"], "amount_usd": "50.00", "receiver_data": _receiver()},
    )
    assert not_approved.status_code == 409
    assert not_approved.json()["error"]["code"] == "BUSINESS_NOT_APPROVED"


def test_create_order_idempotency_replays_same_payload_and_rejects_changed_payload() -> None:
    client = _client()
    owner = _login(client, 921, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="idem_ad")
    remitter = _login(client, 922, "remitter")

    first = _create_order(client, remitter, ad["id"], key="same_order")
    replay = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "same_order"), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "50.00", "receiver_data": _receiver()},
    )
    assert replay.status_code in {200, 201}
    assert replay.json()["data"]["order"]["id"] == first["id"]

    mismatch = client.post(
        "/api/v1/orders",
        headers={**_headers(remitter, "same_order"), "Content-Type": "application/json"},
        json={"ad_id": ad["id"], "amount_usd": "60.00", "receiver_data": _receiver()},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"


def test_detail_and_mine_are_own_only_and_masked() -> None:
    client = _client()
    owner = _login(client, 931, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="detail_ad")
    remitter = _login(client, 932, "remitter")
    other = _login(client, 933, "other")
    order = _create_order(client, remitter, ad["id"], key="detail_order")

    detail = client.get(f"/api/v1/orders/{order['id']}", headers=_bearer(remitter, "req_detail"))
    mine = client.get("/api/v1/orders/mine?limit=20", headers=_bearer(remitter, "req_mine"))
    foreign = client.get(f"/api/v1/orders/{order['id']}", headers=_bearer(other, "req_foreign"))

    assert detail.status_code == 200
    assert mine.status_code == 200
    assert [item["id"] for item in mine.json()["data"]["items"]] == [order["id"]]
    assert foreign.status_code == 404
    combined = detail.text + mine.text
    assert "owner@example.com" not in combined
    assert "account_value" not in combined
    assert "+584121234567" not in combined


def test_cancel_waiting_payment_returns_ad_and_keeps_listing_credit_blocked() -> None:
    client = _client()
    owner = _login(client, 941, "owner")
    business, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="cancel_ad")
    remitter = _login(client, 942, "remitter")
    order = _create_order(client, remitter, ad["id"], key="cancel_order")

    cancelled = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={**_headers(remitter, "cancel_order"), "Content-Type": "application/json"},
        json={"reason": "choose_another_business", "payment_not_sent_confirmed": True},
    )

    assert cancelled.status_code == 200
    assert cancelled.json()["data"]["order"]["status"] == "cancelled"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "active"
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet.available_credits == 0
    assert wallet.blocked_credits == 1
    assert "order_cancelled" in _event_types(client)
    assert "credits_released" not in _event_types(client)


def test_slice_48a_cancel_rejects_unknown_reason() -> None:
    client = _client()
    owner = _login(client, 943, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="cancel_reason_ad")
    remitter = _login(client, 944, "remitter")
    order = _create_order(client, remitter, ad["id"], key="cancel_reason_order")

    response = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={**_headers(remitter, "cancel_unknown_reason"), "Content-Type": "application/json"},
        json={"reason": "free text with private details", "payment_not_sent_confirmed": True},
    )

    assert response.status_code == 422
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "waiting_payment"


def test_slice_48a_cancel_after_instructions_requires_no_payment_confirmation() -> None:
    client = _client()
    owner = _login(client, 945, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="cancel_confirm_ad")
    remitter = _login(client, 946, "remitter")
    order = _create_order(client, remitter, ad["id"], key="cancel_confirm_order")
    shared = client.post(
        f"/api/v1/orders/{order['id']}/share-zelle",
        headers=_headers(owner, "cancel_confirm_share_zelle"),
    )
    assert shared.status_code == 201, shared.text
    reveal = client.get(
        f"/api/v1/orders/{order['id']}/payment-instructions",
        headers=_bearer(remitter, "req_cancel_confirm_reveal"),
    )
    assert reveal.status_code == 200, reveal.text

    missing_confirmation = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={**_headers(remitter, "cancel_without_confirmation"), "Content-Type": "application/json"},
        json={"reason": "business_unavailable"},
    )
    confirmed = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={**_headers(remitter, "cancel_with_confirmation"), "Content-Type": "application/json"},
        json={"reason": "business_unavailable", "payment_not_sent_confirmed": True},
    )

    assert missing_confirmation.status_code == 409
    assert missing_confirmation.json()["error"]["code"] == "ORDER_PAYMENT_NOT_SENT_CONFIRMATION_REQUIRED"
    assert missing_confirmation.json()["error"]["message"] == (
        "Confirma que no enviaste el pago antes de cancelar esta orden."
    )
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["data"]["order"]["cancel_reason"] == "remitter_cancelled_before_payment"


def test_slice_48a_cancel_requires_boolean_confirmation_type() -> None:
    client = _client()
    owner = _login(client, 947, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="cancel_bool_ad")
    remitter = _login(client, 948, "remitter")
    order = _create_order(client, remitter, ad["id"], key="cancel_bool_order")

    response = client.post(
        f"/api/v1/orders/{order['id']}/cancel",
        headers={**_headers(remitter, "cancel_string_confirmation"), "Content-Type": "application/json"},
        json={"reason": "business_unavailable", "payment_not_sent_confirmed": "true"},
    )

    assert response.status_code == 422
    assert client.app.state.order_repository.get_by_id(order["id"]).status == "waiting_payment"


def test_cancel_after_payment_reported_is_prohibited() -> None:
    client = _client()
    owner = _login(client, 951, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="reported_ad")
    remitter = _login(client, 952, "remitter")
    order = _create_order(client, remitter, ad["id"], key="reported_order")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    client.app.state.order_repository.update_order(stored, paid_reported_at=stored.created_at)

    response = client.post(f"/api/v1/orders/{order['id']}/cancel", headers=_headers(remitter, "cancel_reported"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "ORDER_PAYMENT_ALREADY_REPORTED"


def test_extend_once_then_second_extend_fails() -> None:
    client = _client()
    owner = _login(client, 961, "owner")
    _, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="extend_ad")
    remitter = _login(client, 962, "remitter")
    order = _create_order(client, remitter, ad["id"], key="extend_order")

    extended = client.post(f"/api/v1/orders/{order['id']}/extend-payment-deadline", headers=_headers(remitter, "extend_once"))
    second = client.post(f"/api/v1/orders/{order['id']}/extend-payment-deadline", headers=_headers(remitter, "extend_twice"))

    assert extended.status_code == 200
    assert extended.json()["data"]["order"]["extension_used"] is True
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "ORDER_EXTENSION_ALREADY_USED"
    assert "payment_deadline_extended" in _event_types(client)


def test_waiting_payment_expired_materializes_passively_and_safe_error_on_extend() -> None:
    client = _client()
    owner = _login(client, 971, "owner")
    business, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="expired_order_ad")
    remitter = _login(client, 972, "remitter")
    order = _create_order(client, remitter, ad["id"], key="expired_order")
    stored = client.app.state.order_repository.get_by_id(order["id"])
    client.app.state.order_repository.update_order(
        stored,
        payment_report_deadline_at=stored.created_at - timedelta(minutes=1),
        expires_at=stored.created_at - timedelta(minutes=1),
    )

    detail = client.get(f"/api/v1/orders/{order['id']}", headers=_bearer(remitter, "req_expired_detail"))
    extend = client.post(f"/api/v1/orders/{order['id']}/extend-payment-deadline", headers=_headers(remitter, "extend_expired"))

    assert detail.status_code == 200
    assert detail.json()["data"]["order"]["status"] == "cancelled"
    assert detail.json()["data"]["order"]["cancel_reason"] == "payment_not_reported_in_time"
    assert extend.status_code == 409
    assert extend.json()["error"]["code"] == "ORDER_STATUS_INVALID"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "active"
    assert client.app.state.ad_repository.get_wallet(business["id"]).blocked_credits == 1
    combined = detail.text + extend.text + json.dumps([event.__dict__ for event in client.app.state.audit_writer.events], default=str)
    assert BOT_TOKEN not in combined
    assert JWT_SECRET not in combined
    assert JWT_REFRESH_SECRET not in combined
    assert "owner@example.com" not in combined
    assert "order_expired" in _event_types(client)


def test_waiting_payment_expired_after_ad_lifetime_consumes_credit_and_archives_ad() -> None:
    client = _client()
    owner = _login(client, 973, "owner")
    business, method_id = _approved_business_with_method(client, owner, credits=1)
    ad = _create_ad(client, owner, method_id, key="expired_order_ad_lifetime")
    remitter = _login(client, 974, "remitter")
    order = _create_order(client, remitter, ad["id"], key="expired_order_lifetime")
    stored_order = client.app.state.order_repository.get_by_id(order["id"])
    stored_ad = client.app.state.ad_repository.get_ad(ad["id"])
    stored_ad.expires_at = stored_order.created_at - timedelta(minutes=1)
    client.app.state.order_repository.update_order(
        stored_order,
        payment_report_deadline_at=stored_order.created_at - timedelta(minutes=1),
        expires_at=stored_order.created_at - timedelta(minutes=1),
    )

    detail = client.get(f"/api/v1/orders/{order['id']}", headers=_bearer(remitter, "req_expired_detail_lifetime"))

    assert detail.status_code == 200
    assert detail.json()["data"]["order"]["status"] == "cancelled"
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "archived"
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    assert wallet.blocked_credits == 0
    assert wallet.consumed_credits == 1
    assert {"order_expired", "ad_expired", "credits_consumed"}.issubset(set(_event_types(client)))


def test_migration_0005_contains_required_tables_constraints_and_indexes() -> None:
    migration = open("database/migrations/0005_slice_04_order_creation.up.sql", encoding="utf-8").read()
    for text in [
        "create table if not exists orders",
        "create table if not exists order_state_events",
        "orders_status_check",
        "orders_cancel_reason_check",
        "orders_remitter_idempotency_idx",
        "orders_public_order_code_idx",
        "order_state_events_order_created_idx",
    ]:
        assert text in migration
