from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


ADMIN_NOTIFICATION_PRIORITIES = {"info", "attention", "high", "critical"}
ADMIN_NOTIFICATION_STATUSES = {"unread", "read", "dismissed", "resolved"}
ADMIN_NOTIFICATION_OPEN_STATUSES = {"unread", "read"}


@dataclass
class AdminNotificationRecord:
    id: str
    notification_type: str
    priority: str
    status: str
    source_surface: str | None
    resource_type: str
    resource_id: str | None
    business_id: str | None
    actor_user_id: str | None
    title: str
    summary: str
    action_route: str | None
    dedupe_key: str
    metadata_json: dict = field(default_factory=dict)
    first_seen_at: datetime = field(default_factory=utc_now)
    last_seen_at: datetime = field(default_factory=utc_now)
    read_at: datetime | None = None
    read_by_user_id: str | None = None
    dismissed_at: datetime | None = None
    dismissed_by_user_id: str | None = None
    resolved_at: datetime | None = None
    resolved_by_user_id: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
