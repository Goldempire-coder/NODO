from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.credits.models import utc_now


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
        result: dict[str, Any] = {
            "job_type": self.job_type,
            "scanned": len(purchases),
            "eligible": len(eligible),
            "skipped_missing_tx": len(purchases) - len(eligible),
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
        if eligible and callable(latest_block_reader):
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
                updated, ledger = self._credits.apply_onchain_verification(purchase=purchase, verification=verification, actor_user_id=None)
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
                current = self._credits.get_purchase(purchase.id)
                if current is not None and current.status in {"verification_failed", "failed", "expired", "under_review"}:
                    self._notify_credit_attention(purchase=current, reason=current.status, request_id=request_id, error_code=exc.code)
        result["stuck_or_expired"] = self._notify_stuck_or_expired_purchases(request_id=request_id)
        rpc_after = getattr(self._verifier, "rpc_call_count", None)
        if isinstance(rpc_before, int) and isinstance(rpc_after, int):
            result["rpc_calls"] = max(0, rpc_after - rpc_before)
        return result

    def _notify_credit_attention(self, *, purchase, reason: str, request_id: str, error_code: str | None = None) -> None:  # type: ignore[no-untyped-def]
        if self._admin_notifications is None:
            return
        self._admin_notifications.credit_purchase_attention(purchase=purchase, reason=reason, request_id=request_id, error_code=error_code)

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
