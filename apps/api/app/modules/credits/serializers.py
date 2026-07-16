from __future__ import annotations

from typing import Any

from app.modules.ads.models import CreditLedgerRecord
from app.modules.businesses.models import FileAssetRecord
from app.modules.credits.models import CreditPurchaseRecord, ReferralEventRecord
from app.modules.credits.schemas import decimal_text


def mask_tail(value: str | None, keep: int = 4) -> str | None:
    if not value:
        return None
    if len(value) <= keep:
        return "*" * len(value)
    return f"***{value[-keep:]}"


def purchase_public(purchase: CreditPurchaseRecord, *, admin: bool = False) -> dict[str, Any]:
    data = {
        "id": purchase.id,
        "business_id": purchase.business_id,
        "package_code": purchase.package_code,
        "credits_amount": purchase.credits_amount,
        "price_usd": decimal_text(purchase.price_usd),
        "payment_method": purchase.payment_method,
        "status": purchase.status,
        "proof_file_id": purchase.proof_file_id,
        "created_at": purchase.created_at.isoformat(),
        "paid_at": purchase.paid_at.isoformat() if purchase.paid_at else None,
        "approved_at": purchase.approved_at.isoformat() if purchase.approved_at else None,
        "rejected_at": purchase.rejected_at.isoformat() if purchase.rejected_at else None,
    }
    if admin:
        data["manual_payment_reference_masked"] = mask_tail(purchase.manual_payment_reference)
        data["manual_tx_hash_masked"] = mask_tail(purchase.manual_tx_hash)
        data["manual_network"] = purchase.manual_network
        data["admin_note"] = purchase.admin_note
    if purchase.payment_method == "base_usdc_onchain":
        data.update(
            {
                "chain_id": purchase.chain_id,
                "network": purchase.network,
                "token_symbol": purchase.token_symbol,
                "token_contract_address": purchase.token_contract_address,
                "token_decimals": purchase.token_decimals,
                "expected_amount_units": str(purchase.expected_amount_units) if purchase.expected_amount_units is not None else None,
                "destination_wallet_address": purchase.destination_wallet_address,
                "tx_hash_masked": mask_tail(purchase.tx_hash, keep=8),
                "tx_amount_units": str(purchase.tx_amount_units) if purchase.tx_amount_units is not None else None,
                "tx_from_address_masked": mask_tail(purchase.tx_from_address),
                "tx_to_address": purchase.tx_to_address,
                "tx_block_number": purchase.tx_block_number,
                "tx_log_index": purchase.tx_log_index,
                "confirmations": purchase.confirmations,
                "verification_status": purchase.verification_status,
                "detected_at": purchase.detected_at.isoformat() if purchase.detected_at else None,
                "verified_at": purchase.verified_at.isoformat() if purchase.verified_at else None,
                "credited_at": purchase.credited_at.isoformat() if purchase.credited_at else None,
                "expires_at": purchase.expires_at.isoformat() if purchase.expires_at else None,
            }
        )
    return data


def file_public(file: FileAssetRecord) -> dict[str, Any]:
    return {
        "id": file.id,
        "file_type": file.file_type,
        "mime_type": file.mime_type,
        "size_bytes": file.size_bytes,
        "created_at": file.created_at.isoformat(),
    }


def ledger_public(ledger: CreditLedgerRecord) -> dict[str, Any]:
    return {
        "id": ledger.id,
        "business_id": ledger.business_id,
        "type": ledger.type,
        "amount": ledger.amount,
        "balance_available_before": ledger.available_before,
        "balance_available_after": ledger.available_after,
        "balance_blocked_before": ledger.blocked_before,
        "balance_blocked_after": ledger.blocked_after,
        "balance_consumed_before": ledger.consumed_before,
        "balance_consumed_after": ledger.consumed_after,
        "reason": ledger.reason,
        "source": ledger.source,
        "reference_type": ledger.reference_type,
        "reference_id": ledger.reference_id,
        "created_at": ledger.created_at.isoformat(),
    }


def referral_public(event: ReferralEventRecord, viewer_business_id: str) -> dict[str, Any]:
    return {
        "id": event.id,
        "direction": "earned" if event.referrer_business_id == viewer_business_id else "used",
        "status": event.status,
        "credits_awarded": event.credits_awarded,
        "created_at": event.created_at.isoformat(),
        "rewarded_at": event.rewarded_at.isoformat() if event.rewarded_at else None,
    }
