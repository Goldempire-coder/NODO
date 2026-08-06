from __future__ import annotations

from typing import Any

from app.modules.admin.memory_investigation import InMemoryAdminInvestigationMixin
from app.modules.admin.presenters import iso, mask_sensitive
from app.modules.admin.user_presenters import admin_business_link_payload, admin_user_payload

class InMemoryAdminRepository(InMemoryAdminInvestigationMixin):
    def __init__(self, *, users, businesses, orders, disputes, credits, audit_writer, business_intake=None, support=None) -> None:  # type: ignore[no-untyped-def]
        self._users = users
        self._businesses = businesses
        self._business_intake = business_intake
        self._support = support
        self._orders = orders
        self._disputes = disputes
        self._credits = credits
        self._audit = audit_writer

    def dashboard(self) -> dict[str, Any]:
        businesses = list(getattr(self._businesses, "businesses", {}).values())
        orders = list(getattr(self._orders, "orders", {}).values())
        disputes = list(getattr(self._disputes, "disputes", {}).values())
        purchases = list(getattr(self._credits, "purchases", {}).values())
        intakes = list(getattr(getattr(self, "_business_intake", None), "intakes", {}).values())
        return {
            "queues": {
                "pending_businesses": sum(1 for item in businesses if item.verification_status == "pending"),
                "pending_business_intakes": sum(1 for item in intakes if item.status == "submitted"),
                "pending_credit_purchases": sum(1 for item in purchases if item.status == "pending_manual_review"),
                "open_disputes": sum(1 for item in disputes if item.status in {"open", "in_review"}),
            },
            "orders": {
                "active_count": sum(1 for item in orders if item.status not in {"completed", "cancelled"}),
                "disputed_count": sum(1 for item in orders if item.status == "disputed"),
                "delivered_waiting_close_count": sum(1 for item in orders if item.status == "delivered"),
            },
            "credits": {"manual_review_count": sum(1 for item in purchases if item.status == "pending_manual_review")},
            "risk": {"businesses_under_review": sum(1 for item in businesses if item.risk_level == "under_review")},
        }

    def metrics(self) -> dict[str, Any]:
        businesses = list(getattr(self._businesses, "businesses", {}).values())
        orders = list(getattr(self._orders, "orders", {}).values())
        disputes = list(getattr(self._disputes, "disputes", {}).values())
        ledger = list(getattr(getattr(self._credits, "_ads", None), "ledger", {}).values())
        return {
            "source": "read_model",
            "generated_at": iso(max([*(item.created_at for item in businesses), *(item.created_at for item in orders)], default=None)),
            "businesses": {"total": len(businesses), "approved": sum(1 for item in businesses if item.verification_status == "approved")},
            "orders": {status: sum(1 for item in orders if item.status == status) for status in ["waiting_payment", "payment_reported", "payment_confirmed", "delivered", "disputed", "completed", "cancelled"]},
            "disputes": {"open": sum(1 for item in disputes if item.status == "open"), "in_review": sum(1 for item in disputes if item.status == "in_review"), "resolved": sum(1 for item in disputes if item.status == "resolved")},
            "credits": {"consumed_ledger_entries": sum(1 for item in ledger if item.type == "consume"), "released_ledger_entries": sum(1 for item in ledger if item.type == "release")},
        }

    def list_businesses(self, *, verification_status: str | None, risk_level: str | None, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        items = list(getattr(self._businesses, "businesses", {}).values())
        if verification_status:
            items = [item for item in items if item.verification_status == verification_status]
        if risk_level:
            items = [item for item in items if item.risk_level == risk_level]
        if cursor:
            items = [item for item in items if item.created_at.isoformat() < cursor]
        items.sort(key=lambda item: item.created_at, reverse=True)
        page = items[:limit]
        return [self._business_summary(item) for item in page], page[-1].created_at.isoformat() if len(page) == limit else None

    def get_business(self, business_id: str) -> dict[str, Any] | None:
        business = getattr(self._businesses, "businesses", {}).get(business_id)
        return self._business_detail(business) if business else None

    def list_users(
        self,
        *,
        phone: str | None,
        telegram_id: int | None,
        username: str | None,
        role: str | None,
        status: str | None,
        cursor: str | None,
        limit: int,
        full_sensitive: bool,
    ) -> tuple[list[dict[str, Any]], str | None]:
        items = list(getattr(self._users, "_users_by_id", {}).values())
        if phone:
            items = [item for item in items if item.phone and phone in item.phone]
        if telegram_id is not None:
            items = [item for item in items if item.telegram_id == telegram_id]
        if username:
            needle = username.lower()
            items = [item for item in items if item.username and needle in item.username.lower()]
        if role:
            items = [item for item in items if item.role == role]
        if status:
            items = [item for item in items if item.status == status]
        if cursor:
            items = [item for item in items if item.created_at.isoformat() < cursor]
        items.sort(key=lambda item: item.created_at, reverse=True)
        page = items[:limit]
        return [admin_user_payload(item.__dict__, full_sensitive=full_sensitive) for item in page], page[-1].created_at.isoformat() if len(page) == limit else None

    def get_user_admin(self, user_id: str, *, full_sensitive: bool) -> dict[str, Any] | None:
        user = getattr(self._users, "_users_by_id", {}).get(user_id)
        if user is None:
            return None
        orders = [item for item in getattr(self._orders, "orders", {}).values() if item.remitter_user_id == user_id]
        businesses = [item for item in getattr(self._businesses, "businesses", {}).values() if item.owner_user_id == user_id]
        payload = admin_user_payload(user.__dict__, full_sensitive=full_sensitive)
        payload["order_counts"] = {
            "total": len(orders),
            "active": sum(1 for item in orders if item.status not in {"completed", "cancelled"}),
            "completed": sum(1 for item in orders if item.status == "completed"),
            "disputed": sum(1 for item in orders if item.status == "disputed"),
        }
        payload["businesses"] = [self._business_summary(item) for item in businesses]
        return payload

    def get_user_record_for_admin(self, user_id: str):
        return getattr(self._users, "_users_by_id", {}).get(user_id)

    def set_user_status_for_admin(self, *, user_id: str, status: str):
        self._users.set_user_status(user_id, status)
        return self._users.get_user_by_id(user_id)

    def count_active_super_admins(self) -> int:
        return sum(1 for item in getattr(self._users, "_users_by_id", {}).values() if item.role == "super_admin" and item.status == "active")

    def list_access_links_for_business(self, *, business_id: str, full_sensitive: bool) -> list[dict[str, Any]]:
        return self._list_access_links(
            links=[item for item in getattr(self._businesses, "access_links", {}).values() if item.business_id == business_id],
            full_sensitive=full_sensitive,
        )

    def list_access_links_for_user(self, *, user_id: str, full_sensitive: bool) -> list[dict[str, Any]]:
        return self._list_access_links(
            links=[item for item in getattr(self._businesses, "access_links", {}).values() if item.user_id == user_id],
            full_sensitive=full_sensitive,
        )

    def _list_access_links(self, *, links, full_sensitive: bool) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
        rows = []
        for link in sorted(links, key=lambda item: item.updated_at, reverse=True):
            user = getattr(self._users, "_users_by_id", {}).get(link.user_id)
            business = getattr(self._businesses, "businesses", {}).get(link.business_id)
            rows.append(
                {
                    **link.__dict__,
                    "username": user.username if user else None,
                    "first_name": user.first_name if user else None,
                    "phone": user.phone if user else None,
                    "user_telegram_id": user.telegram_id if user else None,
                    "user_role": user.role if user else None,
                    "user_status": user.status if user else None,
                    "business_name": business.business_name if business else None,
                    "verification_status": business.verification_status if business else None,
                    "risk_level": business.risk_level if business else None,
                }
            )
        return [admin_business_link_payload(row, full_sensitive=full_sensitive) for row in rows]

    def list_orders(self, *, status: str | None, business_id: str | None, remitter_user_id: str | None, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        items = list(getattr(self._orders, "orders", {}).values())
        if status:
            items = [item for item in items if item.status == status]
        if business_id:
            items = [item for item in items if item.business_id == business_id]
        if remitter_user_id:
            items = [item for item in items if item.remitter_user_id == remitter_user_id]
        if cursor:
            items = [item for item in items if item.created_at.isoformat() < cursor]
        items.sort(key=lambda item: item.created_at, reverse=True)
        page = items[:limit]
        return [self._order_summary(item) for item in page], page[-1].created_at.isoformat() if len(page) == limit else None

    def get_order(self, order_id: str) -> dict[str, Any] | None:
        order = getattr(self._orders, "orders", {}).get(order_id)
        if order is None:
            return None
        events = [event for event in getattr(self._orders, "events", []) if event.order_id == order.id]
        payment_report = self._orders.get_latest_payment_report_for_order(order.id)
        return {
            "order": self._order_summary(order),
            "payment_report": self._payment_report_summary(payment_report) if payment_report else None,
            "timeline": [
                {
                    "event_type": event.event_type,
                    "from_status": event.from_status,
                    "to_status": event.to_status,
                    "reason": event.reason,
                    "created_at": event.created_at.isoformat(),
                }
                for event in sorted(events, key=lambda item: item.created_at)
            ],
        }

    def list_audit_logs(self, *, event_type: str | None, actor_user_id: str | None, resource_type: str | None, resource_id: str | None, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        items = list(getattr(self._audit, "events", []))
        if event_type:
            items = [item for item in items if item.event_type == event_type]
        if actor_user_id:
            items = [item for item in items if item.actor_user_id == actor_user_id]
        if resource_type:
            items = [item for item in items if item.resource_type == resource_type]
        if resource_id:
            items = [item for item in items if item.resource_id == resource_id]
        if cursor:
            items = [item for item in items if item.created_at.isoformat() < cursor]
        items.sort(key=lambda item: item.created_at, reverse=True)
        page = items[:limit]
        return [self._audit_summary(item) for item in page], page[-1].created_at.isoformat() if len(page) == limit else None

    def _business_summary(self, business) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return {
            "id": business.id,
            "business_name": business.business_name,
            "verification_status": business.verification_status,
            "risk_level": business.risk_level,
            "trust_level": business.trust_level,
            "created_at": business.created_at.isoformat(),
        }

    def _business_detail(self, business) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        data = self._business_summary(business)
        data.update(
            {
                "owner_user_id": business.owner_user_id,
                "country": business.country,
                "min_order_amount_usd": str(business.min_order_amount_usd),
                "max_order_amount_usd": str(business.max_order_amount_usd),
                "daily_limit_usd": str(business.daily_limit_usd),
                "active_order_limit": business.active_order_limit,
                "completed_orders_count": business.completed_orders_count,
                "disputes_count": business.disputes_count,
                "updated_at": business.updated_at.isoformat(),
            }
        )
        return data

    def _order_summary(self, order) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return {
            "id": order.id,
            "public_order_code": order.public_order_code,
            "status": order.status,
            "business_id": order.business_id,
            "remitter_user_id": order.remitter_user_id,
            "amount_usd": str(order.amount_usd),
            "amount_bs_calculated": str(order.amount_bs_calculated),
            "payment_method_snapshot": order.payment_method_snapshot,
            "delivery_method_snapshot": order.delivery_method_snapshot,
            "created_at": order.created_at.isoformat(),
            "paid_reported_at": iso(order.paid_reported_at),
            "payment_confirmed_at": iso(order.payment_confirmed_at),
            "delivered_at": iso(order.delivered_at),
            "completed_at": iso(order.completed_at),
            "capabilities": {"admin_can_view": True},
        }

    def _payment_report_summary(self, report) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return {
            "id": report.id,
            "status": report.status,
            "payment_type": report.payment_type,
            "payment_amount": str(report.payment_amount),
            "proof_file_id": report.proof_file_id,
            "created_at": report.created_at.isoformat(),
        }

    def _audit_summary(self, event) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        return {
            "event_type": event.event_type,
            "actor_user_id": event.actor_user_id,
            "actor_role": event.actor_role,
            "resource_type": event.resource_type,
            "resource_id": event.resource_id,
            "metadata_json": mask_sensitive(event.metadata_json),
            "created_at": event.created_at.isoformat(),
        }


