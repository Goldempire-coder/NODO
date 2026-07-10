from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.admin.policy import require_admin_read
from app.modules.users.models import UserRecord


ADMIN_DISCLAIMER = "Consola admin: revisa negocios, ordenes y actividad con datos protegidos y trazabilidad."


def _require_uuid(value: str, code: str = "NOT_FOUND") -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError(code, status_code=404) from exc


class AdminService:
    def __init__(self, *, settings: Settings, repository, audit_writer, rate_limiter, read_model_cache=None) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._audit = audit_writer
        self._rate = rate_limiter
        self._read_model_cache = read_model_cache

    def _rate_limit(self, action: str, user: UserRecord) -> None:
        key = f"admin:{action}:{user.id}"
        if not self._rate.allow(key, max_attempts=self._settings.business_rate_limit_max_attempts, window_seconds=self._settings.business_rate_limit_window_seconds):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _audit_view(self, *, event_type: str, user: UserRecord, request_id: str, metadata: dict[str, Any] | None = None) -> None:
        self._audit.write(
            event_type=event_type,
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="admin_console",
            resource_id=user.id,
            request_id=request_id,
            metadata_json=metadata or {},
        )

    def _read_cached_model(self, key: str, compute) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        if self._read_model_cache is None or self._settings.admin_read_model_cache_ttl_seconds <= 0:
            return compute()
        cached = self._read_model_cache.get_json(key)
        if cached is not None:
            return cached
        with self._read_model_cache.lock(key):
            cached = self._read_model_cache.get_json(key)
            if cached is not None:
                return cached
            data = compute()
            self._read_model_cache.set_json(key, data, self._settings.admin_read_model_cache_ttl_seconds)
            return data

    def dashboard(self, *, user: UserRecord, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("dashboard", user)
        data = self._read_cached_model("admin:dashboard:v1", self._repository.dashboard)
        self._audit_view(event_type="admin_viewed_dashboard", user=user, request_id=request_id)
        return data | {"disclaimer": ADMIN_DISCLAIMER}

    def metrics(self, *, user: UserRecord, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("metrics", user)
        data = self._read_cached_model("admin:metrics:v1", self._repository.metrics)
        self._audit_view(event_type="admin_viewed_metrics", user=user, request_id=request_id)
        return data | {"disclaimer": ADMIN_DISCLAIMER, "table_created": False}

    def list_businesses(self, *, user: UserRecord, verification_status: str | None, risk_level: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("businesses", user)
        items, next_cursor = self._repository.list_businesses(verification_status=verification_status, risk_level=risk_level, cursor=cursor, limit=limit)
        return {"items": items, "next_cursor": next_cursor, "disclaimer": ADMIN_DISCLAIMER}

    def business_detail(self, *, user: UserRecord, business_id: str, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        business_id = _require_uuid(business_id, "BUSINESS_NOT_FOUND")
        self._rate_limit("business_detail", user)
        business = self._repository.get_business(business_id)
        if business is None:
            raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
        return {"business": business, "disclaimer": ADMIN_DISCLAIMER}

    def list_orders(self, *, user: UserRecord, status: str | None, business_id: str | None, remitter_user_id: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("orders", user)
        if business_id:
            business_id = _require_uuid(business_id, "BUSINESS_NOT_FOUND")
        if remitter_user_id:
            remitter_user_id = _require_uuid(remitter_user_id, "USER_NOT_FOUND")
        items, next_cursor = self._repository.list_orders(status=status, business_id=business_id, remitter_user_id=remitter_user_id, cursor=cursor, limit=limit)
        return {"items": items, "next_cursor": next_cursor, "disclaimer": ADMIN_DISCLAIMER}

    def order_detail(self, *, user: UserRecord, order_id: str, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        order_id = _require_uuid(order_id, "ORDER_NOT_FOUND")
        self._rate_limit("order_detail", user)
        order = self._repository.get_order(order_id)
        if order is None:
            raise ApiError("ORDER_NOT_FOUND", status_code=404)
        return order | {"disclaimer": ADMIN_DISCLAIMER}

    def audit_logs(self, *, user: UserRecord, event_type: str | None, actor_user_id: str | None, resource_type: str | None, resource_id: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("audit_logs", user)
        if actor_user_id:
            actor_user_id = _require_uuid(actor_user_id, "NOT_FOUND")
        if resource_id:
            resource_id = _require_uuid(resource_id, "NOT_FOUND")
        items, next_cursor = self._repository.list_audit_logs(event_type=event_type, actor_user_id=actor_user_id, resource_type=resource_type, resource_id=resource_id, cursor=cursor, limit=limit)
        self._audit_view(event_type="admin_viewed_audit_logs", user=user, request_id=request_id, metadata={"filters": {"event_type": event_type, "resource_type": resource_type}})
        return {"items": items, "next_cursor": next_cursor, "disclaimer": ADMIN_DISCLAIMER}
