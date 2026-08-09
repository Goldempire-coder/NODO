from __future__ import annotations

from app.modules.businesses.models import FileAssetRecord
from app.modules.support.models import (
    BusinessPublicationHoldRecord,
    SupportMessageRecord,
    SupportTicketEventRecord,
    SupportTicketRecord,
)


def ticket_from_row(row) -> SupportTicketRecord:  # type: ignore[no-untyped-def]
    return SupportTicketRecord(
        id=str(row["id"]),
        requester_user_id=str(row["requester_user_id"]),
        requester_role=row["requester_role"],
        requester_surface=row["requester_surface"],
        business_id=str(row["business_id"]) if row["business_id"] else None,
        order_id=str(row["order_id"]) if row["order_id"] else None,
        ad_id=str(row["ad_id"]) if row["ad_id"] else None,
        credit_purchase_id=str(row["credit_purchase_id"]) if row["credit_purchase_id"] else None,
        dispute_id=str(row["dispute_id"]) if row["dispute_id"] else None,
        assigned_support_user_id=str(row["assigned_support_user_id"]) if row["assigned_support_user_id"] else None,
        scope=row["scope"],
        category=row["category"],
        status=row["status"],
        priority=row["priority"],
        subject=row["subject"],
        report_kind=row.get("report_kind"),
        last_message_at=row["last_message_at"],
        escalated_at=row["escalated_at"],
        resolved_at=row["resolved_at"],
        closed_at=row["closed_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def publication_hold_from_row(row) -> BusinessPublicationHoldRecord:  # type: ignore[no-untyped-def]
    return BusinessPublicationHoldRecord(
        id=str(row["id"]),
        business_id=str(row["business_id"]),
        order_id=str(row["order_id"]),
        support_ticket_id=str(row["support_ticket_id"]),
        status=row["status"],
        reason_type=row["reason_type"],
        created_at=row["created_at"],
        released_at=row["released_at"],
        released_by=str(row["released_by"]) if row["released_by"] else None,
        release_reason=row["release_reason"],
    )


def message_from_row(row) -> SupportMessageRecord:  # type: ignore[no-untyped-def]
    return SupportMessageRecord(
        id=str(row["id"]),
        ticket_id=str(row["ticket_id"]),
        sender_user_id=str(row["sender_user_id"]),
        sender_role=row["sender_role"],
        body=row["body"],
        visibility=row["visibility"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def event_from_row(row) -> SupportTicketEventRecord:  # type: ignore[no-untyped-def]
    return SupportTicketEventRecord(
        id=str(row["id"]),
        ticket_id=str(row["ticket_id"]),
        actor_user_id=str(row["actor_user_id"]),
        actor_role=row["actor_role"],
        event_type=row["event_type"],
        from_status=row["from_status"],
        to_status=row["to_status"],
        reason=row["reason"],
        metadata_json=row["metadata_json"] or {},
        created_at=row["created_at"],
    )


def file_from_row(row) -> FileAssetRecord:  # type: ignore[no-untyped-def]
    return FileAssetRecord(
        id=str(row["id"]),
        owner_user_id=str(row["owner_user_id"]),
        resource_type=row["resource_type"],
        resource_id=str(row["resource_id"]),
        file_type=row["file_type"],
        storage_path=row["storage_path"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        created_at=row["created_at"],
        deleted_at=row["deleted_at"],
    )
