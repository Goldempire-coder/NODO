from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest

from app.modules.credits.postgres_repository import PostgresCreditRepository


POSTGRES_OPT_IN = "NODO_RUN_CREDIT_POSTGRES"
POSTGRES_URL_ENV = "NODO_CREDIT_POSTGRES_URL"


@pytest.fixture(scope="module")
def referral_postgres_url() -> str:
    if os.environ.get(POSTGRES_OPT_IN) != "1":
        pytest.skip(f"set {POSTGRES_OPT_IN}=1 for disposable local PostgreSQL validation")
    database_url = os.environ.get(POSTGRES_URL_ENV, "")
    parsed = urlparse(database_url)
    database_name = parsed.path.removeprefix("/").lower()
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not database_name.startswith("nodo_credit_"):
        raise RuntimeError("referral tests require a disposable localhost nodo_credit_* database")
    with psycopg.connect(database_url) as conn:
        tables = conn.execute(
            """
            select table_name from information_schema.tables
            where table_schema = 'public'
              and table_name = any(%s)
            """,
            (["businesses", "referral_codes", "referral_events", "credit_wallets", "credits_ledger"],),
        ).fetchall()
    assert {row[0] for row in tables} == {
        "businesses",
        "referral_codes",
        "referral_events",
        "credit_wallets",
        "credits_ledger",
    }
    return database_url


def _seed_business(database_url: str, label: str, *, approved: bool) -> tuple[str, str]:
    user_id = str(uuid4())
    business_id = str(uuid4())
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "insert into users (id, role, status) values (%s, 'business_owner', 'active')",
            (user_id,),
        )
        conn.execute(
            """
            insert into businesses (
                id, owner_user_id, business_name, verification_status, approved_at
            ) values (%s, %s, %s, %s, case when %s then now() else null end)
            """,
            (business_id, user_id, f"Referral Test {label}", "approved" if approved else "pending", approved),
        )
        conn.commit()
    return user_id, business_id


def test_postgres_business_approval_and_referral_credit_are_exact_once_under_replay(
    referral_postgres_url: str,
) -> None:
    actor_user_id, referrer_id = _seed_business(referral_postgres_url, "referrer-race", approved=True)
    _, referred_id = _seed_business(referral_postgres_url, "referred-race", approved=False)
    repository = PostgresCreditRepository(referral_postgres_url)
    code = repository.get_or_create_referral_code(referrer_id)
    barrier = Barrier(2)

    def approve_once():  # type: ignore[no-untyped-def]
        barrier.wait(timeout=10)
        return repository.award_referral_on_business_approval(
            referred_business_id=referred_id,
            referral_code=f"  {code.code.lower()}  ",
            actor_user_id=actor_user_id,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: approve_once(), range(2)))

    assert sorted(result.created for result in results) == [False, True]
    assert sorted(result.business_approved for result in results) == [False, True]
    assert len({result.event.id for result in results if result.event is not None}) == 1
    with psycopg.connect(referral_postgres_url) as conn:
        referred_status = conn.execute(
            "select verification_status from businesses where id = %s",
            (referred_id,),
        ).fetchone()[0]
        referrer = conn.execute(
            "select referral_credits_earned from businesses where id = %s",
            (referrer_id,),
        ).fetchone()
        wallet = conn.execute(
            "select available_credits, lifetime_bonus_credits from credit_wallets where business_id = %s",
            (referrer_id,),
        ).fetchone()
        events = conn.execute(
            "select status, credits_awarded from referral_events where referred_business_id = %s",
            (referred_id,),
        ).fetchall()
        ledger = conn.execute(
            "select type, amount from credits_ledger where business_id = %s and type = 'referral_bonus'",
            (referrer_id,),
        ).fetchall()
        referred_wallet = conn.execute(
            "select available_credits from credit_wallets where business_id = %s",
            (referred_id,),
        ).fetchone()

    assert referred_status == "approved"
    assert referrer[0] == 5
    assert tuple(wallet) == (5, 5)
    assert [tuple(row) for row in events] == [("rewarded", 5)]
    assert [tuple(row) for row in ledger] == [("referral_bonus", 5)]
    assert referred_wallet is None or referred_wallet[0] == 0


def test_postgres_referral_cap_partial_award_and_invalid_code_fail_closed(
    referral_postgres_url: str,
) -> None:
    actor_user_id, referrer_id = _seed_business(referral_postgres_url, "referrer-cap", approved=True)
    _, partial_referred_id = _seed_business(referral_postgres_url, "referred-partial", approved=False)
    _, capped_referred_id = _seed_business(referral_postgres_url, "referred-capped", approved=False)
    _, invalid_referred_id = _seed_business(referral_postgres_url, "referred-invalid", approved=False)
    repository = PostgresCreditRepository(referral_postgres_url)
    code = repository.get_or_create_referral_code(referrer_id)
    with psycopg.connect(referral_postgres_url) as conn:
        conn.execute(
            "update businesses set referral_credits_earned = 18 where id = %s",
            (referrer_id,),
        )
        conn.commit()

    partial = repository.award_referral_on_business_approval(
        referred_business_id=partial_referred_id,
        referral_code=code.code,
        actor_user_id=actor_user_id,
    )
    capped = repository.award_referral_on_business_approval(
        referred_business_id=capped_referred_id,
        referral_code=code.code,
        actor_user_id=actor_user_id,
    )
    invalid = repository.award_referral_on_business_approval(
        referred_business_id=invalid_referred_id,
        referral_code="DOES-NOT-EXIST",
        actor_user_id=actor_user_id,
    )

    assert partial.event is not None and partial.event.credits_awarded == 2
    assert capped.event is not None and capped.event.status == "rejected"
    assert capped.event.reject_reason == "referral_cap_reached"
    assert invalid.event is None and invalid.outcome == "invalid_code"
    with psycopg.connect(referral_postgres_url) as conn:
        referrer = conn.execute(
            "select referral_credits_earned from businesses where id = %s",
            (referrer_id,),
        ).fetchone()
        ledger = conn.execute(
            "select count(*), coalesce(sum(amount), 0) from credits_ledger where business_id = %s and type = 'referral_bonus'",
            (referrer_id,),
        ).fetchone()
        invalid_event_count = conn.execute(
            "select count(*) from referral_events where referred_business_id = %s",
            (invalid_referred_id,),
        ).fetchone()[0]
        invalid_status = conn.execute(
            "select verification_status from businesses where id = %s",
            (invalid_referred_id,),
        ).fetchone()[0]

    assert referrer[0] == 20
    assert tuple(ledger) == (1, 2)
    assert invalid_event_count == 0
    assert invalid_status == "approved"


def test_postgres_legacy_pending_events_finalize_once_and_keep_terminal_states(
    referral_postgres_url: str,
) -> None:
    actor_user_id, referrer_id = _seed_business(referral_postgres_url, "legacy-referrer", approved=True)
    _, rewarded_referred_id = _seed_business(referral_postgres_url, "legacy-rewarded", approved=False)
    _, rejected_referred_id = _seed_business(referral_postgres_url, "legacy-rejected", approved=False)
    repository = PostgresCreditRepository(referral_postgres_url)
    code = repository.get_or_create_referral_code(referrer_id)
    rewarded_pending = repository.apply_referral_code(
        referred_business_id=rewarded_referred_id,
        referral_code=code.code,
    )
    with psycopg.connect(referral_postgres_url) as conn:
        conn.execute(
            "update businesses set referral_credits_earned = 18 where id = %s",
            (referrer_id,),
        )
        conn.commit()

    rewarded = repository.award_referral_on_business_approval(
        referred_business_id=rewarded_referred_id,
        referral_code=code.code,
        actor_user_id=actor_user_id,
    )
    rewarded_replay = repository.award_referral_on_business_approval(
        referred_business_id=rewarded_referred_id,
        referral_code=code.code,
        actor_user_id=actor_user_id,
    )
    rejected_pending = repository.apply_referral_code(
        referred_business_id=rejected_referred_id,
        referral_code=code.code,
    )
    rejected = repository.award_referral_on_business_approval(
        referred_business_id=rejected_referred_id,
        referral_code=code.code,
        actor_user_id=actor_user_id,
    )
    rejected_replay = repository.award_referral_on_business_approval(
        referred_business_id=rejected_referred_id,
        referral_code=code.code,
        actor_user_id=actor_user_id,
    )

    assert rewarded.event is not None and rewarded.event.id == rewarded_pending.id
    assert rewarded.event.status == "rewarded"
    assert rewarded.event.credits_awarded == 2
    assert rewarded.created is False and rewarded.event_changed is True
    assert rewarded_replay.outcome == "already_processed"
    assert rewarded_replay.event_changed is False
    assert rejected.event is not None and rejected.event.id == rejected_pending.id
    assert rejected.event.status == "rejected"
    assert rejected.event.reject_reason == "referral_cap_reached"
    assert rejected.created is False and rejected.event_changed is True
    assert rejected_replay.outcome == "already_processed"
    assert rejected_replay.event_changed is False
    with psycopg.connect(referral_postgres_url) as conn:
        referrer = conn.execute(
            "select referral_credits_earned from businesses where id = %s",
            (referrer_id,),
        ).fetchone()
        wallet = conn.execute(
            "select available_credits, lifetime_bonus_credits from credit_wallets where business_id = %s",
            (referrer_id,),
        ).fetchone()
        events = conn.execute(
            """
            select referred_business_id, status, credits_awarded
            from referral_events
            where referrer_business_id = %s
            order by referred_business_id
            """,
            (referrer_id,),
        ).fetchall()
        ledger = conn.execute(
            "select count(*), coalesce(sum(amount), 0) from credits_ledger where business_id = %s and type = 'referral_bonus'",
            (referrer_id,),
        ).fetchone()

    assert referrer[0] == 20
    assert tuple(wallet) == (2, 2)
    assert sorted((row[1], row[2]) for row in events) == [("rejected", 0), ("rewarded", 2)]
    assert tuple(ledger) == (1, 2)
