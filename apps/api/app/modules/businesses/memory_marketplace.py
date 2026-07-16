from __future__ import annotations


class InMemoryBusinessMarketplaceMixin:
    def list_marketplace_eligible_business_ids(self) -> set[str]:
        return {
            business.id
            for business in self.businesses.values()  # type: ignore[attr-defined]
            if business.verification_status == "approved"
            and business.risk_level not in {"restricted", "high_risk"}
            and business.is_accepting_orders
        }
