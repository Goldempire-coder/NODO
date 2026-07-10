from __future__ import annotations

from typing import Any

from app.core.errors import ApiError
from app.modules.ads.presenters import ad_payload
from app.modules.ads.rules import calculate_required_credits
from app.modules.ads.schemas import AdUpdateRequest
from app.modules.ads.state_machine import require_archive_allowed, require_pause_allowed, require_update_allowed
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
        if new_max > business.max_order_amount_usd:
            raise ApiError("AD_LIMIT_NOT_ALLOWED", status_code=409)
        if calculate_required_credits(new_max) != ad.required_credits:
            raise ApiError("AD_STATUS_INVALID", status_code=409)
        if self._repository.has_overlapping_ad(  # type: ignore[attr-defined]
            business_id=business.id,
            payment_method=ad.payment_method,
            delivery_method=ad.delivery_method,
            amount_min_usd=new_min,
            amount_max_usd=new_max,
            exclude_ad_id=ad.id,
        ):
            raise ApiError("AD_OVERLAP_NOT_ALLOWED", status_code=409)

        def compute() -> dict[str, Any]:
            updated = self._repository.update_ad(  # type: ignore[attr-defined]
                ad,
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
            return {"ad": ad_payload(updated)}

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
            paused = self._repository.set_status(ad, "paused")  # type: ignore[attr-defined]
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
            f"ads:pause:{idempotency_key}" if idempotency_key else None,
            payload={"id": ad_id, "action": "pause", "reason": reason},
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
        require_archive_allowed(ad)

        def compute() -> dict[str, Any]:
            released = self._repository.release_hold(ad=ad, created_by=user.id)  # type: ignore[attr-defined]
            if released is not None:
                self._audit.write(  # type: ignore[attr-defined]
                    event_type="credits_released",
                    actor_user_id=user.id,
                    actor_role=user.role,
                    resource_type="ad",
                    resource_id=ad.id,
                    request_id=request_id,
                    metadata_json={"ledger_id": released.id, "amount": released.amount},
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
            f"ads:archive:{idempotency_key}" if idempotency_key else None,
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
        return {"items": [ad_payload(ad) for ad in visible], "next_cursor": next_cursor}
