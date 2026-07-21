from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb

from app.modules.businesses.models import FileAssetRecord
from app.modules.support.models import SupportMessageRecord, SupportTicketEventRecord, SupportTicketRecord
from app.modules.support.row_mappers import event_from_row, file_from_row, message_from_row, ticket_from_row
from app.shared.db.connection import pooled_connect


class PostgresSupportRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def create_ticket(self, **fields) -> SupportTicketRecord:  # type: ignore[no-untyped-def]
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into support_tickets (
                    requester_user_id, requester_role, requester_surface, business_id,
                    order_id, ad_id, credit_purchase_id, dispute_id, assigned_support_user_id,
                    scope, category, status, priority, subject, last_message_at,
                    escalated_at, resolved_at, closed_at, created_at, updated_at
                )
                values (
                    %(requester_user_id)s, %(requester_role)s, %(requester_surface)s, %(business_id)s,
                    %(order_id)s, %(ad_id)s, %(credit_purchase_id)s, %(dispute_id)s, %(assigned_support_user_id)s,
                    %(scope)s, %(category)s, %(status)s, %(priority)s, %(subject)s, %(last_message_at)s,
                    %(escalated_at)s, %(resolved_at)s, %(closed_at)s, now(), now()
                )
                returning *
                """,
                fields,
            ).fetchone()
            conn.commit()
        return ticket_from_row(row)

    def get_ticket(self, ticket_id: str) -> SupportTicketRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from support_tickets where id = %s", (ticket_id,)).fetchone()
        return ticket_from_row(row) if row else None

    def list_tickets(
        self,
        *,
        requester_user_id: str | None,
        business_id: str | None,
        status: str | None,
        scope: str | None,
        category: str | None,
        priority: str | None,
        assigned_support_user_id: str | None,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[SupportTicketRecord], str | None]:
        sql = "select * from support_tickets where true"
        params: list[Any] = []
        filters = {
            "requester_user_id": requester_user_id,
            "business_id": business_id,
            "status": status,
            "scope": scope,
            "category": category,
            "priority": priority,
            "assigned_support_user_id": assigned_support_user_id,
        }
        for column, value in filters.items():
            if value:
                sql += f" and {column} = %s"
                params.append(value)
        if cursor:
            sql += " and updated_at < %s"
            params.append(cursor)
        sql += " order by updated_at desc limit %s"
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        items = [ticket_from_row(row) for row in rows]
        return items, items[-1].updated_at.isoformat() if len(items) == limit else None

    def create_message(self, *, ticket_id: str, sender_user_id: str, sender_role: str, body: str, visibility: str) -> SupportMessageRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into support_messages (
                    ticket_id, sender_user_id, sender_role, body, visibility, created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, now(), now())
                returning *
                """,
                (ticket_id, sender_user_id, sender_role, body, visibility),
            ).fetchone()
            conn.execute("update support_tickets set last_message_at = now(), updated_at = now() where id = %s", (ticket_id,))
            conn.commit()
        return message_from_row(row)

    def list_messages(self, *, ticket_id: str) -> list[SupportMessageRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "select * from support_messages where ticket_id = %s and deleted_at is null order by created_at asc",
                (ticket_id,),
            ).fetchall()
        return [message_from_row(row) for row in rows]

    def create_event(
        self,
        *,
        ticket_id: str,
        actor_user_id: str,
        actor_role: str,
        event_type: str,
        from_status: str | None = None,
        to_status: str | None = None,
        reason: str | None = None,
        metadata_json: dict | None = None,
    ) -> SupportTicketEventRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into support_ticket_events (
                    ticket_id, actor_user_id, actor_role, event_type,
                    from_status, to_status, reason, metadata_json, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, %s, now())
                returning *
                """,
                (ticket_id, actor_user_id, actor_role, event_type, from_status, to_status, reason, Jsonb(metadata_json or {})),
            ).fetchone()
            conn.commit()
        return event_from_row(row)

    def list_events(self, *, ticket_id: str) -> list[SupportTicketEventRecord]:
        with self._connect() as conn:
            rows = conn.execute("select * from support_ticket_events where ticket_id = %s order by created_at asc", (ticket_id,)).fetchall()
        return [event_from_row(row) for row in rows]

    def update_ticket(self, ticket: SupportTicketRecord, **fields) -> SupportTicketRecord:  # type: ignore[no-untyped-def]
        assignments = ", ".join(f"{key} = %s" for key in fields)
        params = list(fields.values()) + [ticket.id]
        with self._connect() as conn:
            row = conn.execute(
                f"update support_tickets set {assignments}, updated_at = now() where id = %s returning *",
                params,
            ).fetchone()
            conn.commit()
        return ticket_from_row(row)

    def create_file_asset(
        self,
        *,
        file_id: str,
        owner_user_id: str,
        resource_type: str,
        resource_id: str,
        storage_path: str,
        mime_type: str,
        size_bytes: int,
    ) -> FileAssetRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into file_assets (
                    id, owner_user_id, resource_type, resource_id, file_type,
                    storage_path, mime_type, size_bytes, created_at
                )
                values (%s, %s, %s, %s, 'support_attachment', %s, %s, %s, now())
                returning *
                """,
                (file_id, owner_user_id, resource_type, resource_id, storage_path, mime_type, size_bytes),
            ).fetchone()
            conn.commit()
        return file_from_row(row)

    def get_file_asset(self, file_id: str) -> FileAssetRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from file_assets where id = %s and file_type = 'support_attachment' and deleted_at is null",
                (file_id,),
            ).fetchone()
        return file_from_row(row) if row else None

    def list_files_for_resources(self, *, resources: list[tuple[str, str]]) -> dict[tuple[str, str], list[FileAssetRecord]]:
        result: dict[tuple[str, str], list[FileAssetRecord]] = {resource: [] for resource in resources}
        if not resources:
            return result
        clauses = " or ".join("(resource_type = %s and resource_id = %s)" for _ in resources)
        params: list[Any] = []
        for resource_type, resource_id in resources:
            params.extend([resource_type, resource_id])
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select * from file_assets
                where file_type = 'support_attachment'
                  and deleted_at is null
                  and ({clauses})
                order by created_at asc
                """,
                params,
            ).fetchall()
        for row in rows:
            file = file_from_row(row)
            result.setdefault((file.resource_type, file.resource_id), []).append(file)
        return result
