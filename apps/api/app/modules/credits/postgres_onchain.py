from __future__ import annotations

from app.core.errors import ApiError
from app.modules.ads.models import new_id
from app.modules.credits.models import (
    BASE_MAINNET_CHAIN_ID,
    BASE_MAINNET_NETWORK,
    BASE_USDC_CONTRACT_ADDRESS,
    BASE_USDC_DECIMALS,
    BASE_USDC_TOKEN_SYMBOL,
    CREDIT_PACKAGES,
    ONCHAIN_CREDIT_LEDGER_REASON,
    CreditPurchaseRecord,
)
from app.modules.credits.onchain import OnchainVerificationResult
from app.modules.credits.postgres_purchase_review import _credit_wallet_for_update, _existing_purchase_ledger
from app.modules.credits.postgres_referral_bonus import grant_referral_bonus_if_eligible_pg
from app.modules.credits.row_mappers import ledger_from_row, purchase_from_row


def create_base_usdc_purchase_pg(
    connect,
    *,
    business_id: str,
    package_code: str,
    idempotency_key: str,
    expected_amount_units: int,
    destination_wallet_address: str,
    expires_at,
) -> CreditPurchaseRecord:  # type: ignore[no-untyped-def]
    package = CREDIT_PACKAGES[package_code]
    purchase_id = new_id()
    with connect() as conn:
        row = conn.execute(
            """
            insert into credit_purchases (
                id, business_id, package_code, credits_amount, price_usd, payment_method,
                status, idempotency_key, chain_id, network, token_symbol, token_contract_address,
                token_decimals, expected_amount_units, destination_wallet_address,
                verification_status, expires_at, created_at, updated_at
            )
            values (%s, %s, %s, %s, %s, 'base_usdc_onchain', 'pending_payment', %s,
                %s, %s, %s, %s, %s, %s, %s, 'pending_payment', %s, now(), now())
            returning *
            """,
            (
                purchase_id,
                business_id,
                package_code,
                package["credits"],
                package["price_usd"],
                idempotency_key,
                BASE_MAINNET_CHAIN_ID,
                BASE_MAINNET_NETWORK,
                BASE_USDC_TOKEN_SYMBOL,
                BASE_USDC_CONTRACT_ADDRESS,
                BASE_USDC_DECIMALS,
                expected_amount_units,
                destination_wallet_address,
                expires_at,
            ),
        ).fetchone()
        conn.commit()
    return purchase_from_row(row)


def apply_onchain_verification_pg(
    connect,
    *,
    purchase: CreditPurchaseRecord,
    verification: OnchainVerificationResult,
    actor_user_id: str | None,
):  # type: ignore[no-untyped-def]
    with connect() as conn:
        current_row = conn.execute("select * from credit_purchases where id = %s for update", (purchase.id,)).fetchone()
        if current_row is None:
            conn.rollback()
            raise ApiError("PURCHASE_NOT_FOUND", status_code=404)
        current = purchase_from_row(current_row)
        existing_ledger = _existing_purchase_ledger(conn, current.id)
        if existing_ledger:
            if current.status == "credited":
                return current, ledger_from_row(existing_ledger)
            conn.rollback()
            raise ApiError("CREDIT_ALREADY_GRANTED", status_code=409)
        _insert_or_update_onchain_payment_or_raise(conn, current.id, verification)
        _mark_detected(conn, current.id, verification)
        if verification.error_code:
            conn.execute(
                """
                update credit_purchases
                set status = 'verification_failed', verification_status = 'verification_failed',
                    failed_at = now(), updated_at = now()
                where id = %s
                """,
                (current.id,),
            )
            conn.commit()
            raise ApiError(verification.error_code, status_code=409)
        if verification.verification_status in {"pending_onchain_confirmation", "under_review"}:
            row = conn.execute(
                """
                update credit_purchases
                set status = %s, verification_status = %s, updated_at = now()
                where id = %s returning *
                """,
                (verification.verification_status, verification.verification_status, current.id),
            ).fetchone()
            conn.commit()
            return purchase_from_row(row), None
        if verification.verification_status != "verified":
            conn.rollback()
            raise ApiError("ONCHAIN_VERIFICATION_FAILED", status_code=409)
        wallet = _credit_wallet_for_update(conn, current.business_id)
        available_after = wallet["available_credits"] + current.credits_amount
        conn.execute(
            """
            update credit_wallets
            set available_credits = %s,
                lifetime_purchased_credits = lifetime_purchased_credits + %s,
                updated_at = now()
            where business_id = %s
            """,
            (available_after, current.credits_amount, current.business_id),
        )
        updated_purchase = conn.execute(
            """
            update credit_purchases
            set status = 'credited', verification_status = 'verified',
                paid_at = coalesce(paid_at, now()), approved_at = coalesce(approved_at, now()),
                verified_at = now(), credited_at = now(), updated_at = now()
            where id = %s returning *
            """,
            (current.id,),
        ).fetchone()
        ledger_row = conn.execute(
            """
            insert into credits_ledger (
                business_id, type, amount, available_before, available_after,
                blocked_before, blocked_after, consumed_before, consumed_after,
                related_credit_purchase_id, reason, source, reference_type, reference_id,
                created_by, created_at
            )
            values (%s, 'purchase', %s, %s, %s, %s, %s, %s, %s, %s,
                %s, 'credit_purchases', 'credit_purchase', %s, %s, now())
            returning *
            """,
            (
                current.business_id,
                current.credits_amount,
                wallet["available_credits"],
                available_after,
                wallet["blocked_credits"],
                wallet["blocked_credits"],
                wallet["consumed_credits"],
                wallet["consumed_credits"],
                current.id,
                ONCHAIN_CREDIT_LEDGER_REASON,
                current.id,
                actor_user_id,
            ),
        ).fetchone()
        grant_referral_bonus_if_eligible_pg(conn, referred_business_id=current.business_id, purchase_id=current.id, actor_user_id=actor_user_id)
        conn.commit()
    return purchase_from_row(updated_purchase), ledger_from_row(ledger_row)


def list_onchain_pending_purchases_pg(connect, *, limit: int) -> list[CreditPurchaseRecord]:  # type: ignore[no-untyped-def]
    with connect() as conn:
        rows = conn.execute(
            """
            select * from credit_purchases
            where payment_method = 'base_usdc_onchain'
              and status in ('pending_payment', 'pending_onchain_confirmation', 'detected')
              and tx_hash is not null
              and expected_amount_units is not null
              and destination_wallet_address is not null
            order by created_at asc
            limit %s
            """,
            (limit,),
        ).fetchall()
    return [purchase_from_row(row) for row in rows]


def _mark_detected(conn, purchase_id: str, verification: OnchainVerificationResult) -> None:  # type: ignore[no-untyped-def]
    conn.execute(
        """
        update credit_purchases
        set tx_hash = %s, tx_amount_units = %s, tx_from_address = %s, tx_to_address = %s,
            tx_block_number = %s, tx_log_index = %s, confirmations = %s,
            verification_source = 'base_rpc', verification_status = %s,
            detected_at = coalesce(detected_at, now()), updated_at = now()
        where id = %s
        """,
        (
            verification.tx_hash,
            verification.tx_amount_units,
            verification.tx_from_address,
            verification.tx_to_address,
            verification.tx_block_number,
            verification.tx_log_index,
            verification.confirmations,
            verification.verification_status,
            purchase_id,
        ),
    )


def _insert_or_update_onchain_payment_or_raise(conn, purchase_id: str, verification: OnchainVerificationResult) -> None:  # type: ignore[no-untyped-def]
    if verification.tx_log_index is None:
        return
    inserted = conn.execute(
        """
        insert into credit_purchase_onchain_payments (
            credit_purchase_id, chain_id, network, token_symbol, token_contract_address,
            token_decimals, expected_amount_units, tx_hash, tx_from_address, tx_to_address,
            tx_amount_units, tx_block_number, tx_log_index, confirmations,
            verification_source, verification_status, detected_at, verified_at, created_at, updated_at
        )
        select id, chain_id, network, token_symbol, token_contract_address, token_decimals,
            expected_amount_units, %s, %s, %s, %s, %s, %s, %s, 'base_rpc', %s,
            now(), case when %s = 'verified' then now() else null end, now(), now()
        from credit_purchases where id = %s
        on conflict (chain_id, tx_hash, tx_log_index) do nothing
        returning credit_purchase_id
        """,
        (
            verification.tx_hash,
            verification.tx_from_address,
            verification.tx_to_address,
            verification.tx_amount_units,
            verification.tx_block_number,
            verification.tx_log_index,
            verification.confirmations,
            verification.verification_status,
            verification.verification_status,
            purchase_id,
        ),
    ).fetchone()
    if inserted:
        return
    existing = conn.execute(
        """
        select credit_purchase_id from credit_purchase_onchain_payments
        where chain_id = %s and tx_hash = %s and tx_log_index = %s
        for update
        """,
        (verification.chain_id, verification.tx_hash, verification.tx_log_index),
    ).fetchone()
    if existing is None:
        conn.rollback()
        raise ApiError("ONCHAIN_VERIFICATION_FAILED", status_code=409)
    if str(existing["credit_purchase_id"]) != purchase_id:
        conn.rollback()
        raise ApiError("ONCHAIN_TX_ALREADY_USED", status_code=409)
    conn.execute(
        """
        update credit_purchase_onchain_payments
        set confirmations = %s,
            verification_status = %s,
            updated_at = now(),
            verified_at = case when %s = 'verified' then coalesce(verified_at, now()) else verified_at end
        where credit_purchase_id = %s
          and chain_id = %s
          and tx_hash = %s
          and tx_log_index = %s
        """,
        (
            verification.confirmations,
            verification.verification_status,
            verification.verification_status,
            purchase_id,
            verification.chain_id,
            verification.tx_hash,
            verification.tx_log_index,
        ),
    )
