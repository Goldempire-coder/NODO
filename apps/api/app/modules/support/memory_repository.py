from __future__ import annotations

from datetime import datetime
from threading import RLock

from app.modules.businesses.models import FileAssetRecord
from app.modules.support.models import (
    BusinessPublicationHoldRecord,
    SupportMessageRecord,
    SupportTicketEventRecord,
    SupportTicketRecord,
    new_id,
    utc_now,
)
from app.modules.support.models import ACTIVE_SUPPORT_STATUSES, STRUCTURED_OPERATION_REPORT
from app.core.errors import ApiError
from app.shared.keyset_pagination import decode_keyset_cursor, encode_keyset_cursor, paginate_descending


class InMemorySupportRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.tickets: dict[str, SupportTicketRecord] = {}
        self.messages: dict[str, SupportMessageRecord] = {}
        self.events: dict[str, SupportTicketEventRecord] = {}
        self.files: dict[str, FileAssetRecord] = {}
        self.publication_holds: dict[str, BusinessPublicationHoldRecord] = {}

    def create_ticket(self, **fields) -> SupportTicketRecord:  # type: ignore[no-untyped-def]
        with self._lock:
            if fields.get("report_kind") == STRUCTURED_OPERATION_REPORT:
                existing = self.get_active_operation_report_for_order(fields.get("order_id"))
                if existing is not None:
                    raise ApiError("OPERATION_REPORT_DUPLICATE", status_code=409)
            now = utc_now()
            ticket = SupportTicketRecord(id=new_id(), created_at=now, updated_at=now, **fields)
            self.tickets[ticket.id] = ticket
            return ticket

    def get_active_operation_report_for_order(self, order_id: str | None) -> SupportTicketRecord | None:
        if order_id is None:
            return None
        return next(
            (
                ticket
                for ticket in self.tickets.values()
                if ticket.order_id == order_id
                and ticket.report_kind == STRUCTURED_OPERATION_REPORT
                and ticket.status in ACTIVE_SUPPORT_STATUSES
            ),
            None,
        )

    def create_operation_report(
        self,
        *,
        ticket_fields: dict,
        message_body: str,
        event_metadata: dict,
        publication_paused_until: datetime | None,
    ) -> tuple[SupportTicketRecord, BusinessPublicationHoldRecord | None]:
        with self._lock:
            ticket = self.create_ticket(**ticket_fields)
            self.create_message(
                ticket_id=ticket.id,
                sender_user_id=ticket.requester_user_id,
                sender_role=ticket.requester_role,
                body=message_body,
                visibility="participants",
            )
            self.create_event(
                ticket_id=ticket.id,
                actor_user_id=ticket.requester_user_id,
                actor_role=ticket.requester_role,
                event_type="support_ticket_created",
                to_status="open",
                metadata_json=event_metadata,
            )
            hold = None
            now = utc_now()
            if publication_paused_until is not None and now < publication_paused_until:
                if self.get_active_publication_hold_for_order(ticket.order_id) is not None:
                    raise ApiError("OPERATION_REPORT_DUPLICATE", status_code=409)
                hold = BusinessPublicationHoldRecord(
                    id=new_id(),
                    business_id=ticket.business_id,
                    order_id=ticket.order_id,
                    support_ticket_id=ticket.id,
                    created_at=now,
                )
                self.publication_holds[hold.id] = hold
            return ticket, hold

    def get_publication_hold(self, hold_id: str) -> BusinessPublicationHoldRecord | None:
        return self.publication_holds.get(hold_id)

    def get_publication_hold_for_ticket(
        self,
        support_ticket_id: str,
    ) -> BusinessPublicationHoldRecord | None:
        return next(
            (
                hold
                for hold in self.publication_holds.values()
                if hold.support_ticket_id == support_ticket_id
            ),
            None,
        )

    def get_active_publication_hold_for_order(
        self,
        order_id: str,
    ) -> BusinessPublicationHoldRecord | None:
        return next(
            (
                hold
                for hold in self.publication_holds.values()
                if hold.order_id == order_id and hold.status == "active"
            ),
            None,
        )

    def has_active_publication_hold(self, business_id: str) -> bool:
        return any(
            hold.business_id == business_id and hold.status == "active"
            for hold in self.publication_holds.values()
        )

    def active_publication_hold_business_ids(self, business_ids: set[str]) -> set[str]:
        return {
            hold.business_id
            for hold in self.publication_holds.values()
            if hold.status == "active" and hold.business_id in business_ids
        }

    def release_publication_hold(
        self,
        *,
        hold_id: str,
        released_by: str,
        release_reason: str,
    ) -> BusinessPublicationHoldRecord:
        with self._lock:
            hold = self.publication_holds.get(hold_id)
            if hold is None:
                raise ApiError("BUSINESS_PUBLICATION_HOLD_NOT_FOUND", status_code=404)
            if hold.status != "active":
                raise ApiError("BUSINESS_PUBLICATION_HOLD_ALREADY_RELEASED", status_code=409)
            hold.status = "released"
            hold.released_at = utc_now()
            hold.released_by = released_by
            hold.release_reason = release_reason
            return hold

    def get_ticket(self, ticket_id: str) -> SupportTicketRecord | None:
        return self.tickets.get(ticket_id)

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
        items = list(self.tickets.values())
        if requester_user_id:
            items = [item for item in items if item.requester_user_id == requester_user_id]
        if business_id:
            items = [item for item in items if item.business_id == business_id]
        if requester_surface:
            items = [item for item in items if item.requester_surface == requester_surface]
        if statuses:
            items = [item for item in items if item.status in statuses]
        if scope:
            items = [item for item in items if item.scope == scope]
        if category:
            items = [item for item in items if item.category == category]
        if priority:
            items = [item for item in items if item.priority == priority]
        if assigned_support_user_id:
            items = [item for item in items if item.assigned_support_user_id == assigned_support_user_id]
        return paginate_descending(
            items,
            timestamp_of=lambda item: item.updated_at,
            id_of=lambda item: item.id,
            cursor=cursor,
            limit=limit,
        )

    def create_message(self, *, ticket_id: str, sender_user_id: str, sender_role: str, body: str, visibility: str) -> SupportMessageRecord:
        with self._lock:
            now = utc_now()
            message = SupportMessageRecord(
                id=new_id(),
                ticket_id=ticket_id,
                sender_user_id=sender_user_id,
                sender_role=sender_role,
                body=body,
                visibility=visibility,
                created_at=now,
                updated_at=now,
            )
            self.messages[message.id] = message
            ticket = self.tickets[ticket_id]
            ticket.last_message_at = now
            ticket.updated_at = now
            return message

    def list_messages_page(
        self,
        *,
        ticket_id: str,
        cursor: str | None,
        limit: int,
        include_internal: bool,
        viewer_user_id: str | None,
    ) -> tuple[list[SupportMessageRecord], str | None]:
        items = [
            message
            for message in self.messages.values()
            if message.ticket_id == ticket_id
            and message.deleted_at is None
            and (
                include_internal
                or message.visibility == "participants"
                or message.sender_user_id == viewer_user_id
            )
        ]
        items.sort(key=lambda message: (message.created_at, message.id), reverse=True)
        if cursor:
            position = decode_keyset_cursor(cursor)
            items = [
                message
                for message in items
                if (message.created_at, message.id) < (position.timestamp, position.item_id)
            ]
        page = items[:limit]
        next_cursor = encode_keyset_cursor(page[-1].created_at, page[-1].id) if len(items) > limit else None
        page.reverse()
        return page, next_cursor

    def latest_participant_messages_for_tickets(
        self,
        *,
        ticket_ids: list[str],
        recipient_user_id: str,
    ) -> dict[str, SupportMessageRecord]:
        if not ticket_ids:
            return {}
        ticket_id_set = set(ticket_ids)
        result: dict[str, SupportMessageRecord] = {}
        for message in self.messages.values():
            if (
                message.ticket_id not in ticket_id_set
                or message.deleted_at is not None
                or message.visibility != "participants"
                or message.sender_user_id == recipient_user_id
            ):
                continue
            current = result.get(message.ticket_id)
            if current is None or (message.created_at, message.id) > (current.created_at, current.id):
                result[message.ticket_id] = message
        return result

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
        with self._lock:
            event = SupportTicketEventRecord(
                id=new_id(),
                ticket_id=ticket_id,
                actor_user_id=actor_user_id,
                actor_role=actor_role,
                event_type=event_type,
                from_status=from_status,
                to_status=to_status,
                reason=reason,
                metadata_json=metadata_json or {},
                created_at=utc_now(),
            )
            self.events[event.id] = event
            return event

    def list_events_page(
        self,
        *,
        ticket_id: str,
        cursor: str | None,
        limit: int,
    ) -> tuple[list[SupportTicketEventRecord], str | None]:
        items = [event for event in self.events.values() if event.ticket_id == ticket_id]
        items.sort(key=lambda event: (event.created_at, event.id), reverse=True)
        if cursor:
            position = decode_keyset_cursor(cursor)
            items = [
                event
                for event in items
                if (event.created_at, event.id) < (position.timestamp, position.item_id)
            ]
        page = items[:limit]
        next_cursor = encode_keyset_cursor(page[-1].created_at, page[-1].id) if len(items) > limit else None
        page.reverse()
        return page, next_cursor

    def update_ticket(self, ticket: SupportTicketRecord, **fields) -> SupportTicketRecord:  # type: ignore[no-untyped-def]
        with self._lock:
            for key, value in fields.items():
                setattr(ticket, key, value)
            ticket.updated_at = utc_now()
            return ticket

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
        with self._lock:
            file = FileAssetRecord(
                id=file_id,
                owner_user_id=owner_user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                file_type="support_attachment",
                storage_path=storage_path,
                mime_type=mime_type,
                size_bytes=size_bytes,
                created_at=utc_now(),
            )
            self.files[file.id] = file
            return file

    def get_file_asset(self, file_id: str) -> FileAssetRecord | None:
        file = self.files.get(file_id)
        if file is None or file.deleted_at is not None:
            return None
        return file

    def get_ticket_file_asset(self, *, ticket_id: str, file_id: str) -> FileAssetRecord | None:
        file = self.get_file_asset(file_id)
        if file is None or file.file_type != "support_attachment":
            return None
        if file.resource_type == "support_ticket":
            return file if file.resource_id == ticket_id else None
        if file.resource_type != "support_message":
            return None
        message = self.messages.get(file.resource_id)
        if message is None or message.deleted_at is not None or message.ticket_id != ticket_id:
            return None
        return file

    def list_files_for_resources(self, *, resources: list[tuple[str, str]]) -> dict[tuple[str, str], list[FileAssetRecord]]:
        result: dict[tuple[str, str], list[FileAssetRecord]] = {resource: [] for resource in resources}
        allowed = set(resources)
        for file in self.files.values():
            key = (file.resource_type, file.resource_id)
            if key in allowed and file.deleted_at is None:
                result.setdefault(key, []).append(file)
        for files in result.values():
            files.sort(key=lambda file: file.created_at)
        return result
