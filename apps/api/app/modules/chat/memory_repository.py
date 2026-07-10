from __future__ import annotations

from threading import RLock

from app.modules.businesses.models import FileAssetRecord
from app.modules.chat.models import MessageAttachmentRecord, MessageRecord, new_id, utc_now


class InMemoryChatRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.messages: dict[str, MessageRecord] = {}
        self.attachments: dict[str, MessageAttachmentRecord] = {}
        self.files: dict[str, FileAssetRecord] = {}

    def list_messages(self, *, order_id: str, cursor: str | None, limit: int) -> tuple[list[MessageRecord], str | None]:
        items = [message for message in self.messages.values() if message.order_id == order_id and message.deleted_at is None]
        items.sort(key=lambda message: message.created_at)
        if cursor:
            items = [message for message in items if message.created_at.isoformat() > cursor]
        page = items[:limit]
        next_cursor = page[-1].created_at.isoformat() if len(page) == limit else None
        return page, next_cursor

    def get_message_by_idempotency_key(self, *, sender_user_id: str, idempotency_key: str) -> MessageRecord | None:
        for message in self.messages.values():
            if message.sender_user_id == sender_user_id and message.idempotency_key == idempotency_key:
                return message
        return None

    def create_message(self, *, order_id: str, sender_user_id: str, sender_role: str, body: str | None, idempotency_key: str) -> MessageRecord:
        with self._lock:
            now = utc_now()
            message = MessageRecord(
                id=new_id(),
                order_id=order_id,
                sender_user_id=sender_user_id,
                sender_role=sender_role,
                body=body,
                idempotency_key=idempotency_key,
                created_at=now,
                updated_at=now,
            )
            self.messages[message.id] = message
            return message

    def create_attachment_file(
        self,
        *,
        file_id: str,
        attachment_id: str,
        owner_user_id: str,
        order_id: str,
        storage_path: str,
        mime_type: str,
        size_bytes: int,
    ) -> tuple[FileAssetRecord, MessageAttachmentRecord]:
        with self._lock:
            now = utc_now()
            file = FileAssetRecord(
                id=file_id,
                owner_user_id=owner_user_id,
                resource_type="message",
                resource_id=attachment_id,
                file_type="message_attachment",
                storage_path=storage_path,
                mime_type=mime_type,
                size_bytes=size_bytes,
                created_at=now,
            )
            attachment = MessageAttachmentRecord(
                id=attachment_id,
                message_id=None,
                order_id=order_id,
                file_asset_id=file_id,
                uploaded_by_user_id=owner_user_id,
                file_type="message_attachment",
                mime_type=mime_type,
                size_bytes=size_bytes,
                created_at=now,
                updated_at=now,
            )
            self.files[file.id] = file
            self.attachments[attachment.id] = attachment
            return file, attachment

    def get_attachment(self, attachment_id: str) -> MessageAttachmentRecord | None:
        attachment = self.attachments.get(attachment_id)
        if attachment is None or attachment.deleted_at is not None:
            return None
        return attachment

    def attach_to_message(self, *, attachment_ids: list[str], message_id: str) -> list[MessageAttachmentRecord]:
        attached: list[MessageAttachmentRecord] = []
        with self._lock:
            for attachment_id in attachment_ids:
                attachment = self.attachments[attachment_id]
                attachment.message_id = message_id
                attachment.updated_at = utc_now()
                file = self.files[attachment.file_asset_id]
                file.resource_id = message_id
                attached.append(attachment)
        return attached

    def list_attachments_for_messages(self, message_ids: list[str]) -> dict[str, list[MessageAttachmentRecord]]:
        result: dict[str, list[MessageAttachmentRecord]] = {message_id: [] for message_id in message_ids}
        for attachment in self.attachments.values():
            if attachment.message_id in result and attachment.deleted_at is None:
                result[attachment.message_id].append(attachment)
        return result
