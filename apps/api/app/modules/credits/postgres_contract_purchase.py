from __future__ import annotations

from app.core.errors import ApiError
from app.modules.credits.models import (
    BASE_MAINNET_CHAIN_ID,
    BASE_MAINNET_NETWORK,
    BASE_USDC_CONTRACT_ADDRESS,
    BASE_USDC_DECIMALS,
    BASE_USDC_TOKEN_SYMBOL,
    CREDIT_PACKAGES,
    CreditPurchaseRecord,
    new_id,
)
from app.modules.credits.row_mappers import purchase_from_row


def create_contract_purchase_pg(
    connect,
    *,
    business_id: str,
    package_code: str,
    idempotency_key: str,
    expected_amount_units: int,
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
) -> tuple[CreditPurchaseRecord, bool]:  # type: ignore[no-untyped-def]
    package = CREDIT_PACKAGES[package_code]
    with connect() as conn:
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
                package["price_usd"],
                idempotency_key,
                BASE_MAINNET_CHAIN_ID,
                BASE_MAINNET_NETWORK,
                BASE_USDC_TOKEN_SYMBOL,
                BASE_USDC_CONTRACT_ADDRESS,
                BASE_USDC_DECIMALS,
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
            row = conn.execute(
                """
                select * from credit_purchases
                where business_id = %s and idempotency_key = %s
                for update
                """,
                (business_id, idempotency_key),
            ).fetchone()
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
