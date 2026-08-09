from __future__ import annotations

from app.modules.ads.publication_access import business_can_receive_new_orders


class InMemoryBusinessMarketplaceMixin:
    def _has_active_publication_hold(self, business_id: str) -> bool:
        repository = getattr(self, "_publication_hold_repository", None)
        return repository is not None and repository.has_active_publication_hold(business_id)

    def list_marketplace_eligible_business_ids(self) -> set[str]:
        return {
            business.id
            for business in self.businesses.values()  # type: ignore[attr-defined]
            if business_can_receive_new_orders(
                business,
                has_active_operational_hold=self._has_active_publication_hold(business.id),
            )
        }

    def list_marketplace_ineligible_business_ids(self, business_ids: set[str]) -> set[str]:
        return {
            business_id
            for business_id in business_ids
            if (business := self.businesses.get(business_id)) is None  # type: ignore[attr-defined]
            or not business_can_receive_new_orders(
                business,
                has_active_operational_hold=self._has_active_publication_hold(business_id),
            )
        }
