from __future__ import annotations

from typing import Any
from uuid import UUID

from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.admin.investigation import query_fingerprint
from app.modules.jobs.serializers import job_run_summary
from app.modules.admin.policy import require_admin_mutation, require_admin_read
from app.modules.admin.user_presenters import mask_phone
from app.modules.notifications.user_status_notifications import NoopUserStatusNotificationService, UserStatusNotificationService
from app.modules.users.models import UserRecord
from app.services.health_service import HealthService


ADMIN_DISCLAIMER = "Consola admin: revisa negocios, ordenes y actividad con datos limitados y trazabilidad."


def _require_uuid(value: str, code: str = "NOT_FOUND") -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError(code, status_code=404) from exc


def _normalize_public_order_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper().replace(" ", "")
    if not normalized:
        return None
    if normalized.startswith("NODO-"):
        return normalized
    if len(normalized) == 8:
        return f"NODO-{normalized}"
    return normalized


def _normalize_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = " ".join(value.strip().split())
    return normalized or None


class AdminService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository,
        audit_writer,
        rate_limiter,
        read_model_cache=None,
        idempotency_store=None,
        auth_user_cache=None,
        emergency_mode_repository=None,
        job_repository=None,
        observability_repository=None,
        user_status_notifications=None,
    ) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._audit = audit_writer
        self._rate = rate_limiter
        self._read_model_cache = read_model_cache
        self._idempotency = idempotency_store
        self._auth_user_cache = auth_user_cache
        self._emergency_mode = emergency_mode_repository
        self._job_repository = job_repository
        self._observability_repository = observability_repository
        self._user_status_notifications = user_status_notifications or (
            UserStatusNotificationService(settings=settings, job_repository=job_repository)
            if job_repository is not None
            else NoopUserStatusNotificationService()
        )

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
        return data | {"emergency_mode": self._emergency_mode_payload(), "disclaimer": ADMIN_DISCLAIMER}

    def emergency_mode(self, *, user: UserRecord, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("emergency_mode", user)
        self._audit_view(event_type="admin_viewed_emergency_mode", user=user, request_id=request_id)
        return {"emergency_mode": self._emergency_mode_payload(), "disclaimer": ADMIN_DISCLAIMER}

    def activate_emergency_mode(self, *, user: UserRecord, reason: str, message: str | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._change_emergency_mode(
            user=user,
            enabled=True,
            reason=reason,
            message=message,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def deactivate_emergency_mode(self, *, user: UserRecord, reason: str, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        return self._change_emergency_mode(
            user=user,
            enabled=False,
            reason=reason,
            message=None,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def _change_emergency_mode(
        self,
        *,
        user: UserRecord,
        enabled: bool,
        reason: str,
        message: str | None,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        if not idempotency_key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        reason = reason.strip()
        message = message.strip() if message else None
        if not reason:
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)

        action = "activate" if enabled else "deactivate"

        def compute() -> dict[str, Any]:
            record = self._require_emergency_mode_repository().set_enabled(
                enabled=enabled,
                reason=reason,
                message=message,
                actor_user_id=user.id,
            )
            self._audit.write(
                event_type="platform_emergency_mode_activated" if enabled else "platform_emergency_mode_deactivated",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="platform_emergency_mode",
                resource_id=None,
                request_id=request_id,
                metadata_json={"reason": reason, "message": message, "enabled": enabled},
            )
            return {"emergency_mode": record.to_payload(), "disclaimer": ADMIN_DISCLAIMER}

        if self._idempotency is None:
            return compute()
        return self._idempotency.replay_or_store(
            f"admin_emergency_mode:{action}:{idempotency_key}",
            payload={"enabled": enabled, "reason": reason, "message": message},
            compute=compute,
        )

    def _require_emergency_mode_repository(self):  # type: ignore[no-untyped-def]
        if self._emergency_mode is None:
            raise ApiError("INTERNAL_ERROR", status_code=500)
        return self._emergency_mode

    def _emergency_mode_payload(self) -> dict[str, Any]:
        if self._emergency_mode is None:
            return {"enabled": False, "reason": None, "message": None, "updated_at": None}
        return self._emergency_mode.get().to_payload()

    def metrics(self, *, user: UserRecord, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("metrics", user)
        data = self._read_cached_model(self._aggregate_cache_key("metrics", user), self._repository.metrics)
        self._audit_view(event_type="admin_viewed_metrics", user=user, request_id=request_id)
        return data | {"disclaimer": ADMIN_DISCLAIMER, "table_created": False}

    def incident_console(self, *, user: UserRecord, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("incident_console", user)
        dashboard = self._read_cached_model(self._aggregate_cache_key("dashboard", user), self._repository.dashboard)
        readiness = self._safe_readiness()
        emergency_mode = self._emergency_mode_payload()
        job_summary = self._job_incident_summary()
        notification_summary = self._notification_incident_summary()
        audit_items, _ = self._repository.list_audit_logs(event_type=None, actor_user_id=None, resource_type=None, resource_id=None, cursor=None, limit=10)
        recent_audit = [{key: value for key, value in item.items() if key != "metadata_json"} for item in audit_items]
        status = self._incident_status(
            readiness=readiness,
            emergency_mode=emergency_mode,
            dashboard=dashboard,
            job_summary=job_summary,
            notification_summary=notification_summary,
        )
        self._audit_view(event_type="admin_viewed_incident_console", user=user, request_id=request_id)
        return {
            "status": status,
            "generated_at": None,
            "environment": self._settings.app_env,
            "version": self._settings.app_version,
            "build_id": self._settings.build_id,
            "emergency_mode": emergency_mode,
            "dependencies": readiness,
            "queues": dashboard.get("queues", {}),
            "orders": dashboard.get("orders", {}),
            "jobs": job_summary,
            "notifications": notification_summary,
            "recent_audit": recent_audit,
            "recommended_actions": self._incident_actions(status=status, readiness=readiness, emergency_mode=emergency_mode, notification_summary=notification_summary),
            "disclaimer": "Centro de incidentes: resumen operativo calculado desde fuentes existentes; no reemplaza logs provider.",
        }

    def ux_friction(self, *, user: UserRecord, window_hours: int, limit: int, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("ux_friction", user)
        if self._observability_repository is None:
            data = {
                "ingest_enabled": self._settings.observability_ingest_enabled,
                "window_hours": window_hours,
                "total_events": 0,
                "unique_sessions": 0,
                "friction_events": 0,
                "surfaces": [],
                "top_screens": [],
                "top_actions": [],
                "api_failures": [],
                "recent_friction": [],
                "recommended_actions": ["Configurar repositorio de observabilidad frontend antes de usar este panel."],
                "disclaimer": "Panel UX: no hay repositorio de eventos configurado.",
            }
        else:
            data = self._observability_repository.ux_friction_summary(
                ingest_enabled=self._settings.observability_ingest_enabled,
                window_hours=window_hours,
                limit=limit,
            )
        self._audit_view(event_type="admin_viewed_ux_friction", user=user, request_id=request_id, metadata={"window_hours": window_hours, "limit": limit})
        return data

    def _safe_readiness(self) -> dict[str, Any]:
        try:
            ok, payload = HealthService(self._settings).readiness()
            return {"ok": ok, **payload}
        except Exception as exc:
            return {
                "ok": False,
                "status": "not_ready",
                "checks": {
                    "readiness": {
                        "ok": False,
                        "code": getattr(exc, "code", "READINESS_CHECK_FAILED"),
                        "message": "No se pudo verificar readiness desde admin.",
                    }
                },
            }

    def _job_incident_summary(self) -> dict[str, Any]:
        if self._job_repository is None:
            return {"status_counts": {}, "recent_runs": [], "recent_failed": []}
        runs, _ = self._job_repository.list_job_runs(job_type=None, status=None, cursor=None, limit=20)
        status_counts: dict[str, int] = {}
        for run in runs:
            status_counts[run.status] = status_counts.get(run.status, 0) + 1
        recent_failed = [job_run_summary(run) | {"error_message_safe": run.error_message_safe} for run in runs if run.status == "failed" or run.failed_count > 0]
        return {
            "status_counts": status_counts,
            "recent_runs": [job_run_summary(run) for run in runs[:5]],
            "recent_failed": recent_failed[:5],
        }

    def _notification_incident_summary(self) -> dict[str, Any]:
        if self._job_repository is None or not hasattr(self._job_repository, "notification_incident_summary"):
            return {"status_counts": {}, "pending_due": 0, "recent_problems": []}
        return self._job_repository.notification_incident_summary(limit=10)

    def _incident_status(
        self,
        *,
        readiness: dict[str, Any],
        emergency_mode: dict[str, Any],
        dashboard: dict[str, Any],
        job_summary: dict[str, Any],
        notification_summary: dict[str, Any],
    ) -> str:
        if not readiness.get("ok") or emergency_mode.get("enabled"):
            return "critical"
        if job_summary.get("recent_failed") or notification_summary.get("recent_problems"):
            return "degraded"
        queues = dashboard.get("queues", {})
        orders = dashboard.get("orders", {})
        if queues.get("open_disputes", 0) or queues.get("pending_credit_purchases", 0) or orders.get("delivered_waiting_close_count", 0):
            return "attention"
        return "healthy"

    def _incident_actions(self, *, status: str, readiness: dict[str, Any], emergency_mode: dict[str, Any], notification_summary: dict[str, Any]) -> list[str]:
        actions: list[str] = []
        if not readiness.get("ok"):
            actions.append("Revisar dependencias en Railway/Supabase/Redis antes de tocar producto.")
        if status == "critical" and not emergency_mode.get("enabled"):
            actions.append("Considerar activar modo emergencia si hay impacto en usuarios.")
        if notification_summary.get("recent_problems"):
            actions.append("Revisar notificaciones fallidas y correlacionarlas con ordenes afectadas.")
        actions.append("Usar request_id/correlation_id para buscar el detalle en logs provider.")
        return actions

    def list_businesses(
        self,
        *,
        user: UserRecord,
        verification_status: str | None,
        risk_level: str | None,
        business_id: str | None,
        business_name: str | None,
        cursor: str | None,
        limit: int,
        request_id: str,
    ) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("businesses", user)
        normalized_business_id = _require_uuid(business_id, "BUSINESS_NOT_FOUND") if business_id else None
        normalized_business_name = _normalize_optional_text(business_name)
        if normalized_business_name and len(normalized_business_name) < 3:
            raise ApiError("ADMIN_BUSINESS_SEARCH_QUERY_TOO_SHORT", status_code=400)
        items, next_cursor = self._repository.list_businesses(
            verification_status=verification_status,
            risk_level=risk_level,
            business_id=normalized_business_id,
            business_name=normalized_business_name,
            cursor=cursor,
            limit=limit,
        )
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

    def operational_search(self, *, user: UserRecord, query: str, limit: int, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        normalized_query = query.strip()
        if len(normalized_query) < 3:
            raise ApiError("ADMIN_OPERATIONAL_SEARCH_QUERY_TOO_SHORT", status_code=400)
        self._rate_limit("operational_search", user)
        data = self._repository.operational_search(
            query=normalized_query,
            limit=limit,
            full_sensitive=self._can_view_sensitive_user_fields(user),
        )
        self._audit_view(
            event_type="admin_operational_search_performed",
            user=user,
            request_id=request_id,
            metadata={
                "query_hash": query_fingerprint(normalized_query),
                "query_length": len(normalized_query),
                "limit": limit,
                "result_counts": data.get("result_counts", {}),
            },
        )
        return data | {"disclaimer": ADMIN_DISCLAIMER}

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

    def reveal_user_phone(self, *, user: UserRecord, target_user_id: str, reason: str, request_id: str) -> dict[str, Any]:
        require_admin_mutation(user)
        target_user_id = _require_uuid(target_user_id, "USER_NOT_FOUND")
        reason = reason.strip()
        if not reason:
            raise ApiError("ADMIN_REASON_REQUIRED", status_code=400)
        self._rate_limit("user_phone_reveal", user)
        target = self._repository.get_user_record_for_admin(target_user_id)
        if target is None:
            raise ApiError("USER_NOT_FOUND", status_code=404)
        self._audit.write(
            event_type="admin_user_phone_revealed",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="user",
            resource_id=target_user_id,
            request_id=request_id,
            metadata_json={
                "reason_hash": query_fingerprint(reason),
                "target_role": target.role,
                "has_phone": bool(target.phone),
            },
        )
        return {
            "user_id": target_user_id,
            "phone": target.phone,
            "phone_masked": mask_phone(target.phone),
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
        updated_payload = self._repository.get_user_admin(updated.id, full_sensitive=self._can_view_sensitive_user_fields(user))
        notification_type = {
            "suspend": "user_suspended_account",
            "reactivate": "user_reactivated_account",
            "block": "user_blocked_account",
        }[action]
        self._user_status_notifications.user_status_changed(
            target=updated,
            notification_type=notification_type,
            previous_status=previous_status,
            business_id=self._primary_business_id_from_user_payload(updated_payload),
            request_id=request_id,
        )
        return {
            "user": updated_payload,
            "disclaimer": ADMIN_DISCLAIMER,
        }

    def _primary_business_id_from_user_payload(self, payload: dict[str, Any] | None) -> str | None:
        if not payload:
            return None
        businesses = payload.get("businesses") or []
        if not businesses:
            return None
        for business in businesses:
            if business.get("verification_status") in {"approved", "suspended", "blocked"}:
                return str(business.get("id"))
        return str(businesses[0].get("id"))

    def _ensure_user_mutation_allowed(self, *, actor: UserRecord, target: UserRecord, action: str) -> None:
        if actor.role == "admin" and target.role in {"admin", "super_admin"}:
            raise ApiError("USER_STATUS_MUTATION_NOT_ALLOWED", status_code=403)
        if target.role == "super_admin" and target.status == "active" and action in {"suspend", "block"} and self._repository.count_active_super_admins() <= 1:
            raise ApiError("LAST_SUPER_ADMIN_REQUIRED", status_code=409)

    def _ensure_user_transition_allowed(self, *, current_status: str, action: str) -> None:
        allowed = {
            "suspend": {"active"},
            "reactivate": {"restricted", "dormant", "blocked"},
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

    def list_orders(self, *, user: UserRecord, status: str | None, business_id: str | None, remitter_user_id: str | None, public_order_code: str | None, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        require_admin_read(user)
        self._rate_limit("orders", user)
        if business_id:
            business_id = _require_uuid(business_id, "BUSINESS_NOT_FOUND")
        if remitter_user_id:
            remitter_user_id = _require_uuid(remitter_user_id, "USER_NOT_FOUND")
        public_order_code = _normalize_public_order_code(public_order_code)
        items, next_cursor = self._repository.list_orders(status=status, business_id=business_id, remitter_user_id=remitter_user_id, public_order_code=public_order_code, cursor=cursor, limit=limit)
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
