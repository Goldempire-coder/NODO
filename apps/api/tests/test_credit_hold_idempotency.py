from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from app.core.errors import ApiError
from app.modules.ads.postgres_credit_holds import PostgresAdCreditHoldsMixin
from app.modules.ads.postgres_repository import PostgresAdRepository
from app.shared.db import connection


class SyntheticConnection:
    """Model a committed competitor at the wallet lock, not a PostgreSQL server."""

    closed = False

    def __init__(self, blocked=8):
        self.wallet = {
            "available_credits": 10,
            "blocked_credits": blocked,
            "consumed_credits": 0,
        }
        self.ledger = []
        self.ads = {}
        self.calls = []
        self.before_lock = None
        self.fail_insert = False
        self.commits = 0
        self.rollbacks = 0
        self.initial_wallet = deepcopy(self.wallet)

    def execute(self, sql, parameters):
        sql = " ".join(sql.split())
        self.calls.append(sql)
        row = None
        if sql.startswith("select") and "from credits_ledger" in sql:
            kind = next(k for k in ("release", "consume", "expire") if f"'{k}'" in sql)
            key = "related_order_id" if kind == "consume" else "related_ad_id"
            row = next(
                (
                    r
                    for r in self.ledger
                    if r["type"] == kind and r[key] == parameters[0]
                ),
                None,
            )
        elif sql.startswith("select * from credit_wallets"):
            assert "for update" in sql
            competing = self.before_lock
            self.before_lock = None
            if competing is not None:
                competing()
            row = self.wallet
        elif sql.startswith("update credit_wallets"):
            if "set available_credits" in sql:
                self.wallet.update(
                    available_credits=parameters[0], blocked_credits=parameters[1]
                )
            else:
                self.wallet.update(
                    blocked_credits=parameters[0], consumed_credits=parameters[1]
                )
        elif sql.startswith("insert into credits_ledger"):
            if self.fail_insert:
                raise RuntimeError("synthetic ledger failure")
            kind = next(k for k in ("release", "consume", "expire") if f"'{k}'" in sql)
            row = {
                "id": f"ledger-{len(self.ledger) + 1}",
                "business_id": parameters[0],
                "type": kind,
                "amount": parameters[1],
                "available_before": parameters[2],
                "available_after": parameters[3],
                "blocked_before": parameters[4],
                "blocked_after": parameters[5],
                "consumed_before": parameters[6],
                "consumed_after": parameters[7],
                "related_ad_id": parameters[8],
                "related_order_id": parameters[9],
                "reason": parameters[10],
                "source": parameters[11],
                "reference_type": "order" if kind == "consume" else parameters[12],
                "reference_id": parameters[12 if kind == "consume" else 13],
                "created_by": parameters[-1],
                "created_at": datetime(2026, 9, 28, tzinfo=timezone.utc),
            }
            self.ledger.append(row)
        elif sql.startswith("update ads"):
            self.ads[parameters[-1]] = {
                "status": "archived",
                "credit_consumed_ledger_id": parameters[0]
                if len(parameters) == 2
                else None,
            }
        else:
            raise AssertionError(f"Unexpected synthetic query: {sql}")
        result = deepcopy(row)
        return SimpleNamespace(fetchone=lambda: result)

    def commit(self):
        self.commits += 1

    def rollback(self):
        self.rollbacks += 1
        self.wallet = deepcopy(self.initial_wallet)
        self.ledger.clear()
        self.ads.clear()


def ad(ad_id="synthetic-ad"):
    return SimpleNamespace(
        id=ad_id,
        business_id="synthetic-business",
        required_credits=2,
        credit_hold_ledger_id=f"hold-{ad_id}",
    )


def invoke(repo, conn, kind, record=None):
    record = record or ad()
    arguments = {"ad": record, "created_by": "synthetic-admin"}
    if kind == "consume":
        return repo.consume_hold_for_order_in_transaction(
            conn, order_id=f"order-{record.id}", **arguments
        )
    return getattr(repo, f"{kind}_hold_in_transaction")(conn, **arguments)


def assert_duplicate(repo, conn, kind):
    if kind == "consume":
        with pytest.raises(ApiError) as error:
            invoke(repo, conn, kind)
        assert (error.value.code, error.value.status_code) == (
            "CREDIT_ALREADY_CONSUMED",
            409,
        )
    else:
        assert invoke(repo, conn, kind) is None


@pytest.mark.parametrize("kind", ["release", "consume", "expire"])
@pytest.mark.parametrize("blocked", [8, 2])
def test_competitor_commits_between_initial_read_and_wallet_lock(kind, blocked):
    repo = PostgresAdCreditHoldsMixin()
    conn = SyntheticConnection(blocked)
    conn.before_lock = lambda: invoke(repo, conn, kind)

    assert_duplicate(repo, conn, kind)

    assert len(conn.ledger) == 1
    assert conn.wallet == {
        "available_credits": 12 if kind == "release" else 10,
        "blocked_credits": blocked - 2,
        "consumed_credits": 0 if kind == "release" else 2,
    }
    assert sum(sql.startswith("update credit_wallets") for sql in conn.calls) == 1


@pytest.mark.parametrize("kind", ["release", "consume", "expire"])
def test_sequential_duplicate_keeps_existing_contract_and_original_movement(kind):
    repo = PostgresAdCreditHoldsMixin()
    conn = SyntheticConnection()
    first = invoke(repo, conn, kind)
    before = deepcopy((conn.wallet, conn.ledger))
    conn.calls.clear()

    assert_duplicate(repo, conn, kind)

    assert (conn.wallet, conn.ledger) == before
    assert first["type"] == kind
    assert not any("for update" in sql for sql in conn.calls)
    if kind != "release":
        assert conn.ads[ad().id]["credit_consumed_ledger_id"] == first["id"]


@pytest.mark.parametrize("kind", ["release", "consume", "expire"])
def test_other_ad_in_same_wallet_still_gets_its_own_movement(kind):
    repo = PostgresAdCreditHoldsMixin()
    conn = SyntheticConnection()
    conn.before_lock = lambda: invoke(repo, conn, kind, ad("other-ad"))

    result = invoke(repo, conn, kind)

    assert result["related_ad_id"] == ad().id
    assert len(conn.ledger) == 2
    assert conn.wallet["blocked_credits"] == 4
    assert conn.wallet["available_credits"] == (14 if kind == "release" else 10)
    assert conn.wallet["consumed_credits"] == (0 if kind == "release" else 4)


@pytest.mark.parametrize("kind", ["release", "consume", "expire"])
def test_insufficient_hold_never_changes_credit_balances(kind):
    repo = PostgresAdCreditHoldsMixin()
    conn = SyntheticConnection(blocked=1)
    if kind == "consume":
        with pytest.raises(ApiError) as error:
            invoke(repo, conn, kind)
        assert (error.value.code, error.value.status_code) == (
            "CREDIT_HOLD_NOT_FOUND",
            409,
        )
    else:
        assert invoke(repo, conn, kind) is None
    assert conn.wallet == conn.initial_wallet
    assert not conn.ledger


@pytest.mark.parametrize("kind", ["release", "consume", "expire"])
def test_ledger_failure_rolls_back_outer_repository_transaction(monkeypatch, kind):
    conn = SyntheticConnection()
    conn.fail_insert = True
    pool = SimpleNamespace(acquire=lambda: conn, release=Mock())
    monkeypatch.setattr(connection, "_pool_for", lambda _: pool)
    repo = PostgresAdRepository("synthetic-credit-holds")
    arguments = {"ad": ad(), "created_by": "synthetic-admin"}
    method = getattr(
        repo, "consume_hold_for_order" if kind == "consume" else f"{kind}_hold"
    )
    if kind == "consume":
        arguments["order_id"] = "synthetic-order"

    with pytest.raises(RuntimeError, match="synthetic ledger failure"):
        method(**arguments)

    assert conn.commits == 0
    assert conn.rollbacks == 1
    assert conn.wallet == conn.initial_wallet
    assert not conn.ledger and not conn.ads
    pool.release.assert_called_once_with(conn)
