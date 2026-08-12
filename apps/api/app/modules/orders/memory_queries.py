from __future__ import annotations

from app.modules.orders.models import OrderRecord
from app.shared.keyset_pagination import paginate_descending


class InMemoryOrderQueriesMixin:
    def list_payment_rejected_admin_cancelled_order_ids(self, order_ids: list[str]) -> set[str]:
        if not order_ids or self._disputes is None:  # type: ignore[attr-defined]
            return set()
        wanted = set(order_ids)
        disputes = getattr(self._disputes, "disputes", {})  # type: ignore[attr-defined]
        return {
            dispute.order_id
            for dispute in disputes.values()
            if dispute.order_id in wanted
            and dispute.previous_order_status == "payment_rejected"
            and dispute.resolution_type == "cancelled"
            and dispute.status == "cancelled"
            and (order := self.orders.get(dispute.order_id)) is not None  # type: ignore[attr-defined]
            and order.status == "cancelled"
            and order.cancel_reason == "admin_cancelled"
        }

    def list_for_remitter(self, *, remitter_user_id: str, status: str | None, cursor: str | None, limit: int) -> tuple[list[OrderRecord], str | None]:
        items = [order for order in self.orders.values() if order.remitter_user_id == remitter_user_id]  # type: ignore[attr-defined]
        return self._order_page(items=items, status=status, cursor=cursor, limit=limit)

    def list_for_business(self, *, business_id: str, status: str | None, cursor: str | None, limit: int) -> tuple[list[OrderRecord], str | None]:
        items = [order for order in self.orders.values() if order.business_id == business_id]  # type: ignore[attr-defined]
        return self._order_page(items=items, status=status, cursor=cursor, limit=limit)

    def list_for_business_statuses(self, *, business_id: str, statuses: set[str], cursor: str | None, limit: int) -> tuple[list[OrderRecord], str | None]:
        items = [order for order in self.orders.values() if order.business_id == business_id and order.status in statuses]  # type: ignore[attr-defined]
        return self._order_page(items=items, status=None, cursor=cursor, limit=limit)

    def list_for_remitter_statuses(self, *, remitter_user_id: str, statuses: set[str], cursor: str | None, limit: int) -> tuple[list[OrderRecord], str | None]:
        items = [order for order in self.orders.values() if order.remitter_user_id == remitter_user_id and order.status in statuses]  # type: ignore[attr-defined]
        return self._order_page(items=items, status=None, cursor=cursor, limit=limit)

    def list_attention_for_business(
        self,
        *,
        business_id: str,
        statuses: set[str],
        limit: int,
        cancel_reasons: set[str] | None = None,
    ) -> tuple[list[OrderRecord], bool]:
        items = [
            order
            for order in self.orders.values()  # type: ignore[attr-defined]
            if order.business_id == business_id
            and (
                order.status in statuses
                or (
                    order.status == "cancelled"
                    and cancel_reasons is not None
                    and order.cancel_reason in cancel_reasons
                )
            )
        ]
        return self._attention_order_page(items=items, limit=limit)

    def list_attention_for_remitter(self, *, remitter_user_id: str, statuses: set[str], limit: int) -> tuple[list[OrderRecord], bool]:
        items = [
            order
            for order in self.orders.values()  # type: ignore[attr-defined]
            if order.remitter_user_id == remitter_user_id and order.status in statuses
        ]
        return self._attention_order_page(items=items, limit=limit)

    def list_job_candidate_orders(self, *, limit: int) -> list[OrderRecord]:
        items = [
            order
            for order in self.orders.values()  # type: ignore[attr-defined]
            if order.status in {"waiting_payment", "payment_reported", "payment_confirmed", "delivered"}
        ]
        items.sort(key=lambda order: order.created_at)
        return items[:limit]

    def get_by_id_for_business(self, *, order_id: str, business_id: str) -> OrderRecord | None:
        order = self.orders.get(order_id)  # type: ignore[attr-defined]
        if order is None or order.business_id != business_id:
            return None
        return order

    def _order_page(self, *, items: list[OrderRecord], status: str | None, cursor: str | None, limit: int) -> tuple[list[OrderRecord], str | None]:
        if status:
            items = [order for order in items if order.status == status]
        return paginate_descending(
            items,
            timestamp_of=lambda order: order.created_at,
            id_of=lambda order: order.id,
            cursor=cursor,
            limit=limit,
        )

    def _attention_order_page(self, *, items: list[OrderRecord], limit: int) -> tuple[list[OrderRecord], bool]:
        items.sort(key=lambda order: (order.updated_at, order.id), reverse=True)
        return items[:limit], len(items) > limit
