from __future__ import annotations

from app.modules.businesses.models import FileAssetRecord
from app.modules.chat.models import MessageAttachmentRecord, MessageRecord


def message_from_row(row) -> MessageRecord:  # type: ignore[no-untyped-def]
    return MessageRecord(
        id=str(row["id"]),
        order_id=str(row["order_id"]),
        sender_user_id=str(row["sender_user_id"]),
        sender_role=row["sender_role"],
        body=row["body"],
        visibility=row["visibility"],
        status=row["status"],
        idempotency_key=row["idempotency_key"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
    )


def attachment_from_row(row) -> MessageAttachmentRecord:  # type: ignore[no-untyped-def]
    return MessageAttachmentRecord(
        id=str(row["id"]),
        message_id=str(row["message_id"]) if row["message_id"] else None,
        order_id=str(row["order_id"]),
        file_asset_id=str(row["file_asset_id"]),
        uploaded_by_user_id=str(row["uploaded_by_user_id"]),
        file_type=row["file_type"],
        mime_type=row["mime_type"],
        size_bytes=row["size_bytes"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        deleted_at=row["deleted_at"],
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
