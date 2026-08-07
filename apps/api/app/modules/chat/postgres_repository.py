from __future__ import annotations

from typing import Any

from app.modules.businesses.models import FileAssetRecord
from app.modules.chat.models import MessageAttachmentRecord, MessageRecord
from app.modules.chat.payment_sharing import (
    OFFICIAL_PAYMENT_DETAILS_IDEMPOTENCY_PREFIX,
    contains_configured_payment_account,
    official_payment_details_idempotency_key,
)
from app.modules.chat.row_mappers import attachment_from_row, file_from_row, message_from_row
from app.shared.db.connection import pooled_connect


class PostgresChatRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def list_messages(self, *, order_id: str, cursor: str | None, limit: int) -> tuple[list[MessageRecord], str | None]:
        sql = "select * from messages where order_id = %s and deleted_at is null"
        params: list[Any] = [order_id]
        if cursor:
            sql += " and created_at < %s"
            params.append(cursor)
        sql += " order by created_at desc, id desc limit %s"
        params.append(limit + 1)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        has_older = len(rows) > limit
        rows = list(reversed(rows[:limit]))
        items = [message_from_row(row) for row in rows]
        return items, items[0].created_at.isoformat() if has_older else None

    def get_message(self, message_id: str) -> MessageRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from messages where id = %s and deleted_at is null", (message_id,)).fetchone()
        return message_from_row(row) if row else None

    def latest_counterparty_messages_for_orders(
        self,
        *,
        order_ids: list[str],
        recipient_user_id: str,
        surface: str,
    ) -> dict[str, MessageRecord]:
        if not order_ids:
            return {}
        allowed_roles = ["remitter"] if surface == "business_mini_app" else ["business_owner"]
        with self._connect() as conn:
            rows = conn.execute(
                """
                select distinct on (order_id) *
                from messages
                where order_id = any(%s)
                  and deleted_at is null
                  and visibility = 'parties'
                  and status = 'visible'
                  and sender_user_id <> %s
                  and sender_role = any(%s)
                order by order_id, created_at desc, id desc
                """,
                (order_ids, recipient_user_id, allowed_roles),
            ).fetchall()
        return {message.order_id: message for message in [message_from_row(row) for row in rows]}

    def list_messages_for_evidence(
        self,
        *,
        order_id: str,
        cursor: str | None,
        direction: str,
        limit: int,
        anchor_created_at=None,  # type: ignore[no-untyped-def]
    ) -> tuple[list[MessageRecord], str | None, str | None]:
        sql = "select * from messages where order_id = %s and deleted_at is null"
        params: list[Any] = [order_id]
        descending = direction != "newer"
        if cursor:
            sql += " and created_at > %s" if direction == "newer" else " and created_at < %s"
            params.append(cursor)
        elif anchor_created_at is not None:
            sql += " and created_at <= %s"
            params.append(anchor_created_at)
        sql += " order by created_at desc" if descending else " order by created_at asc"
        sql += " limit %s"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
            if descending:
                rows = list(reversed(rows))
            if not rows:
                return [], None, None
            bounds = conn.execute(
                """
                select
                    exists(select 1 from messages where order_id = %s and deleted_at is null and created_at < %s) as has_older,
                    exists(select 1 from messages where order_id = %s and deleted_at is null and created_at > %s) as has_newer
                """,
                (order_id, rows[0]["created_at"], order_id, rows[-1]["created_at"]),
            ).fetchone()
        items = [message_from_row(row) for row in rows]
        older_cursor = items[0].created_at.isoformat() if bounds["has_older"] else None
        newer_cursor = items[-1].created_at.isoformat() if bounds["has_newer"] else None
        return items, older_cursor, newer_cursor

    def get_message_by_idempotency_key(self, *, sender_user_id: str, idempotency_key: str) -> MessageRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from messages where sender_user_id = %s and idempotency_key = %s and deleted_at is null limit 1",
                (sender_user_id, idempotency_key),
            ).fetchone()
        return message_from_row(row) if row else None

    def has_official_payment_message(self, *, order_id: str, account_value: str) -> bool:
        if not account_value.strip():
            return False
        with self._connect() as conn:
            rows = conn.execute(
                """
                select body
                from messages
                where order_id = %s
                  and sender_role = 'business_owner'
                  and visibility = 'parties'
                  and status = 'visible'
                  and deleted_at is null
                  and position(%s in coalesce(idempotency_key, '')) = 1
                  and position(lower(%s) in lower(coalesce(body, ''))) > 0
                """,
                (
                    order_id,
                    OFFICIAL_PAYMENT_DETAILS_IDEMPOTENCY_PREFIX,
                    account_value.strip(),
                ),
            ).fetchall()
        return any(
            contains_configured_payment_account(row["body"], account_value)
            for row in rows
        )

    def create_configured_payment_message_once(
        self,
        *,
        order_id: str,
        sender_user_id: str,
        body: str,
        account_value: str,
        idempotency_key: str,
    ) -> tuple[MessageRecord, bool]:
        with self._connect() as conn:
            conn.execute("select id from orders where id = %s for update", (order_id,)).fetchone()
            candidates = conn.execute(
                """
                select *
                from messages
                where order_id = %s
                  and sender_role = 'business_owner'
                  and visibility = 'parties'
                  and status = 'visible'
                  and deleted_at is null
                  and position(%s in coalesce(idempotency_key, '')) = 1
                  and position(lower(%s) in lower(coalesce(body, ''))) > 0
                order by created_at asc
                """,
                (
                    order_id,
                    OFFICIAL_PAYMENT_DETAILS_IDEMPOTENCY_PREFIX,
                    account_value.strip(),
                ),
            ).fetchall()
            existing = next(
                (
                    row
                    for row in candidates
                    if contains_configured_payment_account(
                        row["body"],
                        account_value,
                    )
                ),
                None,
            )
            if existing is not None:
                conn.commit()
                return message_from_row(existing), False
            row = conn.execute(
                """
                insert into messages (
                    order_id, sender_user_id, sender_role, body, visibility, status,
                    idempotency_key, created_at, updated_at
                )
                values (%s, %s, 'business_owner', %s, 'parties', 'visible', %s, now(), now())
                returning *
                """,
                (
                    order_id,
                    sender_user_id,
                    body,
                    official_payment_details_idempotency_key(idempotency_key),
                ),
            ).fetchone()
            conn.commit()
        return message_from_row(row), True

    def create_message(self, *, order_id: str, sender_user_id: str, sender_role: str, body: str | None, idempotency_key: str) -> MessageRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into messages (
                    order_id, sender_user_id, sender_role, body, visibility, status,
                    idempotency_key, created_at, updated_at
                )
                values (%s, %s, %s, %s, 'parties', 'visible', %s, now(), now())
                returning *
                """,
                (order_id, sender_user_id, sender_role, body, idempotency_key),
            ).fetchone()
            conn.commit()
        return message_from_row(row)

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
        with self._connect() as conn:
            file_row = conn.execute(
                """
                insert into file_assets (
                    id, owner_user_id, resource_type, resource_id, file_type,
                    storage_path, mime_type, size_bytes, created_at
                )
                values (%s, %s, 'message', %s, 'message_attachment', %s, %s, %s, now())
                returning *
                """,
                (file_id, owner_user_id, attachment_id, storage_path, mime_type, size_bytes),
            ).fetchone()
            attachment_row = conn.execute(
                """
                insert into message_attachments (
                    id, message_id, order_id, file_asset_id, uploaded_by_user_id,
                    file_type, mime_type, size_bytes, status, created_at, updated_at
                )
                values (%s, null, %s, %s, %s, 'message_attachment', %s, %s, 'active', now(), now())
                returning *
                """,
                (attachment_id, order_id, file_id, owner_user_id, mime_type, size_bytes),
            ).fetchone()
            conn.commit()
        return file_from_row(file_row), attachment_from_row(attachment_row)

    def get_attachment(self, attachment_id: str) -> MessageAttachmentRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from message_attachments where id = %s and deleted_at is null", (attachment_id,)).fetchone()
        return attachment_from_row(row) if row else None

    def get_file_asset(self, file_id: str) -> FileAssetRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select *
                from file_assets
                where id = %s
                  and file_type = 'message_attachment'
                  and deleted_at is null
                """,
                (file_id,),
            ).fetchone()
        return file_from_row(row) if row else None

    def attach_to_message(self, *, attachment_ids: list[str], message_id: str) -> list[MessageAttachmentRecord]:
        if not attachment_ids:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                """
                update message_attachments
                set message_id = %s, updated_at = now()
                where id = any(%s)
                returning *
                """,
                (message_id, attachment_ids),
            ).fetchall()
            conn.execute("update file_assets set resource_id = %s where id = any(%s)", (message_id, [str(row["file_asset_id"]) for row in rows]))
            conn.commit()
        return [attachment_from_row(row) for row in rows]

    def list_attachments_for_messages(self, message_ids: list[str]) -> dict[str, list[MessageAttachmentRecord]]:
        result: dict[str, list[MessageAttachmentRecord]] = {message_id: [] for message_id in message_ids}
        if not message_ids:
            return result
        with self._connect() as conn:
            rows = conn.execute(
                "select * from message_attachments where message_id = any(%s) and deleted_at is null order by created_at asc",
                (message_ids,),
            ).fetchall()
        for row in rows:
            attachment = attachment_from_row(row)
            if attachment.message_id:
                result.setdefault(attachment.message_id, []).append(attachment)
        return result
