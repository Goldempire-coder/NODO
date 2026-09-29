from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, replace
from uuid import uuid4

import pytest
import test_chat_disputes as fixtures
from app.core.errors import ApiError
from app.modules.ads.postgres_repository import PostgresAdRepository
from app.modules.chat.models import MessageAttachmentRecord
from app.modules.chat.postgres_repository import PostgresChatRepository
from app.modules.orders.routes_support import order_service
from app.modules.orders.schemas import OrderCreateRequest
from fastapi import Request


def business(client, number):
    owner = fixtures._login(client, number, f"owner_{number}")
    record, method = fixtures._approved_business_with_method(client, owner)
    return owner, record, method


def ad_request(client, owner, method, key):
    return client.post(
        "/api/v1/business/ads",
        headers=fixtures._headers(owner, key),
        json={
            "payment_method_id": method,
            "payment_method": "zelle",
            "delivery_method": "pago_movil_ve",
            "rate_bs_per_usd": "39.5000",
            "amount_min_usd": "20.00",
            "amount_max_usd": "100.00",
        },
    )


def test_create_never_replays_another_business_response():
    client = fixtures._client()
    first, first_business, method = business(client, 88001)
    second, _, _ = business(client, 88002)
    created = ad_request(client, first, method, "same_key")
    assert created.status_code == 201
    replay = ad_request(client, second, method, "same_key")
    assert replay.status_code in (400, 403, 409)
    assert created.json()["data"]["ad"]["id"] not in replay.text
    assert first_business["id"] not in replay.text


@pytest.mark.parametrize("action", ["create", "pause", "archive", "reactivate"])
def test_businesses_can_use_same_key_independently(action):
    client = fixtures._client()
    ads = []
    for number in (88011, 88012):
        owner, record, method = business(client, number)
        response = ad_request(
            client,
            owner,
            method,
            "shared_create" if action == "create" else str(number),
        )
        assert response.status_code == 201, response.text
        ad = response.json()["data"]["ad"]
        if action == "reactivate":
            paused = client.post(
                f"/api/v1/business/ads/{ad['id']}/pause",
                headers=fixtures._headers(owner, f"pause_{number}"),
            )
            assert paused.status_code == 200
        if action != "create":
            response = client.post(
                f"/api/v1/business/ads/{ad['id']}/{action}",
                headers=fixtures._headers(owner, "shared_action"),
            )
            assert response.status_code == 200, response.text
        assert response.json()["data"]["ad"]["business_id"] == record["id"]
        ads.append(response.json()["data"]["ad"]["id"])
    assert ads[0] != ads[1]


def test_pause_loses_race_without_overwriting_order_state(monkeypatch):
    client = fixtures._client()
    owner, _, method = business(client, 88021)
    ad = fixtures._create_ad(client, owner, method)
    repo = client.app.state.ad_repository
    original = repo.set_status
    sender = fixtures._login(client, 88023, "race_sender")
    orders = []
    service = order_service(Request({"type": "http", "app": client.app, "headers": []}))

    def concurrent_status(record, status, **kwargs):
        if status != "paused":
            return original(record, status, **kwargs)
        result = service.create_order(
            user=client.app.state.user_repository.get_user_by_id(sender["user"]["id"]),
            payload=OrderCreateRequest(
                ad_id=record.id,
                amount_usd="50.00",
                receiver_data={
                    "bank": "Banco",
                    "phone": "+584121234567",
                    "document": "V12345678",
                    "holder": "Fictitious",
                },
            ),
            request_id="race_order",
            idempotency_key="race_order",
        )
        orders.append(result["order"])
        return original(record, status, **kwargs)

    monkeypatch.setattr(repo, "set_status", concurrent_status)
    before = sum(
        e.event_type == "ad_paused" for e in client.app.state.audit_writer.events
    )
    response = client.post(
        f"/api/v1/business/ads/{ad['id']}/pause",
        headers=fixtures._headers(owner, "racing_pause"),
    )
    assert response.status_code == 409, response.text
    assert response.json()["error"]["code"] == "AD_STATUS_INVALID"
    assert repo.get_ad(ad["id"]).status == "in_order"
    assert len(orders) == 1
    assert orders[0]["status"] == "waiting_payment"
    assert (
        sum(e.event_type == "ad_paused" for e in client.app.state.audit_writer.events)
        == before
    )


def test_memory_pause_checks_current_record_not_stale_snapshot():
    client = fixtures._client()
    owner, _, method = business(client, 88022)
    ad = fixtures._create_ad(client, owner, method)
    repo = client.app.state.ad_repository
    current = repo.get_ad(ad["id"])
    stale = replace(current)
    current.status = "in_order"
    with pytest.raises(ApiError) as error:
        repo.set_status(stale, "paused", expected_status="active")
    assert error.value.code == "AD_STATUS_INVALID"
    assert current.status == "in_order"


def attachment(order_id, user_id):
    return MessageAttachmentRecord(
        id=str(uuid4()),
        message_id=None,
        order_id=order_id,
        uploaded_by_user_id=user_id,
        file_asset_id=str(uuid4()),
        file_type="message_attachment",
        mime_type="image/png",
        size_bytes=10,
    )


def test_chat_five_attachments_use_one_batch_validation(monkeypatch):
    client = fixtures._client()
    owner, _, method = business(client, 88031)
    ad = fixtures._create_ad(client, owner, method)
    sender = fixtures._login(client, 88032, "sender")
    order = fixtures._create_order(client, sender, ad["id"])
    repo = client.app.state.chat_repository
    records = [attachment(order["id"], sender["user"]["id"]) for _ in range(5)]
    repo.attachments.update({item.id: item for item in records})
    calls = []

    def batch(ids):
        calls.append(ids)
        return {item.id: item for item in records}

    def individual(_):
        pytest.fail("individual attachment validation query")

    monkeypatch.setattr(repo, "get_attachments", batch, raising=False)
    monkeypatch.setattr(repo, "get_attachment", individual)
    monkeypatch.setattr(repo, "attach_to_message", lambda **kwargs: records)
    response = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers=fixtures._headers(sender, "batch_message"),
        json={
            "body": "Fictitious message",
            "attachment_ids": [item.id for item in records],
        },
    )
    assert response.status_code == 201, response.text
    assert calls == [[item.id for item in records]]


class Connection:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []
        self.commits = 0

    def execute(self, sql, params):
        self.calls.append((" ".join(sql.split()), params))
        return self

    def fetchall(self):
        return self.rows

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def commit(self):
        self.commits += 1


def connect_factory(conn, opens):
    @contextmanager
    def connect():
        opens.append(True)
        yield conn

    return connect


def test_postgres_batch_is_one_query_and_filters_deleted(monkeypatch):
    records = [attachment(str(uuid4()), str(uuid4())) for _ in range(5)]
    conn = Connection([asdict(item) for item in records])
    opens = []
    repo = PostgresChatRepository("unused")
    monkeypatch.setattr(repo, "_connect", connect_factory(conn, opens))
    ids = [item.id for item in records]
    result = repo.get_attachments(ids)
    assert set(result) == set(ids)
    assert len(opens) == len(conn.calls) == 1
    sql, params = conn.calls[0]
    assert "id = any(%s)" in sql
    assert "deleted_at is null" in sql
    assert params == (ids,)
    assert repo.get_attachments([]) == {}
    assert len(opens) == 1


def test_postgres_pause_compare_and_set_rejects_no_match(monkeypatch):
    client = fixtures._client()
    owner, _, method = business(client, 88041)
    ad = fixtures._create_ad(client, owner, method)
    stored = client.app.state.ad_repository.get_ad(ad["id"])
    conn = Connection([])
    repo = PostgresAdRepository("unused")
    monkeypatch.setattr(repo, "_connect", connect_factory(conn, []))
    with pytest.raises(ApiError) as error:
        repo.set_status(stored, "paused", expected_status="active")
    assert error.value.code == "AD_STATUS_INVALID"
    assert conn.commits == 0
    assert len(conn.calls) == 1
    sql, params = conn.calls[0]
    assert "and status = %s" in sql
    assert params == ("paused", stored.id, "active")


@pytest.mark.parametrize(
    "invalid", ["missing", "deleted", "other_order", "other_user", "attached"]
)
def test_batch_preserves_attachment_ownership_and_reuse_checks(invalid):
    client = fixtures._client()
    owner, _, method = business(client, 88051)
    ad = fixtures._create_ad(client, owner, method)
    sender = fixtures._login(client, 88052, "attachment_sender")
    order = fixtures._create_order(client, sender, ad["id"])
    repo = client.app.state.chat_repository
    item = attachment(order["id"], sender["user"]["id"])
    if invalid != "missing":
        repo.attachments[item.id] = item
    if invalid == "deleted":
        item.deleted_at = item.created_at
    elif invalid == "other_order":
        item.order_id = str(uuid4())
    elif invalid == "other_user":
        item.uploaded_by_user_id = owner["user"]["id"]
    elif invalid == "attached":
        item.message_id = str(uuid4())
    before = dict(repo.messages)
    response = client.post(
        f"/api/v1/orders/{order['id']}/messages",
        headers=fixtures._headers(sender, "invalid_attachment"),
        json={"body": "Fictitious message", "attachment_ids": [item.id]},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MESSAGE_ATTACHMENT_INVALID"
    assert repo.messages == before
    assert item.file_asset_id not in response.text


def test_same_business_create_replays_without_another_hold_and_rejects_mismatch():
    client = fixtures._client()
    owner, record, method = business(client, 88061)
    first = ad_request(client, owner, method, "retry")
    assert first.status_code == 201
    before = len(client.app.state.ad_repository.ads)
    repeated = ad_request(client, owner, method, "retry")
    assert repeated.status_code == 201
    assert repeated.json()["data"] == first.json()["data"]
    assert len(client.app.state.ad_repository.ads) == before
    assert repeated.json()["data"]["ad"]["business_id"] == record["id"]
    changed = ad_request(client, owner, str(uuid4()), "retry")
    assert changed.status_code == 409
    assert changed.json()["error"]["code"] == "IDEMPOTENCY_PAYLOAD_MISMATCH"


def test_pause_wins_and_subsequent_order_is_rejected():
    client = fixtures._client()
    owner, _, method = business(client, 88071)
    ad = fixtures._create_ad(client, owner, method)
    sender = fixtures._login(client, 88072, "late_sender")
    paused = client.post(
        f"/api/v1/business/ads/{ad['id']}/pause",
        headers=fixtures._headers(owner, "first_pause"),
    )
    assert paused.status_code == 200
    response = client.post(
        "/api/v1/orders",
        headers=fixtures._headers(sender, "late_order"),
        json={
            "ad_id": ad["id"],
            "amount_usd": "50.00",
            "receiver_data": {
                "bank": "Banco",
                "phone": "+584121234567",
                "document": "V12345678",
                "holder": "Fictitious",
            },
        },
    )
    assert response.status_code == 409
    assert client.app.state.ad_repository.get_ad(ad["id"]).status == "paused"


def test_postgres_pause_success_commits_once(monkeypatch):
    client = fixtures._client()
    owner, _, method = business(client, 88081)
    ad = fixtures._create_ad(client, owner, method)
    stored = client.app.state.ad_repository.get_ad(ad["id"])
    conn = Connection([asdict(replace(stored, status="paused"))])
    repo = PostgresAdRepository("unused")
    monkeypatch.setattr(repo, "_connect", connect_factory(conn, []))
    result = repo.set_status(stored, "paused", expected_status="active")
    assert result.status == "paused"
    assert result.id == stored.id
    assert conn.commits == 1
    assert len(conn.calls) == 1
