from __future__ import annotations

from threading import RLock

from app.modules.businesses.models import FileAssetRecord
from app.modules.support.models import SupportMessageRecord, SupportTicketEventRecord, SupportTicketRecord, new_id, utc_now


class InMemorySupportRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.tickets: dict[str, SupportTicketRecord] = {}
        self.messages: dict[str, SupportMessageRecord] = {}
        self.events: dict[str, SupportTicketEventRecord] = {}
        self.files: dict[str, FileAssetRecord] = {}

    def create_ticket(self, **fields) -> SupportTicketRecord:  # type: ignore[no-untyped-def]
        with self._lock:
            now = utc_now()
            ticket = SupportTicketRecord(id=new_id(), created_at=now, updated_at=now, **fields)
            self.tickets[ticket.id] = ticket
            return ticket

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
    ) -> tuple[list[SupportTicketRecord], str | None]:
        items = list(self.tickets.values())
        if requester_user_id:
            items = [item for item in items if item.requester_user_id == requester_user_id]
        if business_id:
            items = [item for item in items if item.business_id == business_id]
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
        items.sort(key=lambda item: item.updated_at, reverse=True)
        if cursor:
            items = [item for item in items if item.updated_at.isoformat() < cursor]
        page = items[:limit]
        return page, page[-1].updated_at.isoformat() if len(page) == limit else None

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

    def list_messages(self, *, ticket_id: str) -> list[SupportMessageRecord]:
        items = [message for message in self.messages.values() if message.ticket_id == ticket_id and message.deleted_at is None]
        items.sort(key=lambda message: message.created_at)
        return items

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

    def list_events(self, *, ticket_id: str) -> list[SupportTicketEventRecord]:
        items = [event for event in self.events.values() if event.ticket_id == ticket_id]
        items.sort(key=lambda event: event.created_at)
        return items

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
