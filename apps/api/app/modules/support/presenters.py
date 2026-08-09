from __future__ import annotations

from typing import Any

from app.modules.businesses.models import FileAssetRecord
from app.modules.support.models import (
    BusinessPublicationHoldRecord,
    SupportMessageRecord,
    SupportTicketEventRecord,
    SupportTicketRecord,
)


def file_asset_public(file: FileAssetRecord) -> dict[str, Any]:
    return {
        "id": file.id,
        "resource_type": file.resource_type,
        "resource_id": file.resource_id,
        "file_type": file.file_type,
        "mime_type": file.mime_type,
        "size_bytes": file.size_bytes,
        "created_at": file.created_at.isoformat(),
    }


def ticket_summary(ticket: SupportTicketRecord) -> dict[str, Any]:
    return {
        "id": ticket.id,
        "requester_role": ticket.requester_role,
        "requester_surface": ticket.requester_surface,
        "business_id": ticket.business_id,
        "order_id": ticket.order_id,
        "ad_id": ticket.ad_id,
        "credit_purchase_id": ticket.credit_purchase_id,
        "dispute_id": ticket.dispute_id,
        "assigned_support_user_id": ticket.assigned_support_user_id,
        "scope": ticket.scope,
        "category": ticket.category,
        "status": ticket.status,
        "priority": ticket.priority,
        "subject": ticket.subject,
        "last_message_at": ticket.last_message_at.isoformat() if ticket.last_message_at else None,
        "escalated_at": ticket.escalated_at.isoformat() if ticket.escalated_at else None,
        "resolved_at": ticket.resolved_at.isoformat() if ticket.resolved_at else None,
        "closed_at": ticket.closed_at.isoformat() if ticket.closed_at else None,
        "created_at": ticket.created_at.isoformat(),
        "updated_at": ticket.updated_at.isoformat(),
    }


def message_public(message: SupportMessageRecord, attachments: list[FileAssetRecord] | None = None) -> dict[str, Any]:
    return {
        "id": message.id,
        "ticket_id": message.ticket_id,
        "sender_role": message.sender_role,
        "body": message.body,
        "visibility": message.visibility,
        "attachments": [file_asset_public(file) for file in (attachments or [])],
        "created_at": message.created_at.isoformat(),
    }


def event_public(event: SupportTicketEventRecord) -> dict[str, Any]:
    return {
        "id": event.id,
        "ticket_id": event.ticket_id,
        "actor_role": event.actor_role,
        "event_type": event.event_type,
        "from_status": event.from_status,
        "to_status": event.to_status,
        "reason": event.reason,
        "metadata": event.metadata_json or {},
        "created_at": event.created_at.isoformat(),
    }


def publication_hold_admin(hold: BusinessPublicationHoldRecord) -> dict[str, Any]:
    return {
        "id": hold.id,
        "business_id": hold.business_id,
        "order_id": hold.order_id,
        "support_ticket_id": hold.support_ticket_id,
        "status": hold.status,
        "reason_type": hold.reason_type,
        "created_at": hold.created_at.isoformat(),
        "released_at": hold.released_at.isoformat() if hold.released_at else None,
        "released_by": hold.released_by,
        "release_reason": hold.release_reason,
    }
