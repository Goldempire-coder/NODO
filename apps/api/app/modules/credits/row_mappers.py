from __future__ import annotations

from decimal import Decimal

from app.modules.ads.models import CreditLedgerRecord, CreditWalletRecord
from app.modules.businesses.models import FileAssetRecord
from app.modules.credits.models import CreditPurchaseRecord


def decimal_from_row_value(value: object) -> Decimal:
    return Decimal(str(value))


def _optional(row, key: str, default=None):  # type: ignore[no-untyped-def]
    try:
        return row[key]
    except (KeyError, IndexError):
        return default


def purchase_from_row(row) -> CreditPurchaseRecord:  # type: ignore[no-untyped-def]
    return CreditPurchaseRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        package_code=row["package_code"],
        credits_amount=row["credits_amount"],
        price_usd=decimal_from_row_value(row["price_usd"]),
        payment_method=row["payment_method"],
        status=row["status"],
        idempotency_key=row["idempotency_key"],
        stripe_checkout_session_id=row["stripe_checkout_session_id"],
        stripe_payment_intent_id=row["stripe_payment_intent_id"],
        stripe_event_id=row["stripe_event_id"],
        manual_payment_reference=row["manual_payment_reference"],
        manual_tx_hash=row["manual_tx_hash"],
        manual_network=row["manual_network"],
        chain_id=_optional(row, "chain_id"),
        network=_optional(row, "network"),
        token_symbol=_optional(row, "token_symbol"),
        token_contract_address=_optional(row, "token_contract_address"),
        token_decimals=_optional(row, "token_decimals"),
        expected_amount_units=int(_optional(row, "expected_amount_units")) if _optional(row, "expected_amount_units") is not None else None,
        destination_wallet_address=_optional(row, "destination_wallet_address"),
        tx_hash=_optional(row, "tx_hash"),
        tx_amount_units=int(_optional(row, "tx_amount_units")) if _optional(row, "tx_amount_units") is not None else None,
        tx_from_address=_optional(row, "tx_from_address"),
        tx_to_address=_optional(row, "tx_to_address"),
        tx_block_number=_optional(row, "tx_block_number"),
        tx_log_index=_optional(row, "tx_log_index"),
        confirmations=_optional(row, "confirmations"),
        verification_source=_optional(row, "verification_source"),
        verification_status=_optional(row, "verification_status"),
        proof_file_id=str(row["proof_file_id"]) if row["proof_file_id"] else None,
        approved_by_admin_id=str(row["approved_by_admin_id"]) if row["approved_by_admin_id"] else None,
        rejected_by_admin_id=str(row["rejected_by_admin_id"]) if row["rejected_by_admin_id"] else None,
        admin_note=row["admin_note"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        paid_at=row["paid_at"],
        approved_at=row["approved_at"],
        rejected_at=row["rejected_at"],
        failed_at=row["failed_at"],
        expired_at=row["expired_at"],
        detected_at=_optional(row, "detected_at"),
        verified_at=_optional(row, "verified_at"),
        credited_at=_optional(row, "credited_at"),
        expires_at=_optional(row, "expires_at"),
    )


def wallet_from_row(row) -> CreditWalletRecord:  # type: ignore[no-untyped-def]
    return CreditWalletRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        available_credits=row["available_credits"],
        blocked_credits=row["blocked_credits"],
        consumed_credits=row["consumed_credits"],
        lifetime_purchased_credits=row["lifetime_purchased_credits"],
        lifetime_bonus_credits=row["lifetime_bonus_credits"],
        lifetime_adjusted_credits=row["lifetime_adjusted_credits"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def ledger_from_row(row) -> CreditLedgerRecord:  # type: ignore[no-untyped-def]
    return CreditLedgerRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        type=row["type"],
        amount=row["amount"],
        available_before=row["available_before"],
        available_after=row["available_after"],
        blocked_before=row["blocked_before"],
        blocked_after=row["blocked_after"],
        consumed_before=row["consumed_before"],
        consumed_after=row["consumed_after"],
        reason=row["reason"],
        source=row["source"],
        reference_type=row["reference_type"],
        reference_id=str(row["reference_id"]),
        related_ad_id=str(row["related_ad_id"]) if row["related_ad_id"] else None,
        related_order_id=str(row["related_order_id"]) if row["related_order_id"] else None,
        related_referral_id=str(row["related_referral_id"]) if row["related_referral_id"] else None,
        related_credit_purchase_id=str(row["related_credit_purchase_id"]) if row["related_credit_purchase_id"] else None,
        notes=row["notes"],
        created_by=str(row["created_by"]) if row["created_by"] else None,
        created_at=row["created_at"],
    )


def file_from_row(row) -> FileAssetRecord:  # type: ignore[no-untyped-def]
    return FileAssetRecord(
        id=str(row["id"]),
        owner_user_id=str(row["owner_user_id"]),
        resource_type=row["resource_type"],
        resource_id=str(row["resource_id"]),
        file_type=row["file_type"],
        storage_path=row["storage_path"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        created_at=row["created_at"],
        deleted_at=row["deleted_at"],
    )
