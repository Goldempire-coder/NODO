from __future__ import annotations

from decimal import Decimal

from app.core.errors import ApiError
from app.modules.credits.models import CREDIT_PACKAGES, CreditPurchaseRecord, new_id
from app.modules.credits.row_mappers import purchase_from_row


def create_contract_purchase_pg(
    connect,
    *,
    business_id: str,
    package_code: str,
    idempotency_key: str,
    price_usd: Decimal | None = None,
    expected_amount_units: int,
    chain_id: int,
    network: str,
    token_symbol: str,
    token_contract_address: str,
    token_decimals: int,
    destination_wallet_address: str,
    purchase_ref: str,
    payer_address: str,
    contract_address: str,
    contract_version: int,
    authorization_expires_at,
    authorization_digest: str,
    authorization_signature: str,
    signer_address: str,
    signer_version: str,
    signed_at,
    max_pending: int = 3,
) -> tuple[CreditPurchaseRecord, bool]:  # type: ignore[no-untyped-def]
    package = CREDIT_PACKAGES[package_code]
    payment_price_usd = price_usd if price_usd is not None else package["price_usd"]
    with connect() as conn:
        conn.execute("select pg_advisory_xact_lock(hashtextextended(%s, 0))", (business_id,))
        existing_row = conn.execute(
            """
            select * from credit_purchases
            where business_id = %s and idempotency_key = %s
            for update
            """,
            (business_id, idempotency_key),
        ).fetchone()
        if existing_row is not None:
            existing = purchase_from_row(existing_row)
            if (
                existing.payment_method != "base_usdc_contract"
                or existing.package_code != package_code
                or existing.onchain_payer_address != payer_address
            ):
                raise ApiError("IDEMPOTENCY_PAYLOAD_MISMATCH", status_code=409)
            conn.commit()
            return existing, False
        pending_count = conn.execute(
            """
            select count(*) as pending_count
            from credit_purchases
            where business_id = %s
              and payment_method = 'base_usdc_contract'
              and status in (
                  'pending_payment',
                  'pending_onchain_confirmation',
                  'detected',
                  'under_review'
              )
            """,
            (business_id,),
        ).fetchone()["pending_count"]
        if pending_count >= max_pending:
            raise ApiError("CRYPTO_PAYMENT_PENDING_LIMIT_REACHED", status_code=409)
        row = conn.execute(
            """
            insert into credit_purchases (
                id, business_id, package_code, credits_amount, price_usd, payment_method,
                status, idempotency_key, chain_id, network, token_symbol, token_contract_address,
                token_decimals, expected_amount_units, destination_wallet_address,
                onchain_purchase_ref, onchain_payer_address, payment_contract_address,
                payment_contract_version, payment_authorization_expires_at,
                payment_authorization_digest, payment_authorization_signature,
                payment_authorization_signer_address, payment_authorization_signer_version,
                payment_authorization_signed_at, verification_status, expires_at,
                created_at, updated_at
            )
            values (
                %s, %s, %s, %s, %s, 'base_usdc_contract',
                'pending_payment', %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, 'pending_payment', %s,
                now(), now()
            )
            on conflict (business_id, idempotency_key) where idempotency_key is not null
            do nothing
            returning *
            """,
            (
                new_id(),
                business_id,
                package_code,
                package["credits"],
                payment_price_usd,
                idempotency_key,
                chain_id,
                network,
                token_symbol,
                token_contract_address,
                token_decimals,
                expected_amount_units,
                destination_wallet_address,
                purchase_ref,
                payer_address,
                contract_address,
                contract_version,
                authorization_expires_at,
                authorization_digest,
                authorization_signature,
                signer_address,
                signer_version,
                signed_at,
                authorization_expires_at,
            ),
        ).fetchone()
        created = row is not None
        if row is None:
            raise ApiError("IDEMPOTENCY_CONFLICT", status_code=409)
        purchase = purchase_from_row(row)
        if (
            purchase.payment_method != "base_usdc_contract"
            or purchase.package_code != package_code
            or purchase.onchain_payer_address != payer_address
        ):
            raise ApiError("IDEMPOTENCY_PAYLOAD_MISMATCH", status_code=409)
        conn.commit()
    return purchase, created


def get_contract_purchase_by_idempotency_pg(
    connect,
    *,
    business_id: str,
    idempotency_key: str,
) -> CreditPurchaseRecord | None:  # type: ignore[no-untyped-def]
    with connect() as conn:
        row = conn.execute(
            """
            select * from credit_purchases
            where business_id = %s and idempotency_key = %s
            """,
            (business_id, idempotency_key),
        ).fetchone()
    return purchase_from_row(row) if row is not None else None


def count_pending_contract_purchases_pg(connect, business_id: str) -> int:  # type: ignore[no-untyped-def]
    with connect() as conn:
        row = conn.execute(
            """
            select count(*) as pending_count
            from credit_purchases
            where business_id = %s
              and payment_method = 'base_usdc_contract'
              and status in (
                  'pending_payment',
                  'pending_onchain_confirmation',
                  'detected',
                  'under_review'
              )
            """,
            (business_id,),
        ).fetchone()
    return int(row["pending_count"])


def find_pending_contract_purchase_pg(connect, business_id: str) -> CreditPurchaseRecord | None:  # type: ignore[no-untyped-def]
    with connect() as conn:
        row = conn.execute(
            """
            select *
            from credit_purchases
            where business_id = %s
              and payment_method = 'base_usdc_contract'
              and status in (
                  'pending_payment',
                  'pending_onchain_confirmation',
                  'detected',
                  'under_review'
              )
              and (
                  status <> 'pending_payment'
                  or (
                      (expires_at is null or expires_at > now())
                      and (
                          payment_authorization_expires_at is null
                          or payment_authorization_expires_at > now()
                      )
                  )
              )
            order by created_at asc
            limit 1
            """,
            (business_id,),
        ).fetchone()
    return purchase_from_row(row) if row is not None else None
