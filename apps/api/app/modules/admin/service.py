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
    def __init__(self, *, settings: Settings, repository, audit_writer, rate_limiter, read_model_cache=None, idempotency_store=None, auth_user_cache=None) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._audit = audit_writer
        self._rate = rate_limiter
        self._read_model_cache = read_model_cache
        self._idempotency = idempotency_store
        self._auth_user_cache = auth_user_cache

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

    def _aggregate_cache_key(self, model_name: str, user: UserRecord) -> str:
        return f"admin:{model_name}:v1:role:{user.role}"

    def _invalidate_auth_user_cache(self, user_id: str) -> None:
        if self._auth_user_cache is None:
            return
        self._auth_user_cache.clear_prefix(f"auth:user:{user_id}")

    def dashboard(self, *, user: UserRecord, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("dashboard", user)
        data = self._read_cached_model(self._aggregate_cache_key("dashboard", user), self._repository.dashboard)
        self._audit_view(event_type="admin_viewed_dashboard", user=user, request_id=request_id)
        return data | {"disclaimer": ADMIN_DISCLAIMER}

    def metrics(self, *, user: UserRecord, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("metrics", user)
        data = self._read_cached_model(self._aggregate_cache_key("metrics", user), self._repository.metrics)
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

    def list_users(
        self,
        *,
        user: UserRecord,
        phone: str | None,
        telegram_id: str | None,
        username: str | None,
        role: str | None,
        status: str | None,
        cursor: str | None,
        limit: int,
        request_id: str,
    ) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("users", user)
        parsed_telegram_id = self._parse_telegram_id(telegram_id)
        items, next_cursor = self._repository.list_users(
            phone=phone,
            telegram_id=parsed_telegram_id,
            username=username,
            role=role,
            status=status,
            cursor=cursor,
            limit=limit,
            full_sensitive=self._can_view_sensitive_user_fields(user),
        )
        return {"items": items, "next_cursor": next_cursor, "disclaimer": ADMIN_DISCLAIMER}

    def user_detail(self, *, user: UserRecord, target_user_id: str, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        target_user_id = _require_uuid(target_user_id, "USER_NOT_FOUND")
        self._rate_limit("user_detail", user)
        target = self._repository.get_user_admin(target_user_id, full_sensitive=self._can_view_sensitive_user_fields(user))
        if target is None:
            raise ApiError("USER_NOT_FOUND", status_code=404)
        access_links = self._repository.list_access_links_for_user(user_id=target_user_id, full_sensitive=self._can_view_sensitive_user_fields(user))
        return {
            "user": target,
            "access_links": access_links,
            "capabilities": {
                "can_mutate_status": user.role in {"admin", "super_admin"},
                "can_view_sensitive": self._can_view_sensitive_user_fields(user),
            },
            "disclaimer": ADMIN_DISCLAIMER,
        }

    def list_user_access_links(self, *, user: UserRecord, target_user_id: str, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        target_user_id = _require_uuid(target_user_id, "USER_NOT_FOUND")
        self._rate_limit("user_access_links", user)
        if self._repository.get_user_record_for_admin(target_user_id) is None:
            raise ApiError("USER_NOT_FOUND", status_code=404)
        return {
            "items": self._repository.list_access_links_for_user(user_id=target_user_id, full_sensitive=self._can_view_sensitive_user_fields(user)),
            "disclaimer": ADMIN_DISCLAIMER,
        }

    def list_business_access_links(self, *, user: UserRecord, business_id: str, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        business_id = _require_uuid(business_id, "BUSINESS_NOT_FOUND")
        self._rate_limit("business_access_links", user)
        if self._repository.get_business(business_id) is None:
            raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
        return {
            "items": self._repository.list_access_links_for_business(business_id=business_id, full_sensitive=self._can_view_sensitive_user_fields(user)),
            "disclaimer": ADMIN_DISCLAIMER,
        }

    def suspend_user(self, *, user: UserRecord, target_user_id: str, reason: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._change_user_status(user=user, target_user_id=target_user_id, action="suspend", next_status="restricted", reason=reason, request_id=request_id, idempotency_key=idempotency_key)

    def reactivate_user(self, *, user: UserRecord, target_user_id: str, reason: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._change_user_status(user=user, target_user_id=target_user_id, action="reactivate", next_status="active", reason=reason, request_id=request_id, idempotency_key=idempotency_key)

    def block_user(self, *, user: UserRecord, target_user_id: str, reason: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._change_user_status(user=user, target_user_id=target_user_id, action="block", next_status="blocked", reason=reason, request_id=request_id, idempotency_key=idempotency_key)

    def _change_user_status(
        self,
        *,
        user: UserRecord,
        target_user_id: str,
        action: str,
        next_status: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        if user.status != "active" or user.role not in {"admin", "super_admin"}:
            raise ApiError("FORBIDDEN", status_code=403)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        reason = reason.strip()
        if not reason:
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
        target_user_id = _require_uuid(target_user_id, "USER_NOT_FOUND")

        def compute() -> dict[str, Any]:
            return self._compute_user_status_change(user=user, target_user_id=target_user_id, action=action, next_status=next_status, reason=reason, request_id=request_id)

        if self._idempotency is None:
            return compute()
        return self._idempotency.replay_or_store(
            f"admin_user:{action}:{target_user_id}:{idempotency_key}",
            payload={"target_user_id": target_user_id, "action": action, "reason": reason},
            compute=compute,
        )

    def _compute_user_status_change(self, *, user: UserRecord, target_user_id: str, action: str, next_status: str, reason: str, request_id: str) -> dict[str, Any]:
        target = self._repository.get_user_record_for_admin(target_user_id)
        if target is None:
            raise ApiError("USER_NOT_FOUND", status_code=404)
        self._ensure_user_mutation_allowed(actor=user, target=target, action=action)
        self._ensure_user_transition_allowed(current_status=target.status, action=action)
        previous_status = target.status
        updated = self._repository.set_user_status_for_admin(user_id=target.id, status=next_status)
        self._invalidate_auth_user_cache(target.id)
        event_type = {"suspend": "user_suspended", "reactivate": "user_reactivated", "block": "user_blocked"}[action]
        self._audit.write(
            event_type=event_type,
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="user",
            resource_id=target.id,
            request_id=request_id,
            metadata_json={"reason": reason, "from_status": previous_status, "to_status": next_status},
        )
        return {
            "user": self._repository.get_user_admin(updated.id, full_sensitive=self._can_view_sensitive_user_fields(user)),
            "disclaimer": ADMIN_DISCLAIMER,
        }

    def _ensure_user_mutation_allowed(self, *, actor: UserRecord, target: UserRecord, action: str) -> None:
        if actor.role == "admin" and target.role in {"admin", "super_admin"}:
            raise ApiError("USER_STATUS_MUTATION_NOT_ALLOWED", status_code=403)
        if target.role == "super_admin" and target.status == "active" and action in {"suspend", "block"} and self._repository.count_active_super_admins() <= 1:
            raise ApiError("LAST_SUPER_ADMIN_REQUIRED", status_code=409)

    def _ensure_user_transition_allowed(self, *, current_status: str, action: str) -> None:
        allowed = {
            "suspend": {"active"},
            "reactivate": {"restricted", "dormant"},
            "block": {"active", "restricted", "dormant"},
        }[action]
        if current_status not in allowed:
            raise ApiError("USER_STATUS_TRANSITION_INVALID", status_code=409)

    def _parse_telegram_id(self, value: str | None) -> int | None:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except ValueError as exc:
            raise ApiError("VALIDATION_ERROR", status_code=422) from exc

    def _can_view_sensitive_user_fields(self, user: UserRecord) -> bool:
        return user.role in {"admin", "super_admin"}

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
