from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.ads.audit_events import ad_creation_audit_events
from app.modules.ads.presenters import ad_payload
from app.modules.ads.rules import calculate_required_credits
from app.modules.ads.schemas import AdCreateRequest, AdUpdateRequest
from app.modules.ads.policy import require_publishable_business
from app.modules.ads.state_machine import require_archive_allowed, require_pause_allowed, require_reactivate_allowed, require_update_allowed
from app.modules.users.models import UserRecord


class AdManagementMixin:
    def update_ad(
        self,
        *,
        user: UserRecord,
        ad_id: str,
        payload: AdUpdateRequest,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        self._rate_limit("update", user)  # type: ignore[attr-defined]
        business = self._owner_business(user)  # type: ignore[attr-defined]
        ad = self._materialize_expired(self._ad_or_404(ad_id), actor=user, request_id=request_id)  # type: ignore[attr-defined]
        if ad.business_id != business.id:
            raise ApiError("FORBIDDEN", status_code=403)
        require_update_allowed(ad)
        new_min = payload.amount_min_usd if payload.amount_min_usd is not None else ad.amount_min_usd
        new_max = payload.amount_max_usd if payload.amount_max_usd is not None else ad.amount_max_usd
        if new_min > new_max:
            raise ApiError("AD_AMOUNT_RANGE_INVALID", status_code=400)
        if new_min < business.min_order_amount_usd:
            raise ApiError("AD_LIMIT_NOT_ALLOWED", status_code=409)
        if new_max > business.max_order_amount_usd:
            raise ApiError("AD_LIMIT_NOT_ALLOWED", status_code=409)
        if calculate_required_credits(new_max) != ad.required_credits:
            raise ApiError("AD_STATUS_INVALID", status_code=409)
        payment_method = None
        if payload.payment_method_id is not None:
            payment_method = self._payment_or_invalid(business, payload.payment_method_id, ad.payment_method)  # type: ignore[attr-defined]

        def compute() -> dict[str, Any]:
            updated = self._repository.update_ad(  # type: ignore[attr-defined]
                ad,
                payment_method_id=payload.payment_method_id,
                rate_bs_per_usd=payload.rate_bs_per_usd,
                amount_min_usd=payload.amount_min_usd,
                amount_max_usd=payload.amount_max_usd,
            )
            self._audit.write(  # type: ignore[attr-defined]
                event_type="ad_updated",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="ad",
                resource_id=updated.id,
                request_id=request_id,
            )
            return {"ad": ad_payload(updated, payment_method=payment_method)}

        response = self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"ads:update:{idempotency_key}" if idempotency_key else None,
            payload={"id": ad_id, **payload.model_dump()},
            compute=compute,
        )
        self._clear_marketplace_cache()  # type: ignore[attr-defined]
        return response

    def pause_ad(self, *, user: UserRecord, ad_id: str, reason: str | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._rate_limit("pause", user)  # type: ignore[attr-defined]
        business = self._owner_business(user)  # type: ignore[attr-defined]
        ad = self._materialize_expired(self._ad_or_404(ad_id), actor=user, request_id=request_id)  # type: ignore[attr-defined]
        if ad.business_id != business.id:
            raise ApiError("FORBIDDEN", status_code=403)
        require_pause_allowed(ad)

        def compute() -> dict[str, Any]:
            paused = self._repository.set_status(  # type: ignore[attr-defined]
                ad, "paused", expected_status="active"
            )
            self._audit.write(  # type: ignore[attr-defined]
                event_type="ad_paused",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="ad",
                resource_id=paused.id,
                request_id=request_id,
                metadata_json={"reason": reason.strip()} if reason and reason.strip() else None,
            )
            return {"ad": ad_payload(paused)}

        response = self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"ads:pause:{business.id}:{idempotency_key}" if idempotency_key else None,
            payload={"id": ad_id, "action": "pause", "reason": reason},
            compute=compute,
        )
        self._clear_marketplace_cache()  # type: ignore[attr-defined]
        return response

    def reactivate_ad(self, *, user: UserRecord, ad_id: str, reason: str | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._rate_limit("reactivate", user)  # type: ignore[attr-defined]
        business = self._owner_business(user)  # type: ignore[attr-defined]
        require_publishable_business(business)
        ad = self._materialize_expired(self._ad_or_404(ad_id), actor=user, request_id=request_id)  # type: ignore[attr-defined]
        if ad.business_id != business.id:
            raise ApiError("FORBIDDEN", status_code=403)
        require_reactivate_allowed(ad)
        if ad.amount_min_usd < business.min_order_amount_usd or ad.amount_max_usd > business.max_order_amount_usd:
            raise ApiError("AD_LIMIT_NOT_ALLOWED", status_code=409)
        self._payment_or_invalid(business, ad.payment_method_id, ad.payment_method)  # type: ignore[attr-defined]
        def compute() -> dict[str, Any]:
            reactivated = self._repository.set_status(  # type: ignore[attr-defined]
                ad,
                "active",
                enforce_publication_access=True,
            )
            self._audit.write(  # type: ignore[attr-defined]
                event_type="ad_reactivated",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="ad",
                resource_id=reactivated.id,
                request_id=request_id,
                metadata_json={"reason": reason.strip()} if reason and reason.strip() else None,
            )
            return {"ad": ad_payload(reactivated)}

        response = self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            (
                f"ads:reactivate:{business.id}:{idempotency_key}"
                if idempotency_key
                else None
            ),
            payload={"id": ad_id, "action": "reactivate", "reason": reason},
            compute=compute,
        )
        self._clear_marketplace_cache()  # type: ignore[attr-defined]
        return response

    def republish_ad(self, *, user: UserRecord, ad_id: str, reason: str | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._rate_limit("republish", user)  # type: ignore[attr-defined]
        business = self._owner_business(user)  # type: ignore[attr-defined]
        require_publishable_business(business)
        source_ad = self._materialize_expired(self._ad_or_404(ad_id), actor=user, request_id=request_id)  # type: ignore[attr-defined]
        if source_ad.business_id != business.id:
            raise ApiError("FORBIDDEN", status_code=403)
        if source_ad.status not in {"archived", "expired"}:
            raise ApiError("AD_STATUS_INVALID", status_code=409)
        payload = AdCreateRequest(
            business_id=business.id,
            payment_method_id=source_ad.payment_method_id,
            payment_method=source_ad.payment_method,
            delivery_method=source_ad.delivery_method,
            rate_bs_per_usd=source_ad.rate_bs_per_usd,
            amount_min_usd=source_ad.amount_min_usd,
            amount_max_usd=source_ad.amount_max_usd,
        )
        required_credits = self._validate_ad_create_rules(business=business, payload=payload)  # type: ignore[attr-defined]
        self._payment_or_invalid(business, payload.payment_method_id, payload.payment_method)  # type: ignore[attr-defined]
        def compute() -> dict[str, Any]:
            republished = self._publish_ad(  # type: ignore[attr-defined]
                user=user,
                business=business,
                payload=payload,
                required_credits=required_credits,
            )
            events = ad_creation_audit_events(
                user=user,
                ad=republished,
                request_id=request_id,
            )
            events.append(
                {
                    "event_type": "ad_republished",
                    "actor_user_id": user.id,
                    "actor_role": user.role,
                    "resource_type": "ad",
                    "resource_id": republished.id,
                    "request_id": request_id,
                    "metadata_json": {
                        "source_ad_id": source_ad.id,
                        "reason": reason.strip() if reason and reason.strip() else None,
                    },
                }
            )
            self._write_audit_events(events)  # type: ignore[attr-defined]
            return {
                "ad": ad_payload(republished),
                "republished_from_ad_id": source_ad.id,
                "credit_hold": {"ledger_id": republished.credit_hold_ledger_id, "required_credits": republished.required_credits},
            }

        response = self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"ads:republish:{idempotency_key}" if idempotency_key else None,
            payload={"id": ad_id, "action": "republish", "reason": reason},
            compute=compute,
        )
        self._clear_marketplace_cache()  # type: ignore[attr-defined]
        return response

    def archive_ad(self, *, user: UserRecord, ad_id: str, reason: str | None, request_id: str, idempotency_key: str | None) -> dict[str, Any]:
        self._rate_limit("archive", user)  # type: ignore[attr-defined]
        business = self._owner_business(user)  # type: ignore[attr-defined]
        ad = self._materialize_expired(self._ad_or_404(ad_id), actor=user, request_id=request_id)  # type: ignore[attr-defined]
        if ad.business_id != business.id:
            raise ApiError("FORBIDDEN", status_code=403)
        if ad.status == "archived":
            return {"ad": ad_payload(ad)}
        require_archive_allowed(ad)

        def compute() -> dict[str, Any]:
            consumed = self._repository.expire_hold(ad=ad, created_by=user.id, reason="ad_archived_by_business", source="ads")  # type: ignore[attr-defined]
            if consumed is not None:
                self._audit.write(  # type: ignore[attr-defined]
                    event_type="credits_consumed",
                    actor_user_id=user.id,
                    actor_role=user.role,
                    resource_type="ad",
                    resource_id=ad.id,
                    request_id=request_id,
                    metadata_json={"ledger_id": consumed.id, "amount": consumed.amount, "reason": "ad_archived_by_business"},
                )
            archived = self._repository.set_status(ad, "archived")  # type: ignore[attr-defined]
            self._audit.write(  # type: ignore[attr-defined]
                event_type="ad_archived",
                actor_user_id=user.id,
                actor_role=user.role,
                resource_type="ad",
                resource_id=archived.id,
                request_id=request_id,
                metadata_json={"reason": reason.strip()} if reason and reason.strip() else None,
            )
            return {"ad": ad_payload(archived)}

        response = self._idempotency.replay_or_store(  # type: ignore[attr-defined]
            f"ads:archive:{business.id}:{idempotency_key}" if idempotency_key else None,
            payload={"id": ad_id, "action": "archive", "reason": reason},
            compute=compute,
        )
        self._clear_marketplace_cache()  # type: ignore[attr-defined]
        return response

    def my_ads(self, *, user: UserRecord, archived: bool, cursor: str | None, limit: int, request_id: str) -> dict[str, Any]:
        self._rate_limit("list_archived" if archived else "list", user)  # type: ignore[attr-defined]
        business = self._owner_business(user)  # type: ignore[attr-defined]
        items, next_cursor = self._repository.list_business_ads(  # type: ignore[attr-defined]
            business_id=business.id,
            archived=archived,
            cursor=cursor,
            limit=limit,
        )
        materialized = [self._materialize_expired(ad, actor=user, request_id=request_id) for ad in items]  # type: ignore[attr-defined]
        visible = [
            ad
            for ad in materialized
            if (ad.status in {"archived", "expired"} if archived else ad.status in {"active", "paused", "in_order", "suspended"})
        ]
        return {
            "items": [
                ad_payload(ad, payment_method=self._businesses.get_payment_method(ad.payment_method_id))  # type: ignore[attr-defined]
                for ad in visible
            ],
            "next_cursor": next_cursor,
        }
