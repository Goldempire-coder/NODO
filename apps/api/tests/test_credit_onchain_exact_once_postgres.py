from __future__ import annotations

import os
import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Barrier
from types import SimpleNamespace
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest

from app.core.errors import ApiError
from app.modules.businesses.models import BusinessRecord
from app.modules.credits.business_purchases import CreditBusinessPurchases
from app.modules.credits.models import BASE_USDC_CONTRACT_ADDRESS
from app.modules.credits.onchain import OnchainVerificationResult
from app.modules.credits.postgres_repository import PostgresCreditRepository
from app.modules.credits.schemas import BaseUsdcTxHashRequest
from app.modules.users.models import UserRecord
from app.shared.audit.audit_service import PostgresAuditWriter
from app.shared.idempotency.store import InMemoryIdempotencyStore


POSTGRES_OPT_IN = "NODO_RUN_CREDIT_POSTGRES"
POSTGRES_URL_ENV = "NODO_CREDIT_POSTGRES_URL"
DESTINATION_WALLET = "0x1111111111111111111111111111111111111111"
WRONG_WALLET = "0x9999999999999999999999999999999999999999"
EXPECTED_AMOUNT_UNITS = 10_000_000


@pytest.fixture(scope="module")
def credit_postgres_url() -> str:
    if os.environ.get(POSTGRES_OPT_IN) != "1":
        pytest.skip(f"set {POSTGRES_OPT_IN}=1 for disposable local PostgreSQL validation")
    database_url = os.environ.get(POSTGRES_URL_ENV, "")
    parsed = urlparse(database_url)
    database_name = parsed.path.removeprefix("/").lower()
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not database_name.startswith("nodo_credit_"):
        raise RuntimeError("credit tests require a disposable localhost nodo_credit_* database")
    with psycopg.connect(database_url) as conn:
        current_database = conn.execute("select current_database()").fetchone()[0]
        rows = conn.execute(
            """
            select table_name from information_schema.tables
            where table_schema = 'public'
              and table_name = any(%s)
            """,
            (["audit_logs", "credit_purchases", "credit_purchase_onchain_payments", "credits_ledger"],),
        ).fetchall()
    assert current_database.lower().startswith("nodo_credit_")
    assert {row[0] for row in rows} == {
        "audit_logs",
        "credit_purchases",
        "credit_purchase_onchain_payments",
        "credits_ledger",
    }
    return database_url


def _seed_business(database_url: str, label: str) -> tuple[UserRecord, BusinessRecord]:
    user_id = str(uuid4())
    business_id = str(uuid4())
    now = datetime.now(timezone.utc)
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "insert into users (id, role, status) values (%s, 'business_owner', 'active')",
            (user_id,),
        )
        conn.execute(
            """
            insert into businesses (
                id, owner_user_id, business_name, verification_status, approved_at
            ) values (%s, %s, %s, 'approved', %s)
            """,
            (business_id, user_id, f"Credit Test {label}", now),
        )
        conn.commit()
    return (
        UserRecord(
            id=user_id,
            telegram_id=None,
            username=f"credit_{label}",
            first_name="Credit",
            last_name="Test",
            role="business_owner",
        ),
        BusinessRecord(
            id=business_id,
            owner_user_id=user_id,
            business_name=f"Credit Test {label}",
            rif=None,
            address=None,
            phone=None,
            verification_status="approved",
            approved_at=now,
        ),
    )


def _unique_tx_hash(label: str, business_id: str) -> str:
    return "0x" + hashlib.sha256(f"{label}:{business_id}".encode("utf-8")).hexdigest()


def _verification(
    tx_hash: str,
    *,
    chain_id: int = 8453,
    token: str = BASE_USDC_CONTRACT_ADDRESS,
    destination: str = DESTINATION_WALLET,
    amount_units: int = EXPECTED_AMOUNT_UNITS,
    log_index: int = 0,
) -> OnchainVerificationResult:
    return OnchainVerificationResult(
        chain_id=chain_id,
        token_contract_address=token,
        destination_wallet_address=destination,
        tx_hash=tx_hash,
        tx_from_address="0x2222222222222222222222222222222222222222",
        tx_to_address=destination,
        tx_amount_units=amount_units,
        tx_block_number=123,
        tx_log_index=log_index,
        confirmations=6,
        verification_status="verified",
    )


def _create_purchase(
    repository: PostgresCreditRepository,
    business_id: str,
    label: str,
    *,
    expires_at: datetime | None = None,
):  # type: ignore[no-untyped-def]
    repository.ensure_wallet(business_id)
    units = EXPECTED_AMOUNT_UNITS
    return repository.create_base_usdc_purchase(
        business_id=business_id,
        package_code="starter",
        idempotency_key=f"credit-postgres-{label}",
        expected_amount_units=units,
        destination_wallet_address=DESTINATION_WALLET,
        expires_at=expires_at or datetime.now(timezone.utc) + timedelta(minutes=30),
    )


def _financial_snapshot(database_url: str, *, business_id: str, purchase_id: str) -> dict[str, int | str]:
    with psycopg.connect(database_url) as conn:
        purchase_status = conn.execute(
            "select status from credit_purchases where id = %s",
            (purchase_id,),
        ).fetchone()[0]
        ledger = conn.execute(
            """
            select count(*), coalesce(sum(amount), 0)
            from credits_ledger where related_credit_purchase_id = %s
            """,
            (purchase_id,),
        ).fetchone()
        onchain_count = conn.execute(
            "select count(*) from credit_purchase_onchain_payments where credit_purchase_id = %s",
            (purchase_id,),
        ).fetchone()[0]
        wallet = conn.execute(
            """
            select available_credits, lifetime_purchased_credits
            from credit_wallets where business_id = %s
            """,
            (business_id,),
        ).fetchone()
    return {
        "purchase_status": purchase_status,
        "ledger_count": ledger[0],
        "ledger_amount": ledger[1],
        "onchain_count": onchain_count,
        "available_credits": wallet[0],
        "lifetime_purchased_credits": wallet[1],
    }


def test_postgres_onchain_credit_is_exact_once_under_concurrent_repository_replay(
    credit_postgres_url: str,
) -> None:
    user, business = _seed_business(credit_postgres_url, "repository-race")
    repository = PostgresCreditRepository(credit_postgres_url)
    purchase = _create_purchase(repository, business.id, "repository-race")
    verification = _verification(_unique_tx_hash("repository-race", business.id), log_index=7)
    barrier = Barrier(2)

    def apply_once():  # type: ignore[no-untyped-def]
        barrier.wait(timeout=10)
        return repository.apply_onchain_verification(
            purchase=purchase,
            verification=verification,
            actor_user_id=user.id,
            min_confirmations=3,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: apply_once(), range(2)))

    assert {result[0].status for result in results} == {"credited"}
    assert len({result[1].id for result in results if result[1] is not None}) == 1
    assert _financial_snapshot(
        credit_postgres_url,
        business_id=business.id,
        purchase_id=purchase.id,
    ) == {
        "purchase_status": "credited",
        "ledger_count": 1,
        "ledger_amount": 5,
        "onchain_count": 1,
        "available_credits": 5,
        "lifetime_purchased_credits": 5,
    }


def test_postgres_onchain_transfer_can_credit_only_one_concurrent_purchase(
    credit_postgres_url: str,
) -> None:
    first_user, first_business = _seed_business(credit_postgres_url, "claim-first")
    second_user, second_business = _seed_business(credit_postgres_url, "claim-second")
    repository = PostgresCreditRepository(credit_postgres_url)
    first_purchase = _create_purchase(repository, first_business.id, "claim-first")
    second_purchase = _create_purchase(repository, second_business.id, "claim-second")
    tx_hash = _unique_tx_hash("shared-claim", f"{first_business.id}:{second_business.id}")
    verification = _verification(tx_hash, log_index=9)
    barrier = Barrier(2)

    def claim(purchase, actor_user_id: str) -> str:  # type: ignore[no-untyped-def]
        barrier.wait(timeout=10)
        try:
            repository.apply_onchain_verification(
                purchase=purchase,
                verification=verification,
                actor_user_id=actor_user_id,
                min_confirmations=3,
            )
        except ApiError as exc:
            return exc.code
        return "credited"

    with ThreadPoolExecutor(max_workers=2) as executor:
        first_result = executor.submit(claim, first_purchase, first_user.id)
        second_result = executor.submit(claim, second_purchase, second_user.id)
        outcomes = {first_result.result(), second_result.result()}

    assert outcomes == {"credited", "ONCHAIN_TX_ALREADY_USED"}
    with psycopg.connect(credit_postgres_url) as conn:
        purchase_rows = conn.execute(
            "select status from credit_purchases where id = any(%s)",
            ([first_purchase.id, second_purchase.id],),
        ).fetchall()
        ledger_count = conn.execute(
            "select count(*) from credits_ledger where related_credit_purchase_id = any(%s)",
            ([first_purchase.id, second_purchase.id],),
        ).fetchone()[0]
        wallet_total = conn.execute(
            "select sum(available_credits) from credit_wallets where business_id = any(%s)",
            ([first_business.id, second_business.id],),
        ).fetchone()[0]
        onchain_count = conn.execute(
            """
            select count(*) from credit_purchase_onchain_payments
            where chain_id = 8453 and tx_hash = %s and tx_log_index = 9
            """,
            (tx_hash,),
        ).fetchone()[0]
    assert sorted(row[0] for row in purchase_rows) == ["credited", "pending_payment"]
    assert ledger_count == 1
    assert wallet_total == 5
    assert onchain_count == 1


class _FixedVerifier:
    def __init__(self, verification: OnchainVerificationResult) -> None:
        self.verification = verification
        self.calls = 0

    def verify(self, **_kwargs) -> OnchainVerificationResult:  # type: ignore[no-untyped-def]
        self.calls += 1
        return self.verification


def test_postgres_onchain_service_replay_does_not_duplicate_credit_audit_events(
    credit_postgres_url: str,
) -> None:
    user, business = _seed_business(credit_postgres_url, "service-replay")
    repository = PostgresCreditRepository(credit_postgres_url)
    purchase = _create_purchase(repository, business.id, "service-replay")
    tx_hash = _unique_tx_hash("service-replay", business.id)
    verifier = _FixedVerifier(_verification(tx_hash, log_index=8))
    service = CreditBusinessPurchases(
        settings=SimpleNamespace(onchain_credit_min_confirmations=3),
        repository=repository,
        audit_writer=PostgresAuditWriter(credit_postgres_url),
        idempotency_store=InMemoryIdempotencyStore(),
        storage=None,
        onchain_verifier=verifier,
        rate_limit=lambda _action, _key: None,
        require_idempotency_key=lambda key: key or "",
    )
    barrier = Barrier(2)

    def submit_once(index: int) -> dict:
        barrier.wait(timeout=10)
        return service.submit_base_usdc_tx_hash(
            user=user,
            business=business,
            purchase_id=purchase.id,
            payload=BaseUsdcTxHashRequest(tx_hash=tx_hash),
            request_id=f"credit-postgres-replay-{index}",
            idempotency_key="same-credit-replay",
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(submit_once, range(2)))

    assert responses[0] == responses[1]
    assert responses[0]["credited"] is True
    assert verifier.calls == 1
    with psycopg.connect(credit_postgres_url) as conn:
        audit_rows = conn.execute(
            """
            select event_type, metadata_json from audit_logs
            where resource_type = 'credit_purchase' and resource_id = %s
            order by created_at
            """,
            (purchase.id,),
        ).fetchall()
    assert [row[0] for row in audit_rows] == [
        "onchain_tx_hash_submitted",
        "onchain_credit_purchase_credited",
        "credits_added",
    ]
    assert all(tx_hash not in str(row[1]) for row in audit_rows)
    assert _financial_snapshot(
        credit_postgres_url,
        business_id=business.id,
        purchase_id=purchase.id,
    )["ledger_count"] == 1


@pytest.mark.parametrize(
    ("label", "verification_overrides", "expired", "expected_status", "expected_error"),
    [
        ("wrong-wallet", {"destination": WRONG_WALLET}, False, "verification_failed", "ONCHAIN_WRONG_TOKEN_OR_WALLET"),
        ("wrong-token", {"token": "0x3333333333333333333333333333333333333333"}, False, "verification_failed", "ONCHAIN_WRONG_TOKEN_OR_WALLET"),
        ("wrong-chain", {"chain_id": 1}, False, "verification_failed", "ONCHAIN_WRONG_CHAIN"),
        ("insufficient", {"amount_units": EXPECTED_AMOUNT_UNITS - 1}, False, "verification_failed", "ONCHAIN_VERIFICATION_FAILED"),
        ("expired", {}, True, "under_review", None),
    ],
)
def test_postgres_onchain_verification_fails_closed_without_credit(
    credit_postgres_url: str,
    label: str,
    verification_overrides: dict,
    expired: bool,
    expected_status: str,
    expected_error: str | None,
) -> None:
    user, business = _seed_business(credit_postgres_url, label)
    repository = PostgresCreditRepository(credit_postgres_url)
    expires_at = datetime.now(timezone.utc) - timedelta(minutes=1) if expired else None
    purchase = _create_purchase(repository, business.id, label, expires_at=expires_at)
    tx_hash = _unique_tx_hash(label, business.id)
    verification = _verification(tx_hash, log_index=100 + len(label), **verification_overrides)

    if expected_error is None:
        updated, ledger = repository.apply_onchain_verification(
            purchase=purchase,
            verification=verification,
            actor_user_id=user.id,
            min_confirmations=3,
        )
        assert updated.status == expected_status
        assert ledger is None
    else:
        with pytest.raises(ApiError) as exc_info:
            repository.apply_onchain_verification(
                purchase=purchase,
                verification=verification,
                actor_user_id=user.id,
                min_confirmations=3,
            )
        assert exc_info.value.code == expected_error

    snapshot = _financial_snapshot(
        credit_postgres_url,
        business_id=business.id,
        purchase_id=purchase.id,
    )
    assert snapshot["purchase_status"] == expected_status
    assert snapshot["ledger_count"] == 0
    assert snapshot["ledger_amount"] == 0
    assert snapshot["available_credits"] == 0
    assert snapshot["lifetime_purchased_credits"] == 0
