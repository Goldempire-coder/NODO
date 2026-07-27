from __future__ import annotations

import time
from decimal import Decimal
from typing import Any

from app.core.errors import ApiError
from app.modules.ads.marketplace_cache import MarketplaceCacheMixin
from app.modules.ads.models import AdRecord
from app.modules.ads.presenters import ad_payload
from app.modules.ads.policy import require_marketplace_user
from app.modules.businesses.models import BusinessRecord
from app.modules.users.models import UserRecord
from app.shared.profiling import activate_profile, profile_attach, profile_mark, reset_profile


class AdMarketplaceMixin(MarketplaceCacheMixin):
    def search(
        self,
        *,
        user: UserRecord,
        amount_usd: Decimal | None,
        payment_method: str | None,
        delivery_method: str | None,
        sort: str | None,
        cursor: str | None,
        limit: int,
        profile_enabled: bool = False,
    ) -> dict[str, Any]:
        profile = [] if profile_enabled else None
        token = activate_profile(profile)
        profile_started = time.perf_counter()
        try:
            stage_started = time.perf_counter()
            require_marketplace_user(user)
            profile_mark(profile, "service:marketplace_access", stage_started)
            stage_started = time.perf_counter()
            self._marketplace_search_rate_limit(user)
            profile_mark(profile, "service:rate_limit", stage_started)
            stage_started = time.perf_counter()
            self._validate_search_params(payment_method=payment_method, delivery_method=delivery_method, sort=sort)
            profile_mark(profile, "service:validate_search_params", stage_started)
            stage_started = time.perf_counter()
            cache_key = self._marketplace_cache_key(
                amount_usd=amount_usd,
                payment_method=payment_method,
                delivery_method=delivery_method,
                sort=sort,
                cursor=cursor,
                limit=limit,
            )
            profile_mark(profile, "cache:key_build", stage_started)
            cached = self._marketplace_cache.get_json(cache_key)  # type: ignore[attr-defined]
            if cached is not None:
                filtered = self._marketplace_cached_response(cached, profile=profile)
                if filtered is not None:
                    return profile_attach(filtered, profile, profile_started)
            with self._marketplace_cache.lock(cache_key):  # type: ignore[attr-defined]
                cached = self._marketplace_cache.get_json(cache_key)  # type: ignore[attr-defined]
                if cached is not None:
                    filtered = self._marketplace_cached_response(cached, profile=profile)
                    if filtered is not None:
                        return profile_attach(filtered, profile, profile_started)
                items, next_cursor, businesses_by_id = self._query_marketplace_ads(
                    amount_usd=amount_usd,
                    payment_method=payment_method,
                    delivery_method=delivery_method,
                    cursor=cursor,
                    limit=limit,
                    profile=profile,
                )
                response = self._marketplace_search_response(
                    items=items,
                    next_cursor=next_cursor,
                    sort=sort,
                    profile=profile,
                    amount_usd=amount_usd,
                    businesses_by_id=businesses_by_id,
                )
                self._marketplace_cache.set_json(cache_key, response, self._settings.marketplace_cache_ttl_seconds)  # type: ignore[attr-defined]
                return profile_attach(response, profile, profile_started)
        finally:
            reset_profile(token)

    def _marketplace_cached_response(self, cached: dict[str, Any], *, profile: list[dict[str, Any]] | None) -> dict[str, Any] | None:
        response = dict(cached)
        items = response.get("items")
        if not isinstance(items, list):
            return response
        ad_ids = [str(item.get("id")) for item in items if isinstance(item, dict) and item.get("id")]
        started = time.perf_counter()
        unavailable = self._marketplace_unavailable_ad_ids(ad_ids)
        profile_mark(profile, "cache:marketplace_unavailable_filter", started, {"checked": len(ad_ids)})
        if unavailable is None:
            profile_mark(profile, "cache:marketplace_cached_response_bypass", time.perf_counter())
            return None
        if not unavailable:
            return response
        unavailable_ad_ids = {marker.removeprefix("ad_unavailable:") for marker in unavailable}
        response["items"] = [
            item
            for item in items
            if not isinstance(item, dict) or str(item.get("id")) not in unavailable_ad_ids
        ]
        profile_mark(
            profile,
            "cache:marketplace_unavailable_filtered",
            time.perf_counter(),
            {"filtered": len(items) - len(response["items"])},
        )
        return response

    def _validate_search_params(self, *, payment_method: str | None, delivery_method: str | None, sort: str | None) -> None:
        if delivery_method not in {None, "pago_movil_ve"}:
            raise ApiError("INVALID_DELIVERY_METHOD", status_code=400)
        if payment_method not in {None, "zelle", "usdt_trc20"}:
            raise ApiError("INVALID_PAYMENT_METHOD", status_code=400)
        if sort not in {None, "trust", "rate", "speed"}:
            raise ApiError("AD_AMOUNT_RANGE_INVALID", status_code=400)

    def _query_marketplace_ads(
        self,
        *,
        amount_usd: Decimal | None,
        payment_method: str | None,
        delivery_method: str | None,
        cursor: str | None,
        limit: int,
        profile: list[dict[str, Any]] | None,
    ) -> tuple[list[AdRecord], str | None, dict[str, BusinessRecord] | None]:
        optimized_marketplace_search = getattr(self._repository, "list_marketplace_ads_with_businesses", None)  # type: ignore[attr-defined]
        if optimized_marketplace_search is not None:
            stage_started = time.perf_counter()
            rows, next_cursor = optimized_marketplace_search(
                amount_usd=amount_usd,
                payment_method=payment_method,
                delivery_method=delivery_method,
                cursor=cursor,
                limit=limit,
            )
            profile_mark(profile, "repo:list_marketplace_ads_with_businesses", stage_started)
            items = [ad for ad, _business in rows]
            businesses_by_id = {business.id: business for _ad, business in rows}
            return items, next_cursor, businesses_by_id

        optimized_ads_search = getattr(self._repository, "list_marketplace_ads_for_marketplace", None)  # type: ignore[attr-defined]
        if optimized_ads_search is not None:
            stage_started = time.perf_counter()
            items, next_cursor = optimized_ads_search(
                amount_usd=amount_usd,
                payment_method=payment_method,
                delivery_method=delivery_method,
                cursor=cursor,
                limit=limit,
            )
            profile_mark(profile, "repo:list_marketplace_ads_for_marketplace", stage_started)
            return items, next_cursor, None

        stage_started = time.perf_counter()
        eligible_ids = self._businesses.list_marketplace_eligible_business_ids()  # type: ignore[attr-defined]
        businesses = self._businesses.get_businesses_by_ids(eligible_ids)  # type: ignore[attr-defined]
        eligible_ids = {
            business_id
            for business_id, business in businesses.items()
            if self._capacity.can_cover(  # type: ignore[attr-defined]
                business=business,
                amount_usd=amount_usd or business.min_order_amount_usd,
            )
        }
        profile_mark(profile, "repo:list_marketplace_eligible_business_ids", stage_started)
        stage_started = time.perf_counter()
        items, next_cursor = self._repository.list_marketplace_ads(  # type: ignore[attr-defined]
            amount_usd=amount_usd,
            payment_method=payment_method,
            delivery_method=delivery_method,
            eligible_business_ids=eligible_ids,
            cursor=cursor,
            limit=limit,
        )
        profile_mark(profile, "repo:list_marketplace_ads", stage_started)
        return items, next_cursor, None

    def _marketplace_search_response(
        self,
        *,
        items: list[AdRecord],
        next_cursor: str | None,
        sort: str | None,
        profile: list[dict[str, Any]] | None,
        amount_usd: Decimal | None,
        businesses_by_id: dict[str, BusinessRecord] | None = None,
    ) -> dict[str, Any]:
        if businesses_by_id is None:
            stage_started = time.perf_counter()
            businesses_by_id = self._businesses.get_businesses_by_ids({ad.business_id for ad in items})  # type: ignore[attr-defined]
            profile_mark(profile, "repo:get_businesses_by_ids", stage_started)
        stage_started = time.perf_counter()
        eligible_items = [
            ad
            for ad in items
            if self._ad_within_current_business_limits(ad=ad, business=businesses_by_id.get(ad.business_id))
            and self._ad_has_available_payment_method(ad)
        ]
        ranked = self._rank(eligible_items, sort=sort, businesses_by_id=businesses_by_id)
        profile_mark(profile, "service:rank", stage_started)
        stage_started = time.perf_counter()
        response = {
            "items": [
                ad_payload(
                    ad,
                    business=businesses_by_id.get(ad.business_id),
                    can_cover_requested_amount=True if amount_usd is not None else None,
                )
                for ad in ranked
            ],
            "next_cursor": next_cursor,
            "disclaimer": "Negocios verificados por NODO. Compara tasa, limites y disponibilidad antes de elegir.",
        }
        profile_mark(profile, "service:payload", stage_started)
        return response

    def detail(self, *, user: UserRecord, ad_id: str, request_id: str) -> dict[str, Any]:
        require_marketplace_user(user)
        self._rate_limit("detail", user)
        ad = self._materialize_expired(self._ad_or_404(ad_id), actor=user, request_id=request_id)
        business = self._businesses.get_business(ad.business_id)  # type: ignore[attr-defined]
        payment = self._businesses.get_payment_method(ad.payment_method_id)  # type: ignore[attr-defined]
        if (
            ad.status != "active"
            or business is None
            or business.verification_status != "approved"
            or business.risk_level in {"restricted", "high_risk"}
            or not business.is_accepting_orders
            or payment is None
            or payment.business_id != ad.business_id
            or payment.verified_status != "approved"
            or not payment.active
            or not self._ad_within_current_business_limits(ad=ad, business=business)
            or not self._capacity.can_cover(  # type: ignore[attr-defined]
                business=business,
                amount_usd=ad.amount_min_usd,
            )
        ):
            raise ApiError("AD_NOT_AVAILABLE", status_code=404)
        return {
            "ad": ad_payload(
                ad,
                business=business,
                payment_method=payment,
                can_cover_requested_amount=True,
            ),
            "disclaimer": "Revisa monto, tasa y negocio antes de crear la orden. NODO organiza el proceso y guarda el respaldo de la operacion.",
        }

    def _rank(self, items: list[AdRecord], *, sort: str | None, businesses_by_id: dict[str, BusinessRecord]) -> list[AdRecord]:
        if sort == "rate":
            return sorted(items, key=lambda ad: (ad.rate_bs_per_usd, ad.created_at), reverse=True)
        if sort in {"trust", "speed"}:
            return sorted(
                items,
                key=lambda ad: (
                    businesses_by_id[ad.business_id].trust_level if ad.business_id in businesses_by_id else "new",
                    businesses_by_id[ad.business_id].completed_orders_count if ad.business_id in businesses_by_id else 0,
                    ad.rate_bs_per_usd,
                ),
                reverse=True,
            )
        return items

    def _ad_within_current_business_limits(self, *, ad: AdRecord, business: BusinessRecord | None) -> bool:
        if business is None:
            return False
        if not business.is_accepting_orders:
            return False
        return ad.amount_min_usd >= business.min_order_amount_usd and ad.amount_max_usd <= business.max_order_amount_usd

    def _ad_has_available_payment_method(self, ad: AdRecord) -> bool:
        payment = self._businesses.get_payment_method(ad.payment_method_id)  # type: ignore[attr-defined]
        return (
            payment is not None
            and payment.business_id == ad.business_id
            and payment.verified_status == "approved"
            and payment.active
        )
