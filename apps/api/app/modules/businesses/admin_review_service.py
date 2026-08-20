from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.businesses.access_control import business_access_diagnostic
from app.modules.businesses.access_link_rules import admin_reason_or_default, required_admin_reason
from app.modules.businesses.models import TRUST_LEVELS
from app.modules.businesses.policy import require_admin_mutation, require_admin_view
from app.modules.businesses.presenters import business_payload, file_payload, mask_phone, mask_rif
from app.modules.businesses.schemas import AdminBusinessCapacityUpdateRequest
from app.modules.businesses.state_machine import require_admin_review_allowed
from app.modules.users.models import UserRecord


class BusinessAdminReviewServiceMixin:
    def admin_pending(self, *, user: UserRecord, cursor: str | None, limit: int) -> dict[str, Any]:
        require_admin_view(user)
        self._rate_limit("admin_pending", user)  # type: ignore[attr-defined]
        items, next_cursor = self._repository.list_pending_businesses(cursor=cursor, limit=limit)  # type: ignore[attr-defined]
        return {
            "items": [self._admin_pending_item_payload(business) for business in items],
            "next_cursor": next_cursor,
        }

    def _admin_pending_item_payload(self, business) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        latest = self._repository.get_latest_submission(business.id)  # type: ignore[attr-defined]
        return {
            "id": business.id,
            "business_name": business.business_name,
            "rif_masked": mask_rif(business.rif),
            "phone_masked": mask_phone(business.phone),
            "verification_status": business.verification_status,
            "risk_level": business.risk_level,
            "submitted_at": latest.submitted_at.isoformat() if latest else None,
            "created_at": business.created_at.isoformat(),
        }

    def admin_detail(self, *, user: UserRecord, business_id: str) -> dict[str, Any]:
        require_admin_view(user)
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        latest = self._repository.get_latest_submission(business.id)  # type: ignore[attr-defined]
        owner_user = self._users.get_user_by_id(business.owner_user_id)  # type: ignore[attr-defined]
        return {
            "business": business_payload(business, admin=user.role in {"admin", "super_admin"}),
            "access_diagnostic": business_access_diagnostic(
                business=business,
                owner_user=owner_user,
                links=self._repository.list_access_links_for_business(business.id),  # type: ignore[attr-defined]
            ),
            "latest_submission": self._latest_submission_payload(latest=latest, user=user),
            "documents": [file_payload(file) for file in self._repository.list_files_for_business(business.id)],  # type: ignore[attr-defined]
        }

    def _latest_submission_payload(self, *, latest, user: UserRecord) -> dict[str, Any] | None:  # type: ignore[no-untyped-def]
        if latest is None:
            return None
        return {
            "id": latest.id,
            "status": latest.status,
            "submitted_data": latest.submitted_data_json if user.role in {"admin", "super_admin"} else {},
            "submitted_at": latest.submitted_at.isoformat(),
            "reviewed_at": latest.reviewed_at.isoformat() if latest.reviewed_at else None,
        }

    def signed_document_url(
        self,
        *,
        user: UserRecord,
        business_id: str,
        file_id: str,
        reason: str,
        request_id: str,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("view_url", user)  # type: ignore[attr-defined]
        reason = self._admin_reason_or_error(reason)
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        file = self._repository.get_file_for_business(business.id, file_id)  # type: ignore[attr-defined]
        if file is None:
            raise ApiError("BUSINESS_DOCUMENT_NOT_FOUND", status_code=404)
        expires_in = min(self._settings.storage_signed_url_ttl_seconds, 300)  # type: ignore[attr-defined]
        url = self._storage.signed_view_url(storage_path=file.storage_path, expires_in=expires_in)  # type: ignore[attr-defined]
        self._audit.write(  # type: ignore[attr-defined]
            event_type="verification_document_viewed",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business",
            resource_id=business.id,
            request_id=request_id,
            metadata_json={"file_id": file.id, "reason": reason},
        )
        return {"url": url, "expires_in": expires_in}

    def update_business_capacity(
        self,
        *,
        user: UserRecord,
        business_id: str,
        payload: AdminBusinessCapacityUpdateRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("business_capacity", user)  # type: ignore[attr-defined]
        reason = self._admin_reason_or_error(payload.reason)
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]
        if payload.trust_level not in TRUST_LEVELS:
            raise ApiError("BUSINESS_TRUST_LEVEL_INVALID", status_code=400)
        if payload.min_order_amount_usd > payload.max_order_amount_usd:
            raise ApiError("BUSINESS_LIMITS_INVALID", status_code=400)
        if payload.daily_limit_usd < payload.max_order_amount_usd:
            raise ApiError("BUSINESS_LIMITS_INVALID", status_code=400)

        idempotency_payload = {
            "id": business_id,
            "trust_level": payload.trust_level,
            "min_order_amount_usd": payload.min_order_amount_usd,
            "max_order_amount_usd": payload.max_order_amount_usd,
            "daily_limit_usd": payload.daily_limit_usd,
            "active_order_limit": payload.active_order_limit,
            "reason": reason,
        }

        def compute() -> dict[str, Any]:
            return self._compute_business_capacity_update(
                user=user,
                business=business,
                payload=payload,
                reason=reason,
                request_id=request_id,
            )

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"business:capacity:{business_id}:{idempotency_key}" if idempotency_key else None,
            payload=idempotency_payload,
            compute=compute,
        )

    def _compute_business_capacity_update(
        self,
        *,
        user: UserRecord,
        business,
        payload: AdminBusinessCapacityUpdateRequest,
        reason: str,
        request_id: str,
    ) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        before = {
            "trust_level": business.trust_level,
            "min_order_amount_usd": f"{business.min_order_amount_usd:.2f}",
            "max_order_amount_usd": f"{business.max_order_amount_usd:.2f}",
            "daily_limit_usd": f"{business.daily_limit_usd:.2f}",
            "active_order_limit": business.active_order_limit,
        }
        updated = self._repository.update_business_capacity(  # type: ignore[attr-defined]
            business=business,
            trust_level=payload.trust_level,
            min_order_amount_usd=payload.min_order_amount_usd,
            max_order_amount_usd=payload.max_order_amount_usd,
            daily_limit_usd=payload.daily_limit_usd,
            active_order_limit=payload.active_order_limit,
        )
        after = {
            "trust_level": updated.trust_level,
            "min_order_amount_usd": f"{updated.min_order_amount_usd:.2f}",
            "max_order_amount_usd": f"{updated.max_order_amount_usd:.2f}",
            "daily_limit_usd": f"{updated.daily_limit_usd:.2f}",
            "active_order_limit": updated.active_order_limit,
        }
        self._clear_marketplace_cache_for_business_status_change()  # type: ignore[attr-defined]
        self._audit.write(  # type: ignore[attr-defined]
            event_type="business_capacity_updated",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business",
            resource_id=business.id,
            request_id=request_id,
            metadata_json={"reason": reason, "before": before, "after": after},
        )
        return {"business": business_payload(updated, admin=True)}

    def approve(
        self,
        *,
        user: UserRecord,
        business_id: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return self._review_business(
            user=user,
            business_id=business_id,
            reason=reason,
            request_id=request_id,
            idempotency_key=idempotency_key,
            decision="approved",
        )

    def reject(
        self,
        *,
        user: UserRecord,
        business_id: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return self._review_business(
            user=user,
            business_id=business_id,
            reason=reason,
            request_id=request_id,
            idempotency_key=idempotency_key,
            decision="rejected",
        )

    def suspend_business(
        self,
        *,
        user: UserRecord,
        business_id: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return self._change_business_status(
            user=user,
            business_id=business_id,
            action="suspend",
            next_status="suspended",
            allowed_current={"approved"},
            reason=reason,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def reactivate_business(
        self,
        *,
        user: UserRecord,
        business_id: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return self._change_business_status(
            user=user,
            business_id=business_id,
            action="reactivate",
            next_status="approved",
            allowed_current={"suspended", "blocked"},
            reason=reason,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def block_business(
        self,
        *,
        user: UserRecord,
        business_id: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        return self._change_business_status(
            user=user,
            business_id=business_id,
            action="block",
            next_status="blocked",
            allowed_current={"pending", "approved", "rejected", "suspended"},
            reason=reason,
            request_id=request_id,
            idempotency_key=idempotency_key,
        )

    def _review_business(
        self,
        *,
        user: UserRecord,
        business_id: str,
        reason: str,
        request_id: str,
        idempotency_key: str | None,
        decision: str,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit("approve" if decision == "approved" else "reject", user)  # type: ignore[attr-defined]
        reason = self._admin_reason_or_error(reason)
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]

        def compute() -> dict[str, Any]:
            return self._compute_review_business(
                user=user,
                business=business,
                decision=decision,
                reason=reason,
                request_id=request_id,
            )

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            idempotency_key,
            payload={"id": business_id, "decision": decision, "reason": reason},
            compute=compute,
        )

    def _compute_review_business(
        self,
        *,
        user: UserRecord,
        business,
        decision: str,
        reason: str,
        request_id: str,
    ) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        submission = require_admin_review_allowed(
            business,
            self._repository.get_latest_submission(business.id),  # type: ignore[attr-defined]
        )
        if decision == "approved":
            updated = self._repository.approve_business(  # type: ignore[attr-defined]
                business=business,
                submission=submission,
                admin_user_id=user.id,
                reason=reason,
            )
            payload = {
                "id": updated.id,
                "verification_status": updated.verification_status,
                "approved_at": updated.approved_at.isoformat() if updated.approved_at else None,
            }
        else:
            updated = self._repository.reject_business(  # type: ignore[attr-defined]
                business=business,
                submission=submission,
                admin_user_id=user.id,
                reason=reason,
            )
            payload = {"id": updated.id, "verification_status": updated.verification_status}

        self._audit.write(  # type: ignore[attr-defined]
            event_type=f"business_{decision}",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business",
            resource_id=business.id,
            request_id=request_id,
            metadata_json={"reason": reason},
        )
        return {"business": payload}

    def _change_business_status(
        self,
        *,
        user: UserRecord,
        business_id: str,
        action: str,
        next_status: str,
        allowed_current: set[str],
        reason: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        require_admin_mutation(user)
        self._rate_limit(f"business_{action}", user)  # type: ignore[attr-defined]
        reason = required_admin_reason(reason)
        business = self._business_or_404(business_id)  # type: ignore[attr-defined]

        def compute() -> dict[str, Any]:
            return self._compute_business_status_change(
                user=user,
                business=business,
                action=action,
                next_status=next_status,
                allowed_current=allowed_current,
                reason=reason,
                request_id=request_id,
            )

        return self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            idempotency_key,
            payload={"id": business_id, "action": action, "reason": reason},
            compute=compute,
        )

    def _compute_business_status_change(
        self,
        *,
        user: UserRecord,
        business,
        action: str,
        next_status: str,
        allowed_current: set[str],
        reason: str,
        request_id: str,
    ) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        previous_status = business.verification_status
        if previous_status not in allowed_current:
            raise ApiError("BUSINESS_STATUS_INVALID", status_code=409)
        updated = self._repository.set_business_verification_status(business=business, status=next_status)  # type: ignore[attr-defined]
        self._clear_marketplace_cache_for_business_status_change()  # type: ignore[attr-defined]
        event_type = {
            "suspend": "business_suspended",
            "reactivate": "business_reactivated",
            "block": "business_blocked",
        }[action]
        notification_type = {
            "suspend": "business_suspended_owner",
            "reactivate": "business_reactivated_owner",
            "block": "business_blocked_owner",
        }[action]
        self._audit.write(  # type: ignore[attr-defined]
            event_type=event_type,
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="business",
            resource_id=business.id,
            request_id=request_id,
            metadata_json={"reason": reason, "from_status": previous_status, "to_status": next_status},
        )
        self._business_status_notifications.business_status_changed(  # type: ignore[attr-defined]
            business=updated,
            notification_type=notification_type,
            previous_status=previous_status,
            request_id=request_id,
        )
        return {
            "business": {
                "id": updated.id,
                "verification_status": updated.verification_status,
                "approved_at": updated.approved_at.isoformat() if updated.approved_at else None,
            },
            "access_diagnostic": business_access_diagnostic(
                business=updated,
                owner_user=self._users.get_user_by_id(updated.owner_user_id),  # type: ignore[attr-defined]
                links=self._repository.list_access_links_for_business(updated.id),  # type: ignore[attr-defined]
            ),
        }

    def _admin_reason_or_error(self, reason: str) -> str:
        return admin_reason_or_default(reason)
