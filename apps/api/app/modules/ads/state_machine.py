from __future__ import annotations

from datetime import datetime, timezone

from app.core.errors import ApiError
from app.modules.ads.models import AdRecord


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def is_expired(ad: AdRecord, *, now: datetime | None = None) -> bool:
    current = now or now_utc()
    return ad.status in {"active", "paused"} and ad.expires_at is not None and ad.expires_at <= current


def require_update_allowed(ad: AdRecord) -> None:
    if ad.status not in {"active", "paused"} or is_expired(ad):
        raise ApiError("AD_STATUS_INVALID", status_code=409)


def require_pause_allowed(ad: AdRecord) -> None:
    if ad.status != "active" or is_expired(ad):
        raise ApiError("AD_STATUS_INVALID", status_code=409)


def require_archive_allowed(ad: AdRecord) -> None:
    if ad.status not in {"paused", "expired"}:
        raise ApiError("AD_STATUS_INVALID", status_code=409)
