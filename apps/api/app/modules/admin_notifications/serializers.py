from __future__ import annotations

from typing import Any

from app.modules.admin_notifications.models import AdminNotificationRecord
from app.modules.admin_notifications.redaction import sanitize_admin_notification_metadata


def admin_notification_public(notification: AdminNotificationRecord) -> dict[str, Any]:
    return {
        "id": notification.id,
        "notification_type": notification.notification_type,
        "priority": notification.priority,
        "status": notification.status,
        "source_surface": notification.source_surface,
        "resource_type": notification.resource_type,
        "resource_id": notification.resource_id,
        "business_id": notification.business_id,
        "actor_user_id": notification.actor_user_id,
        "title": notification.title,
        "summary": notification.summary,
        "action_route": notification.action_route,
        "metadata": sanitize_admin_notification_metadata(notification.metadata_json),
        "first_seen_at": notification.first_seen_at.isoformat(),
        "last_seen_at": notification.last_seen_at.isoformat(),
        "read_at": notification.read_at.isoformat() if notification.read_at else None,
        "dismissed_at": notification.dismissed_at.isoformat() if notification.dismissed_at else None,
        "resolved_at": notification.resolved_at.isoformat() if notification.resolved_at else None,
        "created_at": notification.created_at.isoformat(),
        "updated_at": notification.updated_at.isoformat(),
    }
