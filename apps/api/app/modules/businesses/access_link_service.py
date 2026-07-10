from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.access_link_rules import (
    event_type_for_access_link_status,
    require_business_can_receive_access_link,
    require_idempotency_key,
    required_admin_reason,
)
from app.modules.businesses.models import BusinessAccessLinkRecord, BusinessRecord
from app.modules.businesses.policy import require_admin_mutation
from app.modules.businesses.presenters import access_link_payload
from app.modules.businesses.schemas import AdminBusinessAccessLinkCreateRequest
from app.modules.users.models import UserRecord


class BusinessAccessLinkServiceMixin:
    def create_access_link(
        self,
        *,
        user: UserRecord,
        business_id: str,
        payload: AdminBusinessAccessLinkCreateRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        reason = self._validate_access_link_create_request(user=user, payload=payload, idempotency_key=idempotency_key)
        business = self._approved_business_for_access_link(business_id)
        target = self._target_user_for_access_link(payload=payload, business=business)

        def compute() -> dict[str, Any]:
            return self._compute_access_link_create(user=user, business=business, target=target, payload=payload, reason=reason, request_id=request_id)

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"business_access:create:{business_id}:{idempotency_key}",
            payload={"business_id": business_id, **payload.model_dump()},
            compute=compute,
        )

    def _validate_access_link_create_request(self, *, user: UserRecord, payload: AdminBusinessAccessLinkCreateRequest, idempotency_key: str | None) -> str:
        require_admin_mutation(user)
        self._rate_limit("access_link_create", user)  # type: ignore[attr-defined]
        require_idempotency_key(idempotency_key)
        return required_admin_reason(payload.reason)

    def _approved_business_for_access_link(self, business_id: str) -> BusinessRecord:
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        require_business_can_receive_access_link(business)
        return business

    def _target_user_for_access_link(self, *, payload: AdminBusinessAccessLinkCreateRequest, business: BusinessRecord) -> UserRecord:
        target = self._users.get_user_by_id(payload.user_id)  # type: ignore[attr-defined]
        if target is None:
            raise ApiError("USER_NOT_FOUND", status_code=404)
        if target.status == "blocked":
            raise ApiError("USER_BLOCKED", status_code=403)
        if target.status != "active":
            raise ApiError("USER_NOT_ACTIVE", status_code=403)
        if payload.role_in_business == "owner" and target.id != business.owner_user_id:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        if target.role != "business_owner":
            self._users.set_user_role(target.id, "business_owner")  # type: ignore[attr-defined]
            target.role = "business_owner"
        return target

    def _compute_access_link_create(
        self,
        *,
        user: UserRecord,
        business: BusinessRecord,
        target: UserRecord,
        payload: AdminBusinessAccessLinkCreateRequest,
        reason: str,
        request_id: str,
    ) -> dict[str, Any]:
        link = self._repository.create_access_link(  # type: ignore[attr-defined]
            business_id=business.id,
            user_id=target.id,
            telegram_id_snapshot=target.telegram_id,
            role_in_business=payload.role_in_business,
            linked_by_admin_id=user.id,
            reason=reason,
        )
        self._audit_access_link_event(event_type="business_access_linked", user=user, link=link, business=business, target_user_id=target.id, reason=reason, request_id=request_id)
        return {"access_link": access_link_payload(link)}

    def change_access_link_status(
        self,
        *,
        user: UserRecord,
        business_id: str,
        link_id: str,
        status: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        reason = self._validate_access_link_status_request(user=user, status=status, reason=reason, idempotency_key=idempotency_key)
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        link = self._access_link_for_business(link_id=link_id, business=business)

        def compute() -> dict[str, Any]:
            return self._compute_access_link_status_change(user=user, business=business, link=link, status=status, reason=reason, request_id=request_id)

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"business_access:{status}:{link_id}:{idempotency_key}",
            payload={"business_id": business_id, "link_id": link_id, "status": status, "reason": reason},
            compute=compute,
        )

    def _validate_access_link_status_request(self, *, user: UserRecord, status: str, reason: str, idempotency_key: str | None) -> str:
        require_admin_mutation(user)
        self._rate_limit(f"access_link_{status}", user)  # type: ignore[attr-defined]
        require_idempotency_key(idempotency_key)
        return required_admin_reason(reason)

    def _access_link_for_business(self, *, link_id: str, business: BusinessRecord) -> BusinessAccessLinkRecord:
        link = self._repository.get_access_link(link_id)  # type: ignore[attr-defined]
        if link is None or link.business_id != business.id:
            raise ApiError("BUSINESS_ACCESS_LINK_REQUIRED", status_code=404)
        return link

    def _compute_access_link_status_change(
        self,
        *,
        user: UserRecord,
        business: BusinessRecord,
        link: BusinessAccessLinkRecord,
        status: str,
        reason: str,
        request_id: str,
    ) -> dict[str, Any]:
        updated = self._repository.set_access_link_status(link=link, status=status, reason=reason)  # type: ignore[attr-defined]
        event_type = event_type_for_access_link_status(status)
        self._audit_access_link_event(event_type=event_type, user=user, link=updated, business=business, target_user_id=updated.user_id, reason=reason, request_id=request_id)
        return {"access_link": access_link_payload(updated)}

    def _audit_access_link_event(
        self,
        *,
        event_type: str,
        user: UserRecord,
        link: BusinessAccessLinkRecord,
        business: BusinessRecord,
        target_user_id: str,
        reason: str,
        request_id: str,
    ) -> None:
        self._audit.write(  # type: ignore[attr-defined]
            event_type=event_type,
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business_access_link",
            resource_id=link.id,
            request_id=request_id,
            metadata_json={"business_id": business.id, "target_user_id": target_user_id, "reason": reason},
        )
