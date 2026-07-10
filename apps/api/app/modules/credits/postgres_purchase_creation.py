from __future__ import annotations

from app.modules.ads.models import new_id
from app.modules.businesses.models import FileAssetRecord
from app.modules.credits.models import CREDIT_PACKAGES, CreditPurchaseRecord
from app.modules.credits.postgres_manual_purchase import insert_credit_purchase_proof_file_pg
from app.modules.credits.row_mappers import file_from_row, purchase_from_row


def create_stripe_purchase_pg(connect, *, business_id: str, package_code: str, idempotency_key: str) -> CreditPurchaseRecord:  # type: ignore[no-untyped-def]
    package = CREDIT_PACKAGES[package_code]
    purchase_id = new_id()
    session_id = f"cs_nodo_{purchase_id.replace('-', '')}"
    with connect() as conn:
        row = conn.execute(
            """
            insert into credit_purchases (
                id, business_id, package_code, credits_amount, price_usd, payment_method,
                status, idempotency_key, stripe_checkout_session_id, created_at, updated_at
            )
            values (%s, %s, %s, %s, %s, 'stripe_checkout', 'pending_payment', %s, %s, now(), now())
            returning *
            """,
            (purchase_id, business_id, package_code, package["credits"], package["price_usd"], idempotency_key, session_id),
        ).fetchone()
        conn.commit()
    return purchase_from_row(row)


def create_manual_purchase_pg(
    connect,
    *,
    business_id: str,
    owner_user_id: str,
    package_code: str,
    payment_method: str,
    idempotency_key: str,
    storage_path: str,
    mime_type: str,
    size_bytes: int,
    manual_payment_reference: str | None,
    manual_tx_hash: str | None,
    manual_network: str | None,
) -> tuple[CreditPurchaseRecord, FileAssetRecord]:  # type: ignore[no-untyped-def]
    package = CREDIT_PACKAGES[package_code]
    purchase_id = new_id()
    with connect() as conn:
        file_row = insert_credit_purchase_proof_file_pg(
            conn,
            owner_user_id=owner_user_id,
            purchase_id=purchase_id,
            storage_path=storage_path,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        row = conn.execute(
            """
            insert into credit_purchases (
                id, business_id, package_code, credits_amount, price_usd, payment_method,
                status, idempotency_key, manual_payment_reference, manual_tx_hash,
                manual_network, proof_file_id, created_at, updated_at
            )
            values (%s, %s, %s, %s, %s, %s, 'pending_manual_review', %s, %s, %s, %s, %s, now(), now())
            returning *
            """,
            (
                purchase_id,
                business_id,
                package_code,
                package["credits"],
                package["price_usd"],
                payment_method,
                idempotency_key,
                manual_payment_reference,
                manual_tx_hash,
                manual_network,
                file_row["id"],
            ),
        ).fetchone()
        conn.commit()
    return purchase_from_row(row), file_from_row(file_row)
