from __future__ import annotations

from collections.abc import Callable
from typing import Any
from uuid import UUID

from app.core.errors import ApiError
from app.modules.credits.credit_transactions import CREDIT_TRANSACTION_STATUSES
from app.modules.credits.models import (
    CREDIT_PACKAGES,
    PURCHASE_METHODS,
    CreditPurchaseRecord,
)
from app.modules.credits.policy import require_admin_mutation, require_admin_view
from app.modules.credits.schemas import (
    AdminCreditAdjustmentRequest,
    AdminReviewCreditPurchaseRequest,
)
from app.modules.credits.serializers import (
    admin_credit_transaction_item,
    admin_credit_transaction_summary,
    admin_onchain_evidence,
    admin_purchase_detail,
    admin_purchase_reconciliation,
    admin_purchase_summary,
    ledger_public,
)
from app.modules.users.models import UserRecord


class CreditAdminActions:
    def __init__(
        self,
        *,
        repository,
        business_repository,
        audit_writer,
        idempotency_store,
        rate_limit: Callable[[str, str], None],
        require_idempotency_key: Callable[[str | None], str],
    ) -> None:  # type: ignore[no-untyped-def]
        self._repository = repository
        self._businesses = business_repository
        self._audit = audit_writer
        self._idempotency = idempotency_store
        self._rate_limit = rate_limit
        self._require_idempotency_key = require_idempotency_key

    def list_purchases(self, *, user: UserRecord, status: str | None, business_id: str | None, cursor: str | None, limit: int) -> dict[str, Any]:
        require_admin_view(user)
        self._rate_limit("admin_list_purchases", user.id)
        items, next_cursor = self._repository.list_purchases(status=status, business_id=business_id, cursor=cursor, limit=limit)
        return {"items": [admin_purchase_summary(item) for item in items], "next_cursor": next_cursor}

    def list_transactions(
        self,
        *,
        user: UserRecord,
        financial_status: str | None,
        payment_method: str | None,
        business_id: str | None,
        package_code: str | None,
        created_from,
        created_to,
        cursor: str | None,
        limit: int,
    ) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        require_admin_view(user)
        self._rate_limit("admin_list_credit_transactions", user.id)
        normalized_status = financial_status.strip().lower() if financial_status else None
        normalized_method = payment_method.strip().lower() if payment_method else None
        normalized_package = package_code.strip().lower() if package_code else None
        normalized_business_id = _uuid_filter(business_id)
        if normalized_status and normalized_status not in CREDIT_TRANSACTION_STATUSES:
            raise ApiError("CREDIT_TRANSACTION_STATUS_INVALID", status_code=422)
        if normalized_method and normalized_method not in PURCHASE_METHODS:
            raise ApiError("CREDIT_PAYMENT_METHOD_INVALID", status_code=422)
        if normalized_package and normalized_package not in CREDIT_PACKAGES:
            raise ApiError("CREDIT_PACKAGE_INVALID", status_code=422)
        if created_from and created_to and created_from > created_to:
            raise ApiError("CREDIT_TRANSACTION_DATE_RANGE_INVALID", status_code=422)
        items, next_cursor, summary = self._repository.list_credit_transactions(
            financial_status=normalized_status,
            payment_method=normalized_method,
            business_id=normalized_business_id,
            package_code=normalized_package,
            created_from=created_from,
            created_to=created_to,
            cursor=cursor,
            limit=limit,
        )
        return {
            "items": [admin_credit_transaction_item(item) for item in items],
            "next_cursor": next_cursor,
            "summary": admin_credit_transaction_summary(summary),
        }

    def purchase_detail(self, *, user: UserRecord, purchase_id: str) -> dict[str, Any]:
        require_admin_view(user)
        self._rate_limit("admin_purchase_detail", user.id)
        purchase = self._purchase_or_404(purchase_id)
        ledger = self._repository.ledger_for_purchase(purchase.id)
        return self._detail_payload(purchase, ledger)

    def approve_purchase(self, *, user: UserRecord, purchase_id: str, payload: AdminReviewCreditPurchaseRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("admin_approve_purchase", user.id)
        stable_key = self._require_idempotency_key(idempotency_key)

        def compute() -> dict[str, Any]:
            purchase = self._purchase_or_404(purchase_id)
            if purchase.status != "pending_manual_review":
                raise ApiError("MANUAL_PAYMENT_ALREADY_REVIEWED", status_code=409)
            updated, ledger = self._repository.approve_purchase(purchase=purchase, actor_user_id=user.id, admin_note=payload.reason)
            self._audit.write(event_type="manual_credit_payment_approved", actor_user_id=user.id, actor_role=user.role, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id, metadata_json={"reason": payload.reason})
            self._audit.write(event_type="credits_added", actor_user_id=user.id, actor_role=user.role, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id, metadata_json={"ledger_id": ledger.id if ledger else None, "amount": updated.credits_amount})
            return self._detail_payload(updated, ledger)

        return self._idempotency.replay_or_store(
            f"credits:admin_approve:{purchase_id}:{stable_key}",
            payload={"purchase_id": purchase_id, "reason": payload.reason},
            compute=compute,
        )

    def reject_purchase(self, *, user: UserRecord, purchase_id: str, payload: AdminReviewCreditPurchaseRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("admin_reject_purchase", user.id)
        stable_key = self._require_idempotency_key(idempotency_key)

        def compute() -> dict[str, Any]:
            purchase = self._purchase_or_404(purchase_id)
            updated = self._repository.reject_purchase(purchase=purchase, admin_user_id=user.id, reason=payload.reason)
            event_type = "onchain_credit_purchase_rejected" if purchase.payment_method == "base_usdc_onchain" else "manual_credit_payment_rejected"
            self._audit.write(event_type=event_type, actor_user_id=user.id, actor_role=user.role, resource_type="credit_purchase", resource_id=purchase.id, request_id=request_id, metadata_json={"reason": payload.reason})
            return self._detail_payload(updated, self._repository.ledger_for_purchase(updated.id))

        return self._idempotency.replay_or_store(
            f"credits:admin_reject:{purchase_id}:{stable_key}",
            payload={"purchase_id": purchase_id, "reason": payload.reason},
            compute=compute,
        )

    def adjust(self, *, user: UserRecord, payload: AdminCreditAdjustmentRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("admin_adjust", user.id)
        stable_key = self._require_idempotency_key(idempotency_key)

        def compute() -> dict[str, Any]:
            business = self._businesses.get_business(payload.business_id)
            if business is None:
                raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
            ledger = self._repository.adjust_wallet(
                business_id=payload.business_id,
                amount=payload.amount,
                direction=payload.direction,
                reason=payload.reason,
                notes=payload.notes,
                created_by=user.id,
            )
            self._audit.write(event_type="admin_credit_adjustment", actor_user_id=user.id, actor_role=user.role, resource_type="business", resource_id=payload.business_id, request_id=request_id, metadata_json={"ledger_id": ledger.id, "amount": payload.amount, "direction": payload.direction, "reason": payload.reason})
            return {"ledger": ledger_public(ledger)}

        return self._idempotency.replay_or_store(
            f"credits:admin_adjust:{payload.business_id}:{stable_key}",
            payload=payload.model_dump(),
            compute=compute,
        )

    def _purchase_or_404(self, purchase_id: str) -> CreditPurchaseRecord:
        purchase = self._repository.get_purchase(purchase_id)
        if purchase is None:
            raise ApiError("PURCHASE_NOT_FOUND", status_code=404)
        return purchase

    @staticmethod
    def _detail_payload(purchase: CreditPurchaseRecord, ledger) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return {
            "purchase": admin_purchase_detail(purchase),
            "onchain_evidence": admin_onchain_evidence(purchase),
            "ledger": ledger_public(ledger) if ledger else None,
            "reconciliation": admin_purchase_reconciliation(purchase, ledger),
        }


def _uuid_filter(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(value.strip()))
    except ValueError as exc:
        raise ApiError("BUSINESS_ID_INVALID", status_code=422) from exc
