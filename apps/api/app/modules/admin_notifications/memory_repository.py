from __future__ import annotations

from threading import RLock
from typing import Any

from app.modules.admin_notifications.models import AdminNotificationRecord, new_id, utc_now


class InMemoryAdminNotificationRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.notifications: dict[str, AdminNotificationRecord] = {}

    def upsert_notification(self, **fields: Any) -> tuple[AdminNotificationRecord, bool]:
        with self._lock:
            for notification in self.notifications.values():
                if notification.dedupe_key == fields["dedupe_key"]:
                    for key, value in fields.items():
                        if key not in {"dedupe_key", "status"}:
                            setattr(notification, key, value)
                    notification.last_seen_at = utc_now()
                    notification.updated_at = notification.last_seen_at
                    return notification, False
            now = utc_now()
            notification = AdminNotificationRecord(id=new_id(), created_at=now, updated_at=now, first_seen_at=now, last_seen_at=now, **fields)
            self.notifications[notification.id] = notification
            return notification, True

    def get(self, notification_id: str) -> AdminNotificationRecord | None:
        return self.notifications.get(notification_id)

    def list_notifications(
        self,
        *,
        status: str | None,
        priority: str | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[AdminNotificationRecord], str | None]:
        items = list(self.notifications.values())
        if status:
            items = [item for item in items if item.status == status]
        if priority:
            items = [item for item in items if item.priority == priority]
        if cursor:
            items = [item for item in items if item.last_seen_at.isoformat() < cursor]
        items.sort(key=lambda item: item.last_seen_at, reverse=True)
        page = items[:limit]
        return page, page[-1].last_seen_at.isoformat() if len(page) == limit else None

    def unread_count(self) -> int:
        return sum(1 for item in self.notifications.values() if item.status == "unread")

    def update_notification(self, notification: AdminNotificationRecord, **fields: Any) -> AdminNotificationRecord:
        with self._lock:
            for key, value in fields.items():
                setattr(notification, key, value)
            notification.updated_at = utc_now()
            return notification
