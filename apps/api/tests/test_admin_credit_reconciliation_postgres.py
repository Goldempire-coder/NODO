from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest

from app.modules.credits.models import BASE_USDC_CONTRACT_ADDRESS
from app.modules.credits.onchain import OnchainVerificationResult
from app.modules.credits.postgres_repository import PostgresCreditRepository


POSTGRES_OPT_IN = "NODO_RUN_CREDIT_POSTGRES"
POSTGRES_URL_ENV = "NODO_CREDIT_POSTGRES_URL"
DESTINATION_WALLET = "0x1111111111111111111111111111111111111111"


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


def _seed_business(database_url: str, label: str) -> tuple[str, str]:
    user_id = str(uuid4())
    business_id = str(uuid4())
    with psycopg.connect(database_url) as conn:
        conn.execute(
            "insert into users (id, role, status) values (%s, 'business_owner', 'active')",
            (user_id,),
        )
        conn.execute(
            """
            insert into businesses (id, owner_user_id, business_name, verification_status, approved_at)
            values (%s, %s, %s, 'approved', now())
            """,
            (business_id, user_id, f"Credit Reconciliation {label}"),
        )
        conn.commit()
    return user_id, business_id


def test_postgres_credit_ledger_cursor_and_purchase_reconciliation_are_stable(
    credit_postgres_url: str,
) -> None:
    user_id, business_id = _seed_business(credit_postgres_url, "cursor")
    repository = PostgresCreditRepository(credit_postgres_url)
    entries = [
        repository.adjust_wallet(
            business_id=business_id,
            amount=1,
            direction="add",
            reason=f"stable_cursor_{index}",
            notes=None,
            created_by=user_id,
        )
        for index in range(3)
    ]
    tied_at = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    with psycopg.connect(credit_postgres_url) as conn:
        conn.execute(
            "update credits_ledger set created_at = %s where id = any(%s)",
            (tied_at, [entry.id for entry in entries]),
        )
        conn.commit()

    first, cursor = repository.list_ledger(
        business_id=business_id,
        ledger_type="admin_adjustment",
        cursor=None,
        limit=2,
    )
    second, final_cursor = repository.list_ledger(
        business_id=business_id,
        ledger_type="admin_adjustment",
        cursor=cursor,
        limit=2,
    )

    assert cursor is not None
    assert final_cursor is None
    assert len({item.id for item in [*first, *second]}) == 3

    purchase = repository.create_base_usdc_purchase(
        business_id=business_id,
        package_code="starter",
        idempotency_key=f"reconciliation-{uuid4()}",
        expected_amount_units=10_000_000,
        destination_wallet_address=DESTINATION_WALLET,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
    )
    verification = OnchainVerificationResult(
        chain_id=8453,
        token_contract_address=BASE_USDC_CONTRACT_ADDRESS,
        destination_wallet_address=DESTINATION_WALLET,
        tx_hash="0x" + uuid4().hex + uuid4().hex,
        tx_from_address="0x2222222222222222222222222222222222222222",
        tx_to_address=DESTINATION_WALLET,
        tx_amount_units=10_000_000,
        tx_block_number=52,
        tx_log_index=52,
        confirmations=6,
        verification_status="verified",
    )
    credited, ledger = repository.apply_onchain_verification(
        purchase=purchase,
        verification=verification,
        actor_user_id=user_id,
        min_confirmations=3,
    )

    related = repository.ledger_for_purchase(purchase.id)
    assert credited.status == "credited"
    assert ledger is not None
    assert related is not None
    assert related.id == ledger.id
    assert related.related_credit_purchase_id == purchase.id
