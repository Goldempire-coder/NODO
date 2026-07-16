from __future__ import annotations

from decimal import Decimal

from app.core.errors import ApiError
from app.modules.users.models import UserRecord

MARKETPLACE_CACHE_PREFIX = "marketplace:ads:"
MARKETPLACE_ORDER_INVALIDATION_DEBOUNCE_SECONDS = 2


class MarketplaceCacheMixin:
    def _marketplace_cache_key(
        self,
        *,
        amount_usd: Decimal | None,
        payment_method: str | None,
        delivery_method: str | None,
        sort: str | None,
        cursor: str | None,
        limit: int,
    ) -> str:
        amount_text = str(amount_usd) if amount_usd is not None else "any"
        return f"{MARKETPLACE_CACHE_PREFIX}{amount_text}:{payment_method or 'any'}:{delivery_method or 'any'}:{sort or 'default'}:{cursor or 'first'}:{limit}"

    def _clear_marketplace_cache(self) -> None:
        self._marketplace_cache.clear_prefix(MARKETPLACE_CACHE_PREFIX)  # type: ignore[attr-defined]

    def _mark_marketplace_ad_unavailable(self, ad_id: str) -> bool:
        cache = self._marketplace_cache  # type: ignore[attr-defined]
        if not hasattr(cache, "set_marker"):
            return False
        return bool(cache.set_marker(f"ad_unavailable:{ad_id}", self._settings.marketplace_cache_ttl_seconds))  # type: ignore[attr-defined]

    def _marketplace_unavailable_ad_ids(self, ad_ids: list[str]) -> set[str] | None:
        cache = self._marketplace_cache  # type: ignore[attr-defined]
        if not hasattr(cache, "existing_markers"):
            return set()
        return cache.existing_markers([f"ad_unavailable:{ad_id}" for ad_id in ad_ids])  # type: ignore[attr-defined]

    def _clear_marketplace_cache_after_order(self, ad_id: str) -> None:
        marked = self._mark_marketplace_ad_unavailable(ad_id)
        cache = self._marketplace_cache  # type: ignore[attr-defined]
        if marked and hasattr(cache, "clear_prefix_debounced"):
            cache.clear_prefix_debounced(  # type: ignore[attr-defined]
                MARKETPLACE_CACHE_PREFIX,
                debounce_key="order_create",
                debounce_seconds=MARKETPLACE_ORDER_INVALIDATION_DEBOUNCE_SECONDS,
            )
            return
        self._clear_marketplace_cache()

    def _marketplace_search_rate_limit(self, user: UserRecord) -> None:
        key = f"ads:search:{user.id}"
        if not self._marketplace_rate_limiter.allow(  # type: ignore[attr-defined]
            key,
            max_attempts=self._settings.business_rate_limit_max_attempts,  # type: ignore[attr-defined]
            window_seconds=self._settings.business_rate_limit_window_seconds,  # type: ignore[attr-defined]
        ):
            raise ApiError("RATE_LIMITED", status_code=429)
