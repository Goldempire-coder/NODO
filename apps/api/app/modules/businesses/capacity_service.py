from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.business_capacity.models import BusinessCapacitySnapshot
from app.modules.businesses.access_link_rules import require_idempotency_key
from app.modules.businesses.access_control import require_active_business_access
from app.modules.businesses.policy import require_admin_mutation, require_admin_view
from app.modules.businesses.schemas import (
    AdminOperationalCapacityUpdateRequest,
    BusinessCapacityUpdateRequest,
)
from app.modules.users.models import UserRecord


def _money(value) -> str:  # type: ignore[no-untyped-def]
    return f"{value:.2f}"


class BusinessCapacityServiceMixin:
    def _capacity_payload(
        self,
        *,
        business,
        snapshot: BusinessCapacitySnapshot,
        include_reservations: bool = False,
        include_updater: bool = False,
    ) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        data: dict[str, Any] = {
            "business_id": business.id,
            "availability_status": "online" if business.is_accepting_orders else "offline",
            "declared_available_capacity_usd": _money(snapshot.declared_available_capacity_usd),
            "reserved_capacity_usd": _money(snapshot.reserved_capacity_usd),
            "effective_available_capacity_usd": _money(snapshot.effective_available_capacity_usd),
            "min_order_amount_usd": _money(business.min_order_amount_usd),
            "max_order_amount_usd": _money(business.max_order_amount_usd),
            "daily_limit_usd": _money(business.daily_limit_usd),
            "daily_remaining_usd": _money(snapshot.daily_remaining_usd),
            "updated_at": snapshot.updated_at.isoformat() if snapshot.updated_at else None,
            "capabilities": {
                "can_go_online": business.verification_status == "approved"
                and business.risk_level not in {"restricted", "high_risk"},
                "can_accept_new_orders": (
                    business.is_accepting_orders
                    and snapshot.effective_available_capacity_usd >= business.min_order_amount_usd
                    and snapshot.daily_remaining_usd >= business.min_order_amount_usd
                ),
            },
        }
        if include_reservations:
            data["active_reservations"] = [
                {
                    "order_id": reservation.order_id,
                    "amount_usd": _money(reservation.amount_usd),
                    "status": reservation.status,
                    "created_at": reservation.created_at.isoformat(),
                }
                for reservation in snapshot.reservations
            ]
        if include_updater:
            data["updated_by_user_id"] = snapshot.updated_by_user_id
        return data

    def own_capacity(self, *, user: UserRecord) -> dict[str, Any]:
        self._rate_limit("capacity_read", user)  # type: ignore[attr-defined]
        business, _ = require_active_business_access(
            user=user,
            business_repository=self._repository,  # type: ignore[attr-defined]
        )
        snapshot = self._capacity.get_snapshot(business=business)  # type: ignore[attr-defined]
        return self._capacity_payload(business=business, snapshot=snapshot)

    def update_own_capacity(
        self,
        *,
        user: UserRecord,
        payload: BusinessCapacityUpdateRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._rate_limit("capacity_write", user)  # type: ignore[attr-defined]
        require_idempotency_key(idempotency_key)
        self.require_unlocked_business_pin(user=user)  # type: ignore[attr-defined]
        business, _ = require_active_business_access(
            user=user,
            business_repository=self._repository,  # type: ignore[attr-defined]
        )
        if business.verification_status != "approved" or business.risk_level in {"restricted", "high_risk"}:
            raise ApiError("BUSINESS_NOT_APPROVED", status_code=409)
        if payload.declared_available_capacity_usd > business.daily_limit_usd:
            raise ApiError("CAPACITY_AMOUNT_INVALID", status_code=400)
        accepting_orders = payload.availability_status == "online"

        def compute() -> dict[str, Any]:
            before = self._capacity.get_snapshot(business=business)  # type: ignore[attr-defined]
            snapshot = self._capacity.update_capacity_and_availability(  # type: ignore[attr-defined]
                business=business,
                amount_usd=payload.declared_available_capacity_usd,
                accepting_orders=accepting_orders,
                actor_user_id=user.id,
            )
            self._audit.write(  # type: ignore[attr-defined]
                event_type="business_capacity_updated",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business",
                resource_id=business.id,
                request_id=request_id,
                metadata_json={
                    "before_declared_usd": _money(before.declared_available_capacity_usd),
                    "after_declared_usd": _money(snapshot.declared_available_capacity_usd),
                    "availability_status": payload.availability_status,
                },
            )
            self._clear_marketplace_cache_for_business_status_change()  # type: ignore[attr-defined]
            return self._capacity_payload(business=business, snapshot=snapshot)

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"business:operational-capacity:{business.id}:{idempotency_key}",
            payload={
                "business_id": business.id,
                "availability_status": payload.availability_status,
                "declared_available_capacity_usd": payload.declared_available_capacity_usd,
            },
            compute=compute,
        )

    def admin_capacity(self, *, user: UserRecord, business_id: str) -> dict[str, Any]:
        require_admin_view(user)
        self._rate_limit("admin_capacity_read", user)  # type: ignore[attr-defined]
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        snapshot = self._capacity.get_snapshot(  # type: ignore[attr-defined]
            business=business,
            include_reservations=True,
        )
        return self._capacity_payload(
            business=business,
            snapshot=snapshot,
            include_reservations=True,
            include_updater=True,
        )

    def admin_update_operational_capacity(
        self,
        *,
        user: UserRecord,
        business_id: str,
        payload: AdminOperationalCapacityUpdateRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("admin_capacity_write", user)  # type: ignore[attr-defined]
        require_idempotency_key(idempotency_key)
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        if payload.declared_available_capacity_usd > business.daily_limit_usd:
            raise ApiError("CAPACITY_AMOUNT_INVALID", status_code=400)

        def compute() -> dict[str, Any]:
            before = self._capacity.get_snapshot(business=business)  # type: ignore[attr-defined]
            self._capacity.set_declared_capacity(  # type: ignore[attr-defined]
                business_id=business.id,
                amount_usd=payload.declared_available_capacity_usd,
                actor_user_id=user.id,
            )
            snapshot = self._capacity.get_snapshot(  # type: ignore[attr-defined]
                business=business,
                include_reservations=True,
            )
            self._audit.write(  # type: ignore[attr-defined]
                event_type="business_capacity_updated",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business",
                resource_id=business.id,
                request_id=request_id,
                metadata_json={
                    "source": "admin",
                    "reason": payload.reason or "admin_operational_adjustment",
                    "before_declared_usd": _money(before.declared_available_capacity_usd),
                    "after_declared_usd": _money(snapshot.declared_available_capacity_usd),
                },
            )
            self._clear_marketplace_cache_for_business_status_change()  # type: ignore[attr-defined]
            return self._capacity_payload(
                business=business,
                snapshot=snapshot,
                include_reservations=True,
                include_updater=True,
            )

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"admin:business-operational-capacity:{business.id}:{idempotency_key}",
            payload={
                "business_id": business.id,
                "declared_available_capacity_usd": payload.declared_available_capacity_usd,
                "reason": payload.reason,
            },
            compute=compute,
        )
