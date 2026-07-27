from __future__ import annotations

from typing import Any

from app.core.config import Settings
from app.modules.orders.business_ops import OrderBusinessOps
from app.modules.orders.create_order_flow import OrderCreateFlow
from app.modules.orders.payment_flow import OrderPaymentFlow
from app.modules.orders.rating_ops import OrderRatingOps
from app.modules.orders.remitter_ops import OrderRemitterOps
from app.modules.orders.schemas import OrderActionRequest, OrderCreateRequest, OrderRatingRequest, PaymentReportRequest
from app.modules.orders.service_support import OrderServiceSupportMixin
from app.modules.users.models import UserRecord


class OrderService(OrderServiceSupportMixin):
    def __init__(
        self,
        *,
        settings: Settings,
        repository,
        ad_repository,
        business_repository,
        capacity_repository,
        audit_writer,
        rate_limiter,
        idempotency_store,
        storage=None,
        marketplace_cache=None,
        notification_service=None,
        rating_repository=None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._ads = ad_repository
        self._businesses = business_repository
        self._capacity = capacity_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store
        self._storage = storage
        self._marketplace_cache = marketplace_cache
        self._notification_service = notification_service
        self._rating_ops = OrderRatingOps(
            repository=self._repository,
            rating_repository=rating_repository,
            audit_writer=self._audit,
            idempotency_store=self._idempotency,
            rate_limit=self._rate_limit,
        )
        self._create_flow = OrderCreateFlow(
            repository=self._repository,
            ad_repository=self._ads,
            audit_writer=self._audit,
            idempotency_store=self._idempotency,
            rate_limit=self._rate_limit,
            ad_or_safe_error=self._ad_or_safe_error,
            business_or_unavailable=self._business_or_unavailable,
            payment_or_unavailable=self._payment_or_unavailable,
            ad_expired=self._ad_expired,
            clear_marketplace_cache=self._clear_marketplace_cache,
            clear_marketplace_cache_after_order=self._clear_marketplace_cache_after_order,
            notification_service=self._notification_service,
            capacity_repository=self._capacity,
        )
        self._business_ops = OrderBusinessOps(
            repository=self._repository,
            ad_repository=self._ads,
            audit_writer=self._audit,
            idempotency_store=self._idempotency,
            rate_limit=self._rate_limit,
            approved_business_for_owner=self._approved_business_for_owner,
            notification_service=self._notification_service,
        )
        self._remitter_ops = OrderRemitterOps(
            repository=self._repository,
            ad_repository=self._ads,
            audit_writer=self._audit,
            idempotency_store=self._idempotency,
            rate_limit=self._rate_limit,
            materialize_order_expiration=self._materialize_order_expiration,
            return_or_expire_ad=self._return_or_expire_ad,
            rating_ops=self._rating_ops,
        )
        self._payment_flow = OrderPaymentFlow(
            repository=self._repository,
            audit_writer=self._audit,
            idempotency_store=self._idempotency,
            storage=self._storage,
            rate_limit=self._rate_limit,
            notification_service=self._notification_service,
        )

    def create_order(self, *, user: UserRecord, payload: OrderCreateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._create_flow.create_order(user=user, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def detail(self, *, user: UserRecord, order_id: str, request_id: str) -> dict[str, Any]:
        return self._remitter_ops.detail(user=user, order_id=order_id, request_id=request_id)

    def mine(self, *, user: UserRecord, status: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        return self._remitter_ops.mine(user=user, status=status, cursor=cursor, limit=limit, request_id=request_id)

    def extend(self, *, user: UserRecord, order_id: str, payload: OrderActionRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._remitter_ops.extend(user=user, order_id=order_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def cancel(self, *, user: UserRecord, order_id: str, payload: OrderActionRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._remitter_ops.cancel(user=user, order_id=order_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def create_rating(self, *, user: UserRecord, order_id: str, payload: OrderRatingRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._rating_ops.create(user=user, order_id=order_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def payment_instructions(self, *, user: UserRecord, order_id: str, request_id: str) -> dict[str, Any]:
        return self._payment_flow.payment_instructions(user=user, order_id=order_id, request_id=request_id)

    def upload_payment_evidence(
        self,
        *,
        user: UserRecord,
        order_id: str,
        file_name: str,
        mime_type: str,
        content: bytes,
        pending_payment_report_id: str | None,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return self._payment_flow.upload_payment_evidence(
            user=user,
            order_id=order_id,
            file_name=file_name,
            mime_type=mime_type,
            content=content,
            pending_payment_report_id=pending_payment_report_id,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def report_payment(self, *, user: UserRecord, order_id: str, payload: PaymentReportRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._payment_flow.report_payment(user=user, order_id=order_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def business_orders(self, *, user: UserRecord, status: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        return self._business_ops.business_orders(user=user, status=status, cursor=cursor, limit=limit, request_id=request_id)

    def business_order_detail(self, *, user: UserRecord, order_id: str, request_id: str) -> dict[str, Any]:
        return self._business_ops.business_order_detail(user=user, order_id=order_id, request_id=request_id)

    def confirm_business_payment(self, *, user: UserRecord, order_id: str, payload: OrderActionRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._business_ops.confirm_business_payment(user=user, order_id=order_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def reject_business_payment_report(self, *, user: UserRecord, order_id: str, payload: OrderActionRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._business_ops.reject_business_payment_report(user=user, order_id=order_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)

    def mark_business_delivered(self, *, user: UserRecord, order_id: str, payload: OrderActionRequest | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._business_ops.mark_business_delivered(user=user, order_id=order_id, payload=payload, request_id=request_id, idempotency_key=idempotency_key)
