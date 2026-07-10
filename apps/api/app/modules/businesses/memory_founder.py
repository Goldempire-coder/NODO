from __future__ import annotations

from app.modules.businesses.models import BusinessRecord, utc_now


class InMemoryBusinessFounderMixin:
    def list_expired_founder_businesses(self, *, limit: int) -> list[BusinessRecord]:
        now = utc_now()
        items = [
            business
            for business in self.businesses.values()  # type: ignore[attr-defined]
            if business.founder_status == "active"
            and business.founder_expires_at is not None
            and business.founder_expires_at <= now
        ]
        items.sort(key=lambda business: business.founder_expires_at or business.created_at)
        return items[:limit]

    def expire_founder_access(self, business: BusinessRecord) -> BusinessRecord:
        with self._lock:  # type: ignore[attr-defined]
            business.founder_status = "expired"
            business.updated_at = utc_now()
            return business
