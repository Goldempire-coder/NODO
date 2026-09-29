from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock

import pytest
from test_business_order_ops import (
    _approved_business_with_method,
    _client,
    _create_ad,
    _create_order,
    _headers,
    _login,
    _report_payment,
)


def _ad_payload(method_id: str) -> dict:
    return {
        "payment_method_id": method_id,
        "payment_method": "zelle",
        "delivery_method": "pago_movil_ve",
        "rate_bs_per_usd": "39.5000",
        "amount_min_usd": "20.00",
        "amount_max_usd": "100.00",
    }


@pytest.mark.parametrize("founder_status", ["active", "expired", "revoked", None])
def test_founder_metadata_never_exempts_publication_credit_hold(founder_status):
    client = _client()
    owner = _login(client, 87001, "owner_retired_founder")
    business, method_id = _approved_business_with_method(client, owner, credits=0)
    stored = client.app.state.business_repository.get_business(business["id"])
    stored.founder_status = founder_status
    stored.founder_expires_at = stored.created_at + timedelta(days=30)

    response = client.post(
        "/api/v1/business/ads",
        headers=_headers(owner, "founder_without_credits"),
        json=_ad_payload(method_id),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "CREDIT_BALANCE_INSUFFICIENT"
    repository = client.app.state.ad_repository
    assert repository.ads == {}
    wallet = repository.get_wallet(business["id"])
    assert (
        wallet.available_credits,
        wallet.blocked_credits,
        wallet.consumed_credits,
    ) == (0, 0, 0)
    assert stored.founder_status == founder_status
    assert not any(
        event.event_type in {"founder_free_use", "ad_published", "credits_held"}
        for event in client.app.state.audit_writer.events
    )


def test_manual_admin_credits_publish_and_confirm_once_with_founder_history():
    client = _client()
    owner = _login(client, 87002, "owner_manual_credits")
    business, method_id = _approved_business_with_method(client, owner, credits=0)
    stored = client.app.state.business_repository.get_business(business["id"])
    stored.founder_status = "active"
    stored.founder_expires_at = stored.created_at + timedelta(days=30)
    admin = _login(client, 87003, "admin_manual_credits")
    client.app.state.user_repository.set_user_role(admin["user"]["id"], "super_admin")
    adjustment = {
        "business_id": business["id"],
        "amount": 3,
        "direction": "add",
        "reason": "owner_initial_business_credit_assignment",
    }
    for _ in range(2):
        grant = client.post(
            "/api/v1/admin/credits/adjust",
            headers=_headers(admin, "manual_initial_grant"),
            json=adjustment,
        )
        assert grant.status_code == 200, grant.text
    repository = client.app.state.ad_repository
    wallet = repository.get_wallet(business["id"])
    assert wallet.available_credits == 3
    ad = _create_ad(client, owner, method_id, key="manual_grant_ad")
    stored_ad = repository.get_ad(ad["id"])
    assert stored_ad.credit_hold_ledger_id is not None
    assert (
        wallet.available_credits,
        wallet.blocked_credits,
        wallet.consumed_credits,
    ) == (2, 1, 0)

    remitter = _login(client, 87004, "remitter_manual_credits")
    order = _create_order(client, remitter, ad["id"], key="manual_grant_order")
    _report_payment(client, remitter, order, key="manual_grant_report")
    for _ in range(2):
        confirmed = client.post(
            f"/api/v1/business/orders/{order['id']}/confirm-payment",
            headers=_headers(owner, "manual_grant_confirm"),
            json={"reason": "Ingreso verificado"},
        )
        assert confirmed.status_code == 200, confirmed.text
    assert (
        wallet.available_credits,
        wallet.blocked_credits,
        wallet.consumed_credits,
    ) == (2, 0, 1)
    assert stored_ad.credit_consumed_ledger_id is not None
    events = [event.event_type for event in client.app.state.audit_writer.events]
    assert events.count("credits_held") == 1
    assert events.count("credits_consumed") == 1
    assert "founder_free_use" not in events
    assert stored.founder_status == "active"


@pytest.mark.parametrize("available", [0, 3])
def test_postgres_publication_always_requires_and_attaches_hold(available):
    from app.core.errors import ApiError
    from app.modules.ads.postgres_publish import PostgresAdPublishMixin

    now = datetime.now(timezone.utc)
    fields = dict(
        _ad_payload("method"),
        business_id="business",
        required_credits=1,
        created_by="owner",
    )
    row = {
        **fields,
        "id": "ad",
        "status": "active",
        "credit_hold_ledger_id": None,
        "credit_consumed_ledger_id": None,
        "created_at": now,
        "updated_at": now,
        "activated_at": now,
        "expires_at": now + timedelta(days=7),
        "last_rate_updated_at": now,
    }
    conn = MagicMock()
    conn.__enter__.return_value = conn
    conn.execute.return_value.fetchone.side_effect = [
        {"available_credits": available, "blocked_credits": 2, "consumed_credits": 4},
        row,
        {"id": "hold"},
        {**row, "credit_hold_ledger_id": "hold"},
    ]
    repository = PostgresAdPublishMixin()
    repository._connect = Mock(return_value=conn)
    repository._require_active_candidate_in_transaction = Mock()
    if available == 0:
        with pytest.raises(ApiError) as caught:
            repository.publish_ad(**fields)
        assert caught.value.code == "CREDIT_BALANCE_INSUFFICIENT"
        conn.rollback.assert_called_once()
        conn.commit.assert_not_called()
        assert conn.execute.call_count == 1
    else:
        ad = repository.publish_ad(**fields)
        assert ad.credit_hold_ledger_id == "hold"
        queries = conn.execute.call_args_list
        assert len(queries) == 5
        assert "update credit_wallets" in queries[2].args[0]
        assert queries[2].args[1] == (2, 3, "business")
        assert "insert into credits_ledger" in queries[3].args[0]
        assert queries[3].args[1] == (
            "business",
            "hold",
            1,
            3,
            2,
            2,
            3,
            4,
            4,
            "ad",
            "ad_publish_credit_hold",
            "ad",
            "owner",
        )
        assert "credit_hold_ledger_id" in queries[4].args[0]
        assert queries[4].args[1] == ("hold", "ad")
        conn.commit.assert_called_once()
        conn.rollback.assert_not_called()
    repository._require_active_candidate_in_transaction.assert_called_once_with(
        conn,
        business_id="business",
        payment_method="zelle",
        amount_max_usd="100.00",
        enforce_publication_access=True,
    )


def test_postgres_order_transition_rechecks_credit_hold_atomically():
    from app.core.errors import ApiError
    from app.modules.orders.postgres_create_order import PostgresCreateOrderMixin

    conn = MagicMock()
    conn.execute.return_value.fetchone.return_value = None
    with pytest.raises(ApiError) as caught:
        PostgresCreateOrderMixin()._move_ad_to_in_order_or_raise(conn, ad_id="legacy")
    assert caught.value.code == "AD_NOT_AVAILABLE"
    query, params = conn.execute.call_args.args
    assert "status = 'active'" in query
    assert "credit_hold_ledger_id is not null" in query
    assert params == ("legacy",)
    conn.rollback.assert_called_once()
    conn.commit.assert_not_called()


def test_legacy_ad_without_hold_cannot_open_new_order_or_spend_other_credits():
    client = _client()
    owner = _login(client, 87005, "owner_legacy_ad")
    business, method_id = _approved_business_with_method(client, owner, credits=3)
    ad = _create_ad(client, owner, method_id, key="legacy_ad")
    stored_ad = client.app.state.ad_repository.get_ad(ad["id"])
    # Simulate a historical no-hold ad; the wallet must not supply an unrelated hold.
    stored_ad.credit_hold_ledger_id = None
    remitter = _login(client, 87006, "remitter_legacy_ad")
    events_before = len(client.app.state.audit_writer.events)
    response = client.post(
        "/api/v1/orders",
        headers=_headers(remitter, "legacy_order"),
        json={"ad_id": ad["id"], "amount_usd": "50.00"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "AD_NOT_AVAILABLE"
    assert client.app.state.order_repository.orders == {}
    assert stored_ad.status == "active"
    assert stored_ad.credit_consumed_ledger_id is None
    assert len(client.app.state.audit_writer.events) == events_before
    wallet = client.app.state.ad_repository.get_wallet(business["id"])
    assert (
        wallet.available_credits,
        wallet.blocked_credits,
        wallet.consumed_credits,
    ) == (2, 1, 0)
