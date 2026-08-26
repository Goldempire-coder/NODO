from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.credits.models import utc_now
from app.modules.credits.onchain import normalize_credit_verification


def _mask_tx_hash(value: str, keep: int = 8) -> str:
    return f"***{value[-keep:]}" if len(value) > keep else "*" * len(value)


class BaseUsdcCreditPurchaseWatcher:
    job_type = "verify_base_usdc_credit_purchases"

    def __init__(self, *, settings, credit_repository, audit_writer, onchain_verifier, admin_notifications=None) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._credits = credit_repository
        self._audit = audit_writer
        self._verifier = onchain_verifier
        self._admin_notifications = admin_notifications

    def run_once(self, *, request_id: str = "watcher") -> dict[str, Any]:
        purchases = self._credits.list_onchain_pending_purchases(limit=self._settings.onchain_credit_watcher_batch_size)
        eligible = [purchase for purchase in purchases if purchase.tx_hash and purchase.expected_amount_units is not None and purchase.destination_wallet_address]
        contract_purchase_reader = getattr(self._credits, "list_contract_pending_purchases", None)
        contract_purchases = (
            contract_purchase_reader(limit=self._settings.onchain_credit_watcher_batch_size)
            if callable(contract_purchase_reader)
            else []
        )
        contract_eligible = [
            purchase
            for purchase in contract_purchases
            if purchase.expected_amount_units is not None
            and purchase.destination_wallet_address
            and purchase.onchain_purchase_ref
            and purchase.onchain_payer_address
            and purchase.payment_contract_address
            and purchase.payment_contract_version is not None
        ]
        result: dict[str, Any] = {
            "job_type": self.job_type,
            "scanned": len(purchases),
            "eligible": len(eligible),
            "skipped_missing_tx": len(purchases) - len(eligible),
            "contract_scanned": len(contract_purchases),
            "contract_eligible": len(contract_eligible),
            "contract_skipped_incomplete": len(contract_purchases) - len(contract_eligible),
            "contract_verified_attempts": 0,
            "contract_credited": 0,
            "contract_under_review": 0,
            "contract_pending": 0,
            "stuck_or_expired": 0,
            "verified_attempts": 0,
            "credited": 0,
            "under_review": 0,
            "pending": 0,
            "errors": [],
            "rpc_calls": 0,
            "latest_block_prefetched": False,
        }
        rpc_before = getattr(self._verifier, "rpc_call_count", None)
        latest_block_number: int | None = None
        latest_block_reader = getattr(self._verifier, "latest_block_number", None)
        if (eligible or contract_eligible) and callable(latest_block_reader):
            try:
                latest_block_number = latest_block_reader()
                result["latest_block_prefetched"] = True
            except ApiError as exc:
                result["errors"].append({"purchase_id": None, "code": exc.code, "stage": "latest_block_prefetch"})
        for purchase in eligible:
            if not purchase.tx_hash or purchase.expected_amount_units is None or not purchase.destination_wallet_address:
                continue
            try:
                result["verified_attempts"] += 1
                verification = self._verifier.verify(
                    tx_hash=purchase.tx_hash,
                    expected_amount_units=purchase.expected_amount_units,
                    destination_wallet_address=purchase.destination_wallet_address,
                    min_confirmations=self._settings.onchain_credit_min_confirmations,
                    latest_block_number=latest_block_number,
                )
                verification = normalize_credit_verification(
                    purchase=purchase,
                    verification=verification,
                    submitted_tx_hash=purchase.tx_hash,
                    min_confirmations=self._settings.onchain_credit_min_confirmations,
                    now=utc_now(),
                )
                updated, ledger = self._credits.apply_onchain_verification(
                    purchase=purchase,
                    verification=verification,
                    actor_user_id=None,
                    min_confirmations=self._settings.onchain_credit_min_confirmations,
                )
                if ledger:
                    result["credited"] += 1
                    self._audit.write(event_type="onchain_credit_purchase_credited", actor_user_id=None, actor_role=None, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id, metadata_json={"source": self.job_type})
                elif updated.status == "under_review":
                    result["under_review"] += 1
                    self._notify_credit_attention(purchase=updated, reason="under_review", request_id=request_id)
                else:
                    result["pending"] += 1
            except ApiError as exc:
                result["errors"].append({"purchase_id": purchase.id, "code": exc.code})
                self._audit.write(
                    event_type="onchain_payment_verification_failed",
                    actor_user_id=None,
                    actor_role=None,
                    resource_type="credit_purchase",
                    resource_id=purchase.id,
                    request_id=request_id,
                    metadata_json={"source": self.job_type, "tx_hash_masked": _mask_tx_hash(purchase.tx_hash), "code": exc.code},
                )
                current = self._credits.get_purchase(purchase.id)
                if current is not None and current.status in {"verification_failed", "failed", "expired", "under_review"}:
                    self._notify_credit_attention(purchase=current, reason=current.status, request_id=request_id, error_code=exc.code)
        contract_payment_reader = getattr(self._verifier, "find_contract_payments", None)
        if contract_eligible and callable(contract_payment_reader):
            try:
                contract_verifications = contract_payment_reader(
                    purchases=contract_eligible,
                    min_confirmations=self._settings.onchain_credit_min_confirmations,
                    latest_block_number=latest_block_number,
                    lookback_blocks=getattr(self._settings, "onchain_credit_contract_watcher_lookback_blocks", 5000),
                )
            except ApiError as exc:
                for purchase in contract_eligible:
                    self._record_contract_verification_error(
                        result=result,
                        purchase=purchase,
                        request_id=request_id,
                        error=exc,
                    )
            else:
                for purchase in contract_eligible:
                    try:
                        result["contract_verified_attempts"] += 1
                        verification = contract_verifications.get(purchase.id)
                        if verification is None:
                            result["contract_pending"] += 1
                            result["pending"] += 1
                            continue
                        verification = normalize_credit_verification(
                            purchase=purchase,
                            verification=verification,
                            submitted_tx_hash=verification.tx_hash,
                            min_confirmations=self._settings.onchain_credit_min_confirmations,
                            now=utc_now(),
                        )
                        updated, ledger = self._credits.apply_onchain_verification(
                            purchase=purchase,
                            verification=verification,
                            actor_user_id=None,
                            min_confirmations=self._settings.onchain_credit_min_confirmations,
                        )
                        if ledger:
                            result["contract_credited"] += 1
                            result["credited"] += 1
                            self._audit.write(
                                event_type="onchain_credit_purchase_credited",
                                actor_user_id=None,
                                actor_role=None,
                                resource_type="credit_purchase",
                                resource_id=purchase.id,
                                request_id=request_id,
                                metadata_json={"source": self.job_type, "payment_method": "base_usdc_contract"},
                            )
                        elif updated.status == "under_review":
                            result["contract_under_review"] += 1
                            result["under_review"] += 1
                            self._notify_credit_attention(purchase=updated, reason="under_review", request_id=request_id)
                        else:
                            result["contract_pending"] += 1
                            result["pending"] += 1
                    except ApiError as exc:
                        self._record_contract_verification_error(
                            result=result,
                            purchase=purchase,
                            request_id=request_id,
                            error=exc,
                        )
        result["stuck_or_expired"] = self._notify_stuck_or_expired_purchases(request_id=request_id)
        rpc_after = getattr(self._verifier, "rpc_call_count", None)
        if isinstance(rpc_before, int) and isinstance(rpc_after, int):
            result["rpc_calls"] = max(0, rpc_after - rpc_before)
        return result

    def _notify_credit_attention(self, *, purchase, reason: str, request_id: str, error_code: str | None = None) -> None:  # type: ignore[no-untyped-def]
        if self._admin_notifications is None:
            return
        self._admin_notifications.credit_purchase_attention(purchase=purchase, reason=reason, request_id=request_id, error_code=error_code)

    def _record_contract_verification_error(self, *, result: dict[str, Any], purchase, request_id: str, error: ApiError) -> None:  # type: ignore[no-untyped-def]
        result["errors"].append({"purchase_id": purchase.id, "code": error.code, "stage": "contract_event"})
        metadata: dict[str, Any] = {"source": self.job_type, "payment_method": "base_usdc_contract", "code": error.code}
        if purchase.tx_hash:
            metadata["tx_hash_masked"] = _mask_tx_hash(purchase.tx_hash)
        self._audit.write(
            event_type="onchain_payment_verification_failed",
            actor_user_id=None,
            actor_role=None,
            resource_type="credit_purchase",
            resource_id=purchase.id,
            request_id=request_id,
            metadata_json=metadata,
        )
        current = self._credits.get_purchase(purchase.id)
        if current is not None and current.status in {"verification_failed", "failed", "expired", "under_review"}:
            self._notify_credit_attention(purchase=current, reason=current.status, request_id=request_id, error_code=error.code)

    def _notify_stuck_or_expired_purchases(self, *, request_id: str) -> int:
        if self._admin_notifications is None:
            return 0
        notified = 0
        current_time = utc_now()
        for status in ("pending_payment", "expired"):
            cursor: str | None = None
            seen_cursors: set[str] = set()
            while True:
                purchases, next_cursor = self._credits.list_purchases(status=status, business_id=None, cursor=cursor, limit=self._settings.onchain_credit_watcher_batch_size)
                for purchase in purchases:
                    if purchase.payment_method != "base_usdc_onchain":
                        continue
                    if status == "pending_payment":
                        if purchase.tx_hash or purchase.expires_at is None:
                            continue
                        if purchase.expires_at > current_time:
                            continue
                        reason = "stuck"
                    else:
                        reason = "expired"
                    self._notify_credit_attention(purchase=purchase, reason=reason, request_id=request_id)
                    notified += 1
                if not next_cursor or next_cursor in seen_cursors:
                    break
                seen_cursors.add(next_cursor)
                cursor = next_cursor
        return notified
