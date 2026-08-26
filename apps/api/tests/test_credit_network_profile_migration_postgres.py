from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import psycopg
import pytest

POSTGRES_OPT_IN = "NODO_RUN_CREDIT_POSTGRES"
POSTGRES_URL_ENV = "NODO_CREDIT_POSTGRES_URL"
ROOT = Path(__file__).resolve().parents[3]
MIGRATION_UP = ROOT / "database" / "migrations" / "0058_credit_contract_network_profiles.up.sql"
MIGRATION_DOWN = ROOT / "database" / "migrations" / "0058_credit_contract_network_profiles.down.sql"
MIGRATION_0059_UP = ROOT / "database" / "migrations" / "0059_credit_onchain_payment_network_profiles.up.sql"
MIGRATION_0059_DOWN = ROOT / "database" / "migrations" / "0059_credit_onchain_payment_network_profiles.down.sql"

BASE_MAINNET_USDC = "0x833589fcd6edb6e08f4c7c32d4f71b54bda02913"
BASE_SEPOLIA_USDC = "0x036cbd53842c5426634e7929541ec2318f3dcf7e"
TREASURY = "0x1111111111111111111111111111111111111111"
PAYER = "0x2222222222222222222222222222222222222222"
PAYMENT_CONTRACT = "0x3333333333333333333333333333333333333333"
SIGNER = "0x4444444444444444444444444444444444444444"
VALID_PURCHASE_REF = "0x" + "a" * 64


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
            (business_id, user_id, "52C2D Network Migration"),
        )
    return business_id


def _insert_contract_purchase(
    conn: psycopg.Connection,
    *,
    business_id: str,
    chain_id: int,
    network: str,
    token_contract_address: str,
    payment_contract_address: str | None = PAYMENT_CONTRACT,
    payment_contract_version: int = 2,
) -> str:
    purchase_id = str(uuid4())
    purchase_ref = "0x" + uuid4().hex + uuid4().hex
    conn.execute(
        """
        insert into credit_purchases (
            id, business_id, package_code, credits_amount, price_usd,
            payment_method, status, chain_id, network, token_symbol,
            token_contract_address, token_decimals, expected_amount_units,
            destination_wallet_address, expires_at, onchain_purchase_ref,
            onchain_payer_address, payment_contract_address,
            payment_contract_version, payment_authorization_expires_at,
            payment_authorization_digest, payment_authorization_signature,
            payment_authorization_signer_address,
            payment_authorization_signer_version,
            payment_authorization_signed_at
        ) values (
            %s, %s, 'starter', 5, 10.00,
            'base_usdc_contract', 'pending_payment', %s, %s, 'USDC',
            %s, 6, 10000000,
            %s, now() + interval '15 minutes', %s,
            %s, %s,
            %s, now() + interval '15 minutes',
            %s, %s,
            %s, 'postgres-test-v1', now()
        )
        """,
        (
            purchase_id,
            business_id,
            chain_id,
            network,
            token_contract_address,
            TREASURY,
            purchase_ref,
            PAYER,
            payment_contract_address,
            payment_contract_version,
            "0x" + "a" * 64,
            "0x" + "b" * 130,
            SIGNER,
        ),
    )
    return purchase_id


def _insert_onchain_evidence(
    conn: psycopg.Connection,
    *,
    purchase_id: str,
    chain_id: int,
    network: str,
    token_contract_address: str,
    payment_contract_address: str | None = PAYMENT_CONTRACT,
    purchase_ref: str | None = VALID_PURCHASE_REF,
    payer_address: str | None = PAYER,
    payment_contract_version: int | None = 2,
) -> str:
    evidence_id = str(uuid4())
    conn.execute(
        """
        insert into credit_purchase_onchain_payments (
            id, credit_purchase_id, chain_id, network, token_symbol,
            token_contract_address, token_decimals, expected_amount_units,
            tx_hash, tx_from_address, tx_to_address, tx_amount_units,
            tx_block_number, tx_log_index, confirmations, verification_source,
            verification_status, payment_contract_address, purchase_ref,
            payer_address, payment_contract_version
        ) values (
            %s, %s, %s, %s, 'USDC',
            %s, 6, 10000000,
            %s, %s, %s, 10000000,
            456, 17, 6, 'base_rpc',
            'verified', %s, %s,
            %s, %s
        )
        """,
        (
            evidence_id,
            purchase_id,
            chain_id,
            network,
            token_contract_address,
            "0x" + uuid4().hex + uuid4().hex,
            PAYER,
            TREASURY,
            payment_contract_address,
            purchase_ref,
            payer_address,
            payment_contract_version,
        ),
    )
    return evidence_id


def _delete_contract_purchase_rows(conn: psycopg.Connection) -> None:
    conn.execute(
        """
        delete from credits_ledger
        where related_credit_purchase_id in (
            select id from credit_purchases where payment_method = 'base_usdc_contract'
        )
        """
    )
    conn.execute(
        """
        delete from credit_purchase_onchain_payments
        where credit_purchase_id in (
            select id from credit_purchases where payment_method = 'base_usdc_contract'
        )
        """
    )
    conn.execute("delete from credit_purchases where payment_method = 'base_usdc_contract'")


def test_0058_migration_contract_is_explicit_and_reversible() -> None:
    up = MIGRATION_UP.read_text(encoding="utf-8")
    down = MIGRATION_DOWN.read_text(encoding="utf-8")

    assert "chain_id = 8453" in up
    assert "network = 'base_mainnet'" in up
    assert BASE_MAINNET_USDC in up
    assert "chain_id = 84532" in up
    assert "network = 'base_sepolia'" in up
    assert BASE_SEPOLIA_USDC in up
    assert "payment_contract_address is not null" in up
    assert "payment_contract_version is not null" in up
    assert "0058 rollback blocked: base_sepolia contract purchases exist" in down
    assert "chain_id = 84532" not in down.split("add constraint", 1)[1]


def test_0059_onchain_evidence_profile_is_explicit_and_reversible() -> None:
    up = MIGRATION_0059_UP.read_text(encoding="utf-8")
    down = MIGRATION_0059_DOWN.read_text(encoding="utf-8")

    assert "credit_purchase_onchain_network_profile_check" in up
    assert "chain_id = 8453" in up
    assert "network = 'base_mainnet'" in up
    assert BASE_MAINNET_USDC in up
    assert "chain_id = 84532" in up
    assert "network = 'base_sepolia'" in up
    assert BASE_SEPOLIA_USDC in up
    assert "credit_purchase_onchain_contract_metadata_check" in up
    assert "purchase_ref is not null" in up
    assert "payment_contract_address is not null" in up
    assert "payer_address is not null" in up
    assert "0059 rollback blocked: non-mainnet onchain payment evidence exists" in down
    assert "credit_purchase_onchain_chain_check" in down
    assert "credit_purchase_onchain_token_check" in down


def test_0058_down_and_up_succeed_without_sepolia_purchases(credit_postgres_url: str) -> None:
    up = MIGRATION_UP.read_text(encoding="utf-8")
    down = MIGRATION_DOWN.read_text(encoding="utf-8")

    with psycopg.connect(credit_postgres_url) as conn:
        _delete_contract_purchase_rows(conn)
        conn.execute(down)
        conn.execute(up)
        conn.rollback()


def test_0059_down_and_up_succeed_without_non_mainnet_evidence(credit_postgres_url: str) -> None:
    up = MIGRATION_0059_UP.read_text(encoding="utf-8")
    down = MIGRATION_0059_DOWN.read_text(encoding="utf-8")

    with psycopg.connect(credit_postgres_url) as conn:
        conn.execute("delete from credit_purchase_onchain_payments where network <> 'base_mainnet'")
        conn.execute(down)
        conn.execute(up)
        conn.rollback()


@pytest.mark.parametrize(
    ("chain_id", "network", "token_contract_address"),
    [
        (8453, "base_mainnet", BASE_MAINNET_USDC),
        (84532, "base_sepolia", BASE_SEPOLIA_USDC),
    ],
    ids=["base-mainnet", "base-sepolia"],
)
def test_0058_accepts_only_canonical_network_profiles(
    credit_postgres_url: str,
    chain_id: int,
    network: str,
    token_contract_address: str,
) -> None:
    business_id = _seed_business(credit_postgres_url)
    with psycopg.connect(credit_postgres_url) as conn:
        purchase_id = _insert_contract_purchase(
            conn,
            business_id=business_id,
            chain_id=chain_id,
            network=network,
            token_contract_address=token_contract_address,
        )
        stored = conn.execute(
            "select chain_id, network, token_contract_address from credit_purchases where id = %s",
            (purchase_id,),
        ).fetchone()
        assert stored == (chain_id, network, token_contract_address)
        conn.rollback()


def test_0059_accepts_base_sepolia_onchain_contract_evidence(
    credit_postgres_url: str,
) -> None:
    business_id = _seed_business(credit_postgres_url)
    with psycopg.connect(credit_postgres_url) as conn:
        purchase_id = _insert_contract_purchase(
            conn,
            business_id=business_id,
            chain_id=84532,
            network="base_sepolia",
            token_contract_address=BASE_SEPOLIA_USDC,
        )
        evidence_id = _insert_onchain_evidence(
            conn,
            purchase_id=purchase_id,
            chain_id=84532,
            network="base_sepolia",
            token_contract_address=BASE_SEPOLIA_USDC,
        )
        stored = conn.execute(
            """
            select chain_id, network, token_contract_address, payment_contract_address,
                purchase_ref, payer_address, payment_contract_version
            from credit_purchase_onchain_payments
            where id = %s
            """,
            (evidence_id,),
        ).fetchone()
        assert stored[0:4] == (84532, "base_sepolia", BASE_SEPOLIA_USDC, PAYMENT_CONTRACT)
        assert stored[4].startswith("0x")
        assert stored[5:] == (PAYER, 2)
        conn.rollback()


@pytest.mark.parametrize(
    ("chain_id", "network", "token_contract_address", "payment_contract_address", "payment_contract_version"),
    [
        (84532, "base_mainnet", BASE_SEPOLIA_USDC, PAYMENT_CONTRACT, 2),
        (8453, "base_sepolia", BASE_MAINNET_USDC, PAYMENT_CONTRACT, 2),
        (84532, "base_sepolia", BASE_MAINNET_USDC, PAYMENT_CONTRACT, 2),
        (8453, "base_mainnet", BASE_SEPOLIA_USDC, PAYMENT_CONTRACT, 2),
        (84532, "base_sepolia", BASE_SEPOLIA_USDC, None, 2),
        (84532, "base_sepolia", BASE_SEPOLIA_USDC, PAYMENT_CONTRACT, 0),
    ],
    ids=[
        "sepolia-chain-mainnet-network",
        "mainnet-chain-sepolia-network",
        "mainnet-token-on-sepolia",
        "sepolia-token-on-mainnet",
        "missing-payment-contract",
        "invalid-contract-version",
    ],
)
def test_0058_rejects_mixed_or_incomplete_profiles(
    credit_postgres_url: str,
    chain_id: int,
    network: str,
    token_contract_address: str,
    payment_contract_address: str | None,
    payment_contract_version: int,
) -> None:
    business_id = _seed_business(credit_postgres_url)
    with (
        psycopg.connect(credit_postgres_url) as conn,
        pytest.raises(psycopg.errors.CheckViolation),
    ):
        _insert_contract_purchase(
            conn,
            business_id=business_id,
            chain_id=chain_id,
            network=network,
            token_contract_address=token_contract_address,
            payment_contract_address=payment_contract_address,
            payment_contract_version=payment_contract_version,
        )


@pytest.mark.parametrize(
    ("chain_id", "network", "token_contract_address", "payment_contract_address", "purchase_ref", "payer_address", "payment_contract_version"),
    [
        (84532, "base_sepolia", BASE_MAINNET_USDC, PAYMENT_CONTRACT, "0x" + "a" * 64, PAYER, 2),
        (8453, "base_mainnet", BASE_SEPOLIA_USDC, PAYMENT_CONTRACT, "0x" + "a" * 64, PAYER, 2),
        (84532, "base_mainnet", BASE_SEPOLIA_USDC, PAYMENT_CONTRACT, "0x" + "a" * 64, PAYER, 2),
        (84532, "base_sepolia", BASE_SEPOLIA_USDC, PAYMENT_CONTRACT, None, PAYER, 2),
        (84532, "base_sepolia", BASE_SEPOLIA_USDC, None, "0x" + "a" * 64, PAYER, 2),
        (84532, "base_sepolia", BASE_SEPOLIA_USDC, PAYMENT_CONTRACT, "0x" + "a" * 64, None, 2),
    ],
    ids=[
        "mainnet-token-on-sepolia-evidence",
        "sepolia-token-on-mainnet-evidence",
        "sepolia-chain-mainnet-network-evidence",
        "partial-missing-ref",
        "partial-missing-contract",
        "partial-missing-payer",
    ],
)
def test_0059_rejects_mixed_or_partial_onchain_evidence(
    credit_postgres_url: str,
    chain_id: int,
    network: str,
    token_contract_address: str,
    payment_contract_address: str | None,
    purchase_ref: str | None,
    payer_address: str | None,
    payment_contract_version: int | None,
) -> None:
    business_id = _seed_business(credit_postgres_url)
    with (
        psycopg.connect(credit_postgres_url) as conn,
        pytest.raises(psycopg.errors.CheckViolation),
    ):
        purchase_id = _insert_contract_purchase(
            conn,
            business_id=business_id,
            chain_id=84532,
            network="base_sepolia",
            token_contract_address=BASE_SEPOLIA_USDC,
        )
        _insert_onchain_evidence(
            conn,
            purchase_id=purchase_id,
            chain_id=chain_id,
            network=network,
            token_contract_address=token_contract_address,
            payment_contract_address=payment_contract_address,
            purchase_ref=purchase_ref,
            payer_address=payer_address,
            payment_contract_version=payment_contract_version,
        )


def test_0058_down_blocks_existing_sepolia_purchase_before_changing_constraint(
    credit_postgres_url: str,
) -> None:
    business_id = _seed_business(credit_postgres_url)
    down = MIGRATION_DOWN.read_text(encoding="utf-8")

    with psycopg.connect(credit_postgres_url) as conn:
        _delete_contract_purchase_rows(conn)
        _insert_contract_purchase(
            conn,
            business_id=business_id,
            chain_id=84532,
            network="base_sepolia",
            token_contract_address=BASE_SEPOLIA_USDC,
        )
        with pytest.raises(
            psycopg.errors.RaiseException,
            match="0058 rollback blocked: base_sepolia contract purchases exist",
        ):
            conn.execute(down)
        conn.rollback()


def test_0059_down_blocks_existing_sepolia_evidence_before_changing_constraint(
    credit_postgres_url: str,
) -> None:
    business_id = _seed_business(credit_postgres_url)
    down = MIGRATION_0059_DOWN.read_text(encoding="utf-8")

    with psycopg.connect(credit_postgres_url) as conn:
        conn.execute("delete from credit_purchase_onchain_payments")
        purchase_id = _insert_contract_purchase(
            conn,
            business_id=business_id,
            chain_id=84532,
            network="base_sepolia",
            token_contract_address=BASE_SEPOLIA_USDC,
        )
        _insert_onchain_evidence(
            conn,
            purchase_id=purchase_id,
            chain_id=84532,
            network="base_sepolia",
            token_contract_address=BASE_SEPOLIA_USDC,
        )
        with pytest.raises(
            psycopg.errors.RaiseException,
            match="0059 rollback blocked: non-mainnet onchain payment evidence exists",
        ):
            conn.execute(down)
        conn.rollback()
