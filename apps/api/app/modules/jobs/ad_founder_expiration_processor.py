from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from app.modules.jobs.models import JOB_TYPE_EXPIRE_AND_ESCALATE
from app.modules.jobs.worker_support import JobCounters


class AdFounderExpirationProcessor:
    def __init__(
        self,
        *,
        ad_repository: Any,
        business_repository: Any,
        audit_writer: Any,
        notify: Callable[..., bool],
    ) -> None:
        self._ads = ad_repository
        self._businesses = business_repository
        self._audit = audit_writer
        self._notify = notify

    def process_ads(self, *, now: datetime, batch_size: int, dry_run: bool, request_id: str, counters: JobCounters) -> None:
        for ad in self._ads.list_expirable_ads(limit=batch_size):
            counters.processed += 1
            if dry_run:
                counters.changed += 1
                continue
            ledger = self._ads.expire_hold(ad=ad, created_by=None, reason="ad_expired_without_purchase", source="jobs")
            self._audit.write(
                event_type="ad_expired",
                actor_user_id=None,
                actor_role=None,
                resource_type="ad",
                resource_id=ad.id,
                request_id=request_id,
                metadata_json={"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE},
            )
            if ledger is not None:
                self._audit.write(
                    event_type="credits_consumed",
                    actor_user_id=None,
                    actor_role=None,
                    resource_type="ad",
                    resource_id=ad.id,
                    request_id=request_id,
                    metadata_json={"job_type": JOB_TYPE_EXPIRE_AND_ESCALATE, "ledger_id": ledger.id, "amount": ledger.amount},
                )
            business = self._businesses.get_business(ad.business_id)
            if business is not None:
                self._notify(
                    notification_type="ad_expired",
                    dedupe_key=f"ad:{ad.id}:expired:business",
                    scheduled_for=now,
                    recipient_user_id=business.owner_user_id,
                    business_id=ad.business_id,
                )
            counters.changed += 1
