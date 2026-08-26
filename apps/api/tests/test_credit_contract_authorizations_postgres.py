from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Barrier
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest
from app.core.errors import ApiError
from app.modules.credits.payment_authorizations import (
    PaymentAuthorizationSnapshot,
    sign_payment_authorization,
)
from app.modules.credits.postgres_repository import PostgresCreditRepository
from eth_account import Account

POSTGRES_OPT_IN = "NODO_RUN_CREDIT_POSTGRES"
POSTGRES_URL_ENV = "NODO_CREDIT_POSTGRES_URL"
TREASURY = "0x1111111111111111111111111111111111111111"
PAYER = "0x2222222222222222222222222222222222222222"
CONTRACT = "0x3333333333333333333333333333333333333333"
BASE_SEPOLIA_USDC = "0x036cbd53842c5426634e7929541ec2318f3dcf7e"
ROOT = Path(__file__).resolve().parents[3]
MIGRATION_UP = ROOT / "database" / "migrations" / "0057_crypto_credit_contract_authorizations.up.sql"
MIGRATION_DOWN = ROOT / "database" / "migrations" / "0057_crypto_credit_contract_authorizations.down.sql"


@pytest.fixture(scope="module")
def credit_postgres_url() -> str:
    if os.environ.get(POSTGRES_OPT_IN) != "1":
        pytest.skip(f"set {POSTGRES_OPT_IN}=1 for disposable local PostgreSQL validation")
    database_url = os.environ.get(POSTGRES_URL_ENV, "")
    parsed = urlparse(database_url)
    database_name = parsed.path.removeprefix("/").lower()
    if parsed.hostname not in {"127.0.0.1", "localhost"} or not database_name.startswith("nodo_credit_"):
        raise RuntimeError("credit tests require a disposable localhost nodo_credit_* database")
    return database_url


def _seed_business(database_url: str) -> str:
    user_id = str(uuid4())
    business_id = str(uuid4())
    with psycopg.connect(database_url) as conn:
        conn.execute("insert into users (id, role, status) values (%s, 'business_owner', 'active')", (user_id,))
        conn.execute(
            """
            insert into businesses (id, owner_user_id, business_name, verification_status, approved_at)
            values (%s, %s, %s, 'approved', now())
            """,
            (business_id, user_id, "52C1 Contract Purchase"),
        )
        conn.commit()
    return business_id


def _candidate(repository: PostgresCreditRepository, *, business_id: str, idempotency_key: str):  # type: ignore[no-untyped-def]
    signer = Account.create()
    signed_at = datetime.now(timezone.utc)
    expires_at = signed_at + timedelta(minutes=15)
    snapshot = PaymentAuthorizationSnapshot(
        purchase_ref="0x" + uuid4().hex + uuid4().hex,
        payer=PAYER,
        amount=10_000_000,
        valid_until=int(expires_at.timestamp()),
        chain_id=84532,
        verifying_contract=CONTRACT,
        contract_version=2,
    )
    signed = sign_payment_authorization(
        snapshot,
        signer_key=signer.key.hex(),
        configured_signer_address=signer.address,
    )
    return repository.create_contract_purchase(
        business_id=business_id,
        package_code="starter",
        idempotency_key=idempotency_key,
        expected_amount_units=snapshot.amount,
        chain_id=84532,
        network="base_sepolia",
        token_symbol="USDC",
        token_contract_address=BASE_SEPOLIA_USDC,
        token_decimals=6,
        destination_wallet_address=TREASURY,
        purchase_ref=snapshot.purchase_ref,
        payer_address=PAYER,
        contract_address=CONTRACT,
        contract_version=2,
        authorization_expires_at=expires_at,
        authorization_digest=signed.digest,
        authorization_signature=signed.signature,
        signer_address=signed.signer_address,
        signer_version="postgres-test-v1",
        signed_at=signed_at,
    )


def test_postgres_contract_purchase_replay_is_exact_once_without_credit(
    credit_postgres_url: str,
) -> None:
    business_id = _seed_business(credit_postgres_url)
    repository = PostgresCreditRepository(credit_postgres_url)
    idempotency_key = f"contract-{uuid4()}"
    barrier = Barrier(2)

    def create_once():  # type: ignore[no-untyped-def]
        barrier.wait(timeout=10)
        return _candidate(repository, business_id=business_id, idempotency_key=idempotency_key)

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: create_once(), range(2)))

    purchases = [result[0] for result in results]
    assert len({purchase.id for purchase in purchases}) == 1
    assert len({purchase.onchain_purchase_ref for purchase in purchases}) == 1
    assert len({purchase.payment_authorization_signature for purchase in purchases}) == 1
    assert sorted(result[1] for result in results) == [False, True]

    purchase = purchases[0]
    with psycopg.connect(credit_postgres_url) as conn:
        purchase_count = conn.execute(
            "select count(*) from credit_purchases where business_id = %s and idempotency_key = %s",
            (business_id, idempotency_key),
        ).fetchone()[0]
        ledger_count = conn.execute(
            "select count(*) from credits_ledger where related_credit_purchase_id = %s",
            (purchase.id,),
        ).fetchone()[0]
        wallet_count = conn.execute(
            "select count(*) from credit_wallets where business_id = %s",
            (business_id,),
        ).fetchone()[0]
    assert purchase_count == 1
    assert ledger_count == 0
    assert wallet_count == 0
    assert purchase.chain_id == 84532
    assert purchase.network == "base_sepolia"
    assert purchase.token_contract_address == BASE_SEPOLIA_USDC

    with pytest.raises(ApiError) as mismatch:
        repository.create_contract_purchase(
            business_id=business_id,
            package_code="pro",
            idempotency_key=idempotency_key,
            expected_amount_units=25_000_000,
            chain_id=84532,
            network="base_sepolia",
            token_symbol="USDC",
            token_contract_address=BASE_SEPOLIA_USDC,
            token_decimals=6,
            destination_wallet_address=TREASURY,
            purchase_ref="0x" + uuid4().hex + uuid4().hex,
            payer_address=PAYER,
            contract_address=CONTRACT,
            contract_version=2,
            authorization_expires_at=datetime.now(timezone.utc) + timedelta(minutes=15),
            authorization_digest="0x" + "a" * 64,
            authorization_signature="0x" + "b" * 130,
            signer_address="0x4444444444444444444444444444444444444444",
            signer_version="postgres-test-v1",
            signed_at=datetime.now(timezone.utc),
        )
    assert mismatch.value.code == "IDEMPOTENCY_PAYLOAD_MISMATCH"


def test_postgres_contract_pending_limit_is_atomic_under_concurrency(
    credit_postgres_url: str,
) -> None:
    business_id = _seed_business(credit_postgres_url)
    repository = PostgresCreditRepository(credit_postgres_url)
    barrier = Barrier(4)

    def create_once(index: int):  # type: ignore[no-untyped-def]
        barrier.wait(timeout=10)
        try:
            return _candidate(
                repository,
                business_id=business_id,
                idempotency_key=f"pending-limit-{index}-{uuid4()}",
            )
        except ApiError as exc:
            return exc

    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(create_once, range(4)))

    purchases = [result[0] for result in results if isinstance(result, tuple)]
    errors = [result for result in results if isinstance(result, ApiError)]
    assert len(purchases) == 3
    assert [error.code for error in errors] == ["CRYPTO_PAYMENT_PENDING_LIMIT_REACHED"]
    assert repository.count_pending_contract_purchases(business_id) == 3

    with psycopg.connect(credit_postgres_url) as conn:
        purchase_ids = [purchase.id for purchase in purchases]
        ledger_count = conn.execute(
            "select count(*) from credits_ledger where related_credit_purchase_id = any(%s::uuid[])",
            (purchase_ids,),
        ).fetchone()[0]
        wallet_count = conn.execute(
            "select count(*) from credit_wallets where business_id = %s",
            (business_id,),
        ).fetchone()[0]
    assert ledger_count == 0
    assert wallet_count == 0


def test_contract_purchase_migration_constraints_are_canonical() -> None:
    up = MIGRATION_UP.read_text(encoding="utf-8")
    down = MIGRATION_DOWN.read_text(encoding="utf-8")
    repository_source = (ROOT / "apps" / "api" / "app" / "modules" / "credits" / "postgres_contract_purchase.py").read_text(encoding="utf-8")

    assert "base_usdc_contract" in up
    assert "credit_purchases_onchain_purchase_ref_unique_idx" in up
    assert "payment_authorization_signature ~ '^0x[0-9a-f]{130}$'" in up
    assert "0057 rollback blocked: base_usdc_contract purchases exist" in down
    assert "drop column if exists payment_authorization_signature" in down
    assert "base_usdc_contract" not in down.split("add constraint credit_purchases_method_check", 1)[1].split(");", 1)[0]
    assert "app.modules.ads.models" not in repository_source


def test_0057_down_and_up_succeed_without_contract_purchases(credit_postgres_url: str) -> None:
    down = MIGRATION_DOWN.read_text(encoding="utf-8")
    up = MIGRATION_UP.read_text(encoding="utf-8")

    with psycopg.connect(credit_postgres_url) as conn:
        conn.execute("delete from credit_purchases where payment_method = 'base_usdc_contract'")
        conn.execute(down)
        conn.execute(up)
        conn.rollback()


def test_0057_down_blocks_contract_purchases_with_clear_error(credit_postgres_url: str) -> None:
    business_id = _seed_business(credit_postgres_url)
    repository = PostgresCreditRepository(credit_postgres_url)
    _candidate(repository, business_id=business_id, idempotency_key=f"rollback-{uuid4()}")
    down = MIGRATION_DOWN.read_text(encoding="utf-8")

    with (
        psycopg.connect(credit_postgres_url, autocommit=True) as conn,
        pytest.raises(psycopg.errors.RaiseException, match="0057 rollback blocked: base_usdc_contract purchases exist"),
    ):
        conn.execute(down)
