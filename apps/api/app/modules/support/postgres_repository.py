from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb
from psycopg.errors import UniqueViolation

from app.core.errors import ApiError
from app.modules.businesses.models import FileAssetRecord
from app.modules.support.models import (
    BusinessPublicationHoldRecord,
    SupportMessageRecord,
    SupportTicketEventRecord,
    SupportTicketRecord,
)
from app.modules.support.row_mappers import (
    event_from_row,
    file_from_row,
    message_from_row,
    publication_hold_from_row,
    ticket_from_row,
)
from app.shared.db.connection import pooled_connect


class PostgresSupportRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def create_ticket(self, **fields) -> SupportTicketRecord:  # type: ignore[no-untyped-def]
        fields.setdefault("report_kind", None)
        try:
            with self._connect() as conn:
                row = self._insert_ticket(conn, fields)
                conn.commit()
        except UniqueViolation as exc:
            if exc.diag.constraint_name == "support_tickets_active_operation_report_order_uidx":
                raise ApiError("OPERATION_REPORT_DUPLICATE", status_code=409) from exc
            raise
        return ticket_from_row(row)

    def _insert_ticket(self, conn, fields: dict):  # type: ignore[no-untyped-def]
        return conn.execute(
            """
            insert into support_tickets (
                requester_user_id, requester_role, requester_surface, business_id,
                order_id, ad_id, credit_purchase_id, dispute_id, assigned_support_user_id,
                scope, category, status, priority, subject, report_kind, last_message_at,
                escalated_at, resolved_at, closed_at, created_at, updated_at
            )
            values (
                %(requester_user_id)s, %(requester_role)s, %(requester_surface)s, %(business_id)s,
                %(order_id)s, %(ad_id)s, %(credit_purchase_id)s, %(dispute_id)s, %(assigned_support_user_id)s,
                %(scope)s, %(category)s, %(status)s, %(priority)s, %(subject)s, %(report_kind)s, %(last_message_at)s,
                %(escalated_at)s, %(resolved_at)s, %(closed_at)s, now(), now()
            )
            returning *
            """,
            fields,
        ).fetchone()

    def create_operation_report(
        self,
        *,
        ticket_fields: dict,
        message_body: str,
        event_metadata: dict,
        publication_paused_until=None,
    ) -> tuple[SupportTicketRecord, BusinessPublicationHoldRecord | None]:
        try:
            with self._connect() as conn:
                pause = conn.execute(
                    """
                    select ad_publication_paused_until, now() as database_now
                    from businesses
                    where id = %s
                    for update
                    """,
                    (ticket_fields["business_id"],),
                ).fetchone()
                if pause is None:
                    raise ApiError("BUSINESS_NOT_FOUND", status_code=404)
                row = self._insert_ticket(conn, ticket_fields)
                conn.execute(
                    """
                    insert into support_messages (
                        ticket_id, sender_user_id, sender_role, body, visibility,
                        created_at, updated_at
                    )
                    values (%s, %s, %s, %s, 'participants', now(), now())
                    """,
                    (
                        row["id"],
                        ticket_fields["requester_user_id"],
                        ticket_fields["requester_role"],
                        message_body,
                    ),
                )
                conn.execute(
                    """
                    insert into support_ticket_events (
                        ticket_id, actor_user_id, actor_role, event_type,
                        to_status, metadata_json, created_at
                    )
                    values (%s, %s, %s, 'support_ticket_created', 'open', %s, now())
                    """,
                    (
                        row["id"],
                        ticket_fields["requester_user_id"],
                        ticket_fields["requester_role"],
                        Jsonb(event_metadata),
                    ),
                )
                row = conn.execute(
                    """
                    update support_tickets
                    set last_message_at = now(), updated_at = now()
                    where id = %s
                    returning *
                    """,
                    (row["id"],),
                ).fetchone()
                hold_row = None
                if (
                    pause["ad_publication_paused_until"] is not None
                    and pause["database_now"] < pause["ad_publication_paused_until"]
                ):
                    hold_row = conn.execute(
                        """
                        insert into business_publication_holds (
                            business_id, order_id, support_ticket_id,
                            status, reason_type, created_at
                        )
                        values (%s, %s, %s, 'active', 'structured_operation_report', now())
                        returning *
                        """,
                        (
                            ticket_fields["business_id"],
                            ticket_fields["order_id"],
                            row["id"],
                        ),
                    ).fetchone()
                conn.commit()
        except UniqueViolation as exc:
            if exc.diag.constraint_name in {
                "support_tickets_active_operation_report_order_uidx",
                "business_publication_holds_active_order_uidx",
                "business_publication_holds_support_ticket_id_key",
            }:
                raise ApiError("OPERATION_REPORT_DUPLICATE", status_code=409) from exc
            raise
        return (
            ticket_from_row(row),
            publication_hold_from_row(hold_row) if hold_row else None,
        )

    def get_publication_hold(self, hold_id: str) -> BusinessPublicationHoldRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from business_publication_holds where id = %s",
                (hold_id,),
            ).fetchone()
        return publication_hold_from_row(row) if row else None

    def get_publication_hold_for_ticket(
        self,
        support_ticket_id: str,
    ) -> BusinessPublicationHoldRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "select * from business_publication_holds where support_ticket_id = %s",
                (support_ticket_id,),
            ).fetchone()
        return publication_hold_from_row(row) if row else None

    def get_active_publication_hold_for_order(
        self,
        order_id: str,
    ) -> BusinessPublicationHoldRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select * from business_publication_holds
                where order_id = %s and status = 'active'
                limit 1
                """,
                (order_id,),
            ).fetchone()
        return publication_hold_from_row(row) if row else None

    def has_active_publication_hold(self, business_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """
                select exists(
                    select 1 from business_publication_holds
                    where business_id = %s and status = 'active'
                ) as active
                """,
                (business_id,),
            ).fetchone()
        return bool(row["active"])

    def active_publication_hold_business_ids(self, business_ids: set[str]) -> set[str]:
        if not business_ids:
            return set()
        with self._connect() as conn:
            rows = conn.execute(
                """
                select distinct business_id
                from business_publication_holds
                where business_id = any(%s::uuid[]) and status = 'active'
                """,
                (list(business_ids),),
            ).fetchall()
        return {str(row["business_id"]) for row in rows}

    def release_publication_hold(
        self,
        *,
        hold_id: str,
        released_by: str,
        release_reason: str,
    ) -> BusinessPublicationHoldRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                update business_publication_holds
                set status = 'released',
                    released_at = now(),
                    released_by = %s,
                    release_reason = %s
                where id = %s and status = 'active'
                returning *
                """,
                (released_by, release_reason, hold_id),
            ).fetchone()
            if row is None:
                existing = conn.execute(
                    "select status from business_publication_holds where id = %s",
                    (hold_id,),
                ).fetchone()
                conn.rollback()
                if existing is None:
                    raise ApiError("BUSINESS_PUBLICATION_HOLD_NOT_FOUND", status_code=404)
                raise ApiError("BUSINESS_PUBLICATION_HOLD_ALREADY_RELEASED", status_code=409)
            conn.commit()
        return publication_hold_from_row(row)

    def get_active_operation_report_for_order(self, order_id: str | None) -> SupportTicketRecord | None:
        if order_id is None:
            return None
        with self._connect() as conn:
            row = conn.execute(
                """
                select * from support_tickets
                where order_id = %s
                  and report_kind = 'structured_operation_report'
                  and status in ('open', 'waiting_support', 'waiting_user', 'escalated')
                limit 1
                """,
                (order_id,),
            ).fetchone()
        return ticket_from_row(row) if row else None

    def get_ticket(self, ticket_id: str) -> SupportTicketRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from support_tickets where id = %s", (ticket_id,)).fetchone()
        return ticket_from_row(row) if row else None

    def list_tickets(
        self,
        *,
        requester_user_id: str | None,
        business_id: str | None,
        statuses: set[str] | None,
        scope: str | None,
        category: str | None,
        priority: str | None,
        assigned_support_user_id: str | None,
        cursor: str | None,
        limit: int,
        requester_surface: str | None = None,
    ) -> tuple[list[SupportTicketRecord], str | None]:
        sql = "select * from support_tickets where true"
        params: list[Any] = []
        filters = {
            "requester_user_id": requester_user_id,
            "business_id": business_id,
            "requester_surface": requester_surface,
            "scope": scope,
            "category": category,
            "priority": priority,
            "assigned_support_user_id": assigned_support_user_id,
        }
        for column, value in filters.items():
            if value:
                sql += f" and {column} = %s"
                params.append(value)
        if statuses:
            sql += " and status = any(%s)"
            params.append(sorted(statuses))
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

    def latest_participant_messages_for_tickets(
        self,
        *,
        ticket_ids: list[str],
        recipient_user_id: str,
    ) -> dict[str, SupportMessageRecord]:
        if not ticket_ids:
            return {}
        with self._connect() as conn:
            rows = conn.execute(
                """
                select distinct on (ticket_id) *
                from support_messages
                where ticket_id = any(%s)
                  and deleted_at is null
                  and visibility = 'participants'
                  and sender_user_id <> %s
                order by ticket_id, created_at desc, id desc
                """,
                (ticket_ids, recipient_user_id),
            ).fetchall()
        return {message.ticket_id: message for message in [message_from_row(row) for row in rows]}

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
