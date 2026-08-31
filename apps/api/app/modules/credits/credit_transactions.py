from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.modules.ads.models import CreditLedgerRecord
from app.modules.credits.models import CreditPurchaseRecord

CREDIT_TRANSACTION_STATUSES = {"pending", "confirmed", "review", "failed", "dismissed"}
CONFIRMED_PURCHASE_STATUSES = {"approved", "credited"}
PENDING_PURCHASE_STATUSES = {"created", "pending_payment", "pending_onchain_confirmation", "detected", "paid"}
REVIEW_PURCHASE_STATUSES = {"pending_manual_review", "under_review", "verified"}
FAILED_PURCHASE_STATUSES = {"rejected", "failed", "expired", "verification_failed"}


@dataclass(frozen=True)
class CreditTransactionRecord:
    purchase: CreditPurchaseRecord
    business_name: str | None
    ledger: CreditLedgerRecord | None


@dataclass(frozen=True)
class CreditTransactionSummary:
    total_count: int
    confirmed_count: int
    pending_count: int
    review_count: int
    failed_count: int
    dismissed_count: int
    confirmed_amount_usd: Decimal
    confirmed_credits: int


def credit_transaction_status(purchase: CreditPurchaseRecord, ledger: CreditLedgerRecord | None) -> str:
    if ledger is not None and purchase.status in CONFIRMED_PURCHASE_STATUSES:
        return "confirmed"
    if purchase.owner_dismissed_at is not None and ledger is None:
        return "dismissed"
    if purchase.status in REVIEW_PURCHASE_STATUSES:
        return "review"
    if purchase.status in CONFIRMED_PURCHASE_STATUSES:
        return "review"
    if purchase.status in FAILED_PURCHASE_STATUSES:
        return "failed"
    if purchase.status in PENDING_PURCHASE_STATUSES:
        return "pending"
    return "review"


def credit_transaction_time(purchase: CreditPurchaseRecord) -> datetime:
    return (
        purchase.credited_at
        or purchase.verified_at
        or purchase.approved_at
        or purchase.paid_at
        or purchase.detected_at
        or purchase.updated_at
        or purchase.created_at
    )


def summarize_credit_transactions(records: list[CreditTransactionRecord]) -> CreditTransactionSummary:
    counts = {status: 0 for status in CREDIT_TRANSACTION_STATUSES}
    confirmed_amount = Decimal()
    confirmed_credits = 0
    for record in records:
        status = credit_transaction_status(record.purchase, record.ledger)
        counts[status] += 1
        if status == "confirmed":
            confirmed_amount += record.purchase.price_usd
            confirmed_credits += record.purchase.credits_amount
    return CreditTransactionSummary(
        total_count=len(records),
        confirmed_count=counts["confirmed"],
        pending_count=counts["pending"],
        review_count=counts["review"],
        failed_count=counts["failed"],
        dismissed_count=counts["dismissed"],
        confirmed_amount_usd=confirmed_amount,
        confirmed_credits=confirmed_credits,
    )
