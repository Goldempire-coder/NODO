from __future__ import annotations

from datetime import timedelta
from typing import Any

from app.core.config import Settings
from app.core.errors import ApiError
from app.modules.ads.marketplace_cache import MARKETPLACE_CACHE_PREFIX
from app.modules.businesses.access_link_rules import require_idempotency_key
from app.modules.businesses.access_link_service import BusinessAccessLinkServiceMixin
from app.modules.businesses.access_control import require_active_business_access
from app.modules.businesses.admin_review_service import BusinessAdminReviewServiceMixin
from app.modules.businesses.models import BusinessAccessLinkRecord, BusinessRecord, utc_now
from app.modules.businesses.pin_security import hash_pin, verify_pin
from app.modules.businesses.presenters import business_payload, mask_account, payment_method_display
from app.modules.businesses.schemas import BusinessAvailabilityUpdateRequest, BusinessOwnPaymentMethodCreateRequest, BusinessOwnPaymentMethodUpdateRequest, BusinessPinSetupRequest, BusinessPinVerifyRequest
from app.modules.notifications.business_access_notifications import NoopBusinessAccessNotificationService
from app.modules.notifications.business_status_notifications import NoopBusinessStatusNotificationService
from app.modules.users.models import UserRecord

BUSINESS_PIN_UNLOCK_TTL_SECONDS = 900
BUSINESS_PIN_MAX_FAILED_ATTEMPTS = 5
BUSINESS_PIN_LOCK_SECONDS = 600
TRON_BASE58_ALPHABET = set("123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz")


class BusinessService(BusinessAccessLinkServiceMixin, BusinessAdminReviewServiceMixin):
    def __init__(self, *, settings: Settings, repository, user_repository, audit_writer, rate_limiter, idempotency_store, storage, marketplace_cache=None, business_status_notifications=None, business_access_notifications=None) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._users = user_repository
        self._audit = audit_writer
        self._rate_limiter = rate_limiter
        self._idempotency = idempotency_store
        self._storage = storage
        self._marketplace_cache = marketplace_cache
        self._business_status_notifications = business_status_notifications or NoopBusinessStatusNotificationService()
        self._business_access_notifications = business_access_notifications or NoopBusinessAccessNotificationService()

    def _rate_limit(self, action: str, user: UserRecord) -> None:
        key = f"business:{action}:{user.id}"
        if not self._rate_limiter.allow(
            key,
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _business_or_404(self, business_id: str) -> BusinessRecord:
        business = self._repository.get_business(business_id)
        if business is None:
            raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
        return business

    def _clear_marketplace_cache_for_business_status_change(self) -> None:
        if self._marketplace_cache is not None:
            self._marketplace_cache.clear_prefix(MARKETPLACE_CACHE_PREFIX)

    def my_business(self, *, user: UserRecord) -> dict[str, Any]:
        business = self._repository.get_active_business_for_owner(user.id)
        return {"business": business_payload(business) if business else None}

    def update_own_availability(self, *, user: UserRecord, payload: BusinessAvailabilityUpdateRequest, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._rate_limit("availability_write", user)
        require_idempotency_key(idempotency_key)
        self.require_unlocked_business_pin(user=user)
        business, _ = require_active_business_access(user=user, business_repository=self._repository)
        if business.verification_status != "approved" or business.risk_level in {"restricted", "high_risk"}:
            raise ApiError("BUSINESS_NOT_APPROVED", status_code=409)

        def compute() -> dict[str, Any]:
            updated = self._repository.update_business_accepting_orders(business.id, payload.accepting_orders)
            if updated is None:
                raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
            self._audit.write(
                event_type="business_accepting_orders_updated",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business",
                resource_id=business.id,
                request_id=request_id,
                metadata_json={"accepting_orders": payload.accepting_orders},
            )
            self._clear_marketplace_cache_for_business_status_change()
            return {"business": business_payload(updated)}

        return self._idempotency.replay_or_store(
            f"business:availability:{business.id}:{idempotency_key}",
            payload={"business_id": business.id, "accepting_orders": payload.accepting_orders},
            compute=compute,
        )

    def _pin_unlocked(self, link: BusinessAccessLinkRecord) -> bool:
        return link.business_pin_unlocked_until is not None and link.business_pin_unlocked_until > utc_now()

    def _pin_locked(self, link: BusinessAccessLinkRecord) -> bool:
        return link.business_pin_locked_until is not None and link.business_pin_locked_until > utc_now()

    def _pin_status_payload(self, link: BusinessAccessLinkRecord) -> dict[str, Any]:
        return {
            "required": True,
            "configured": link.business_pin_hash is not None,
            "unlocked": self._pin_unlocked(link),
            "failed_attempts": link.business_pin_failed_attempts,
            "locked_until": link.business_pin_locked_until.isoformat() if self._pin_locked(link) else None,
            "unlocked_until": link.business_pin_unlocked_until.isoformat() if self._pin_unlocked(link) else None,
        }

    def business_pin_status(self, *, user: UserRecord) -> dict[str, Any]:
        _, link = require_active_business_access(user=user, business_repository=self._repository)
        return {"pin": self._pin_status_payload(link)}

    def setup_business_pin(self, *, user: UserRecord, payload: BusinessPinSetupRequest, request_id: str) -> dict[str, Any]:
        business, link = require_active_business_access(user=user, business_repository=self._repository)
        if link.business_pin_hash is not None:
            if not payload.current_pin:
                raise ApiError("BUSINESS_PIN_CURRENT_REQUIRED", status_code=400)
            self._verify_current_pin_or_fail(link=link, pin=payload.current_pin, request_id=request_id, user=user)
        updated = self._repository.set_access_link_pin_hash(link_id=link.id, pin_hash=hash_pin(payload.pin))
        updated = self._repository.mark_access_link_pin_verified(
            link_id=updated.id,
            unlocked_until=utc_now() + timedelta(seconds=BUSINESS_PIN_UNLOCK_TTL_SECONDS),
        )
        self._audit.write(
            event_type="business_pin_set",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business_access_link",
            resource_id=link.id,
            request_id=request_id,
            metadata_json={"business_id": business.id, "changed_existing_pin": link.business_pin_hash is not None},
        )
        return {"pin": self._pin_status_payload(updated)}

    def verify_business_pin(self, *, user: UserRecord, payload: BusinessPinVerifyRequest, request_id: str) -> dict[str, Any]:
        _, link = require_active_business_access(user=user, business_repository=self._repository)
        updated = self._verify_current_pin_or_fail(link=link, pin=payload.pin, request_id=request_id, user=user)
        return {"pin": self._pin_status_payload(updated)}

    def lock_business_pin(self, *, user: UserRecord, request_id: str) -> dict[str, Any]:
        _, link = require_active_business_access(user=user, business_repository=self._repository)
        if link.business_pin_hash is None:
            return {"pin": self._pin_status_payload(link)}
        updated = self._repository.lock_access_link_pin(link_id=link.id)
        self._audit.write(
            event_type="business_pin_locked",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business_access_link",
            resource_id=link.id,
            request_id=request_id,
        )
        return {"pin": self._pin_status_payload(updated)}

    def require_unlocked_business_pin(self, *, user: UserRecord) -> None:
        _, link = require_active_business_access(user=user, business_repository=self._repository)
        if link.business_pin_hash is None:
            raise ApiError("BUSINESS_PIN_NOT_SET", status_code=423)
        if self._pin_locked(link):
            raise ApiError("BUSINESS_PIN_LOCKED", status_code=423)
        if not self._pin_unlocked(link):
            raise ApiError("BUSINESS_PIN_REQUIRED", status_code=423)

    def _verify_current_pin_or_fail(self, *, link: BusinessAccessLinkRecord, pin: str, request_id: str, user: UserRecord) -> BusinessAccessLinkRecord:
        if link.business_pin_hash is None:
            raise ApiError("BUSINESS_PIN_NOT_SET", status_code=423)
        if self._pin_locked(link):
            raise ApiError("BUSINESS_PIN_LOCKED", status_code=423)
        if not verify_pin(pin, link.business_pin_hash):
            failed_attempts = link.business_pin_failed_attempts + 1
            locked_until = utc_now() + timedelta(seconds=BUSINESS_PIN_LOCK_SECONDS) if failed_attempts >= BUSINESS_PIN_MAX_FAILED_ATTEMPTS else None
            updated = self._repository.record_access_link_pin_failure(
                link_id=link.id,
                failed_attempts=failed_attempts,
                locked_until=locked_until,
            )
            self._audit.write(
                event_type="business_pin_failed",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business_access_link",
                resource_id=link.id,
                request_id=request_id,
                metadata_json={
                    "failed_attempts": updated.business_pin_failed_attempts,
                    "locked": locked_until is not None,
                },
            )
            raise ApiError("BUSINESS_PIN_INVALID", status_code=403)
        updated = self._repository.mark_access_link_pin_verified(
            link_id=link.id,
            unlocked_until=utc_now() + timedelta(seconds=BUSINESS_PIN_UNLOCK_TTL_SECONDS),
        )
        self._audit.write(
            event_type="business_pin_verified",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business_access_link",
            resource_id=link.id,
            request_id=request_id,
        )
        return updated

    def own_payment_methods(self, *, user: UserRecord) -> list[dict[str, Any]]:
        self._rate_limit("payment_methods", user)
        business, _ = require_active_business_access(user=user, business_repository=self._repository)
        methods = [
            method
            for method in self._repository.list_payment_methods_for_business(business.id)
            if method.verified_status == "approved" and method.active
        ]
        return [payment_method_display(method, business=business) for method in methods]

    def _approved_business_for_payment_method_write(self, *, user: UserRecord) -> BusinessRecord:
        business, _ = require_active_business_access(user=user, business_repository=self._repository)
        if business.verification_status != "approved" or business.risk_level in {"restricted", "high_risk"}:
            raise ApiError("BUSINESS_NOT_APPROVED", status_code=409)
        return business

    def _normalize_payment_account(self, *, method_type: str, account_value: str | None) -> str:
        raw_value = account_value or ""
        if method_type == "usdt_trc20":
            normalized = "".join(raw_value.strip().split())
            if len(normalized) != 34 or not normalized.startswith("T") or any(char not in TRON_BASE58_ALPHABET for char in normalized):
                raise ApiError("PAYMENT_METHOD_INVALID", status_code=400)
            return normalized
        normalized = " ".join(raw_value.strip().split())
        if len(normalized) < 3:
            raise ApiError("PAYMENT_METHOD_INVALID", status_code=400)
        return normalized

    def _payment_duplicate_key(self, *, method_type: str, account_value: str) -> str:
        return account_value.casefold() if method_type == "zelle" else account_value

    def _normalize_payment_create_payload(self, payload: BusinessOwnPaymentMethodCreateRequest) -> tuple[str, str, str | None, str]:
        method_type = payload.method_type
        raw_account = payload.account_value or payload.zelle_account
        account_value = self._normalize_payment_account(method_type=method_type, account_value=raw_account)
        holder_name = " ".join(payload.holder_name.strip().split())
        if len(holder_name) < 2:
            raise ApiError("PAYMENT_METHOD_INVALID", status_code=400)
        return method_type, account_value, "TRC20" if method_type == "usdt_trc20" else None, holder_name

    def create_own_payment_method(
        self,
        *,
        user: UserRecord,
        payload: BusinessOwnPaymentMethodCreateRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._rate_limit("payment_methods_write", user)
        require_idempotency_key(idempotency_key)
        self.require_unlocked_business_pin(user=user)
        business = self._approved_business_for_payment_method_write(user=user)
        method_type, account_value, network, holder_name = self._normalize_payment_create_payload(payload)

        def compute() -> dict[str, Any]:
            existing_methods = self._repository.list_payment_methods_for_business(business.id)
            active_methods_for_type = [
                method
                for method in existing_methods
                if method.method_type == method_type and method.verified_status == "approved" and method.active
            ]
            normalized_account = self._payment_duplicate_key(method_type=method_type, account_value=account_value)
            for method in active_methods_for_type:
                if self._payment_duplicate_key(method_type=method.method_type, account_value=method.account_value) == normalized_account:
                    return {"payment_method": payment_method_display(method, business=business), "created": False}
            if len(active_methods_for_type) >= 8:
                raise ApiError("PAYMENT_METHOD_LIMIT_REACHED", status_code=409)
            payment = self._repository.add_payment_method(
                business_id=business.id,
                method_type=method_type,
                network=network,
                account_value=account_value,
                account_masked=mask_account(account_value),
                holder_name=holder_name,
                verified_status="approved",
                active=True,
            )
            self._audit.write(
                event_type="business_payment_method_self_added",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business",
                resource_id=business.id,
                request_id=request_id,
                metadata_json={"payment_method_id": payment.id, "method_type": payment.method_type},
            )
            return {"payment_method": payment_method_display(payment, business=business), "created": True}

        return self._idempotency.replay_or_store(
            f"business_payment_method:create:{business.id}:{idempotency_key}" if idempotency_key else None,
            payload={"business_id": business.id, **payload.model_dump()},
            compute=compute,
        )

    def update_own_payment_method(
        self,
        *,
        user: UserRecord,
        payment_method_id: str,
        payload: BusinessOwnPaymentMethodUpdateRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._rate_limit("payment_methods_write", user)
        require_idempotency_key(idempotency_key)
        self.require_unlocked_business_pin(user=user)
        business = self._approved_business_for_payment_method_write(user=user)
        method = self._repository.get_payment_method(payment_method_id)
        if method is None or method.business_id != business.id or method.method_type not in {"zelle", "usdt_trc20"} or method.verified_status != "approved" or not method.active:
            raise ApiError("PAYMENT_METHOD_NOT_FOUND", status_code=404)
        account_value = method.account_value
        raw_account = payload.account_value if payload.account_value is not None else payload.zelle_account
        if raw_account is not None:
            account_value = self._normalize_payment_account(method_type=method.method_type, account_value=raw_account)
        holder_name = " ".join(payload.holder_name.strip().split())
        if len(holder_name) < 2:
            raise ApiError("PAYMENT_METHOD_INVALID", status_code=400)
        normalized_account = self._payment_duplicate_key(method_type=method.method_type, account_value=account_value)
        for existing in self._repository.list_payment_methods_for_business(business.id):
            if (
                existing.id != method.id
                and existing.method_type == method.method_type
                and existing.active
                and existing.verified_status == "approved"
                and self._payment_duplicate_key(method_type=existing.method_type, account_value=existing.account_value) == normalized_account
            ):
                raise ApiError("PAYMENT_METHOD_DUPLICATE", status_code=409)

        def compute() -> dict[str, Any]:
            updated = self._repository.update_payment_method(
                payment_method_id,
                account_value=account_value,
                account_masked=mask_account(account_value),
                holder_name=holder_name,
            )
            if updated is None:
                raise ApiError("PAYMENT_METHOD_NOT_FOUND", status_code=404)
            self._audit.write(
                event_type="business_payment_method_self_updated",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business",
                resource_id=business.id,
                request_id=request_id,
                metadata_json={"payment_method_id": updated.id, "method_type": updated.method_type},
            )
            self._clear_marketplace_cache_for_business_status_change()
            return {"payment_method": payment_method_display(updated, business=business)}

        return self._idempotency.replay_or_store(
            f"business_payment_method:update:{business.id}:{payment_method_id}:{idempotency_key}" if idempotency_key else None,
            payload={"business_id": business.id, "payment_method_id": payment_method_id, **payload.model_dump()},
            compute=compute,
        )

    def delete_own_payment_method(
        self,
        *,
        user: UserRecord,
        payment_method_id: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._rate_limit("payment_methods_write", user)
        require_idempotency_key(idempotency_key)
        self.require_unlocked_business_pin(user=user)
        business = self._approved_business_for_payment_method_write(user=user)
        method = self._repository.get_payment_method(payment_method_id)
        if method is None or method.business_id != business.id or method.method_type not in {"zelle", "usdt_trc20"}:
            raise ApiError("PAYMENT_METHOD_NOT_FOUND", status_code=404)

        def compute() -> dict[str, Any]:
            latest = self._repository.get_payment_method(payment_method_id)
            if latest is None or latest.business_id != business.id or latest.method_type not in {"zelle", "usdt_trc20"}:
                raise ApiError("PAYMENT_METHOD_NOT_FOUND", status_code=404)
            if not latest.active:
                return {"deleted": True, "payment_method_id": payment_method_id}
            deleted = self._repository.deactivate_payment_method(payment_method_id)
            if deleted is None:
                raise ApiError("PAYMENT_METHOD_NOT_FOUND", status_code=404)
            self._audit.write(
                event_type="business_payment_method_self_deleted",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="business",
                resource_id=business.id,
                request_id=request_id,
                metadata_json={"payment_method_id": deleted.id, "method_type": deleted.method_type},
            )
            self._clear_marketplace_cache_for_business_status_change()
            return {"deleted": True, "payment_method_id": payment_method_id}

        return self._idempotency.replay_or_store(
            f"business_payment_method:delete:{business.id}:{payment_method_id}:{idempotency_key}" if idempotency_key else None,
            payload={"business_id": business.id, "payment_method_id": payment_method_id},
            compute=compute,
        )

