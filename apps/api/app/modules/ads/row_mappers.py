from __future__ import annotations

from decimal import Decimal

from app.modules.ads.models import AdRecord, CreditLedgerRecord, CreditWalletRecord


def decimal_from_row_value(value: object) -> Decimal:
    return Decimal(str(value))


def ad_from_row(row) -> AdRecord:  # type: ignore[no-untyped-def]
    return AdRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        payment_method_id=str(row["payment_method_id"]),
        payment_method=row["payment_method"],
        delivery_method=row["delivery_method"],
        rate_bs_per_usd=decimal_from_row_value(row["rate_bs_per_usd"]),
        amount_min_usd=decimal_from_row_value(row["amount_min_usd"]),
        amount_max_usd=decimal_from_row_value(row["amount_max_usd"]),
        required_credits=row["required_credits"],
        status=row["status"],
        credit_hold_ledger_id=str(row["credit_hold_ledger_id"]) if row["credit_hold_ledger_id"] else None,
        credit_consumed_ledger_id=str(row["credit_consumed_ledger_id"]) if row["credit_consumed_ledger_id"] else None,
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        activated_at=row["activated_at"],
        expires_at=row["expires_at"],
        last_rate_updated_at=row["last_rate_updated_at"],
    )


def wallet_from_row(row) -> CreditWalletRecord:  # type: ignore[no-untyped-def]
    return CreditWalletRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        available_credits=row["available_credits"],
        blocked_credits=row["blocked_credits"],
        consumed_credits=row["consumed_credits"],
        lifetime_purchased_credits=row.get("lifetime_purchased_credits", 0),
        lifetime_bonus_credits=row.get("lifetime_bonus_credits", 0),
        lifetime_adjusted_credits=row.get("lifetime_adjusted_credits", 0),
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def credit_ledger_from_row(row) -> CreditLedgerRecord:  # type: ignore[no-untyped-def]
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
        related_ad_id=str(row["related_ad_id"]) if row.get("related_ad_id") else None,
        related_order_id=str(row["related_order_id"]) if row.get("related_order_id") else None,
        related_referral_id=str(row["related_referral_id"]) if row.get("related_referral_id") else None,
        related_credit_purchase_id=str(row["related_credit_purchase_id"]) if row.get("related_credit_purchase_id") else None,
        notes=row.get("notes"),
        created_by=str(row["created_by"]) if row.get("created_by") else None,
        created_at=row["created_at"],
    )
