from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from app.modules.admin.user_presenters import mask_telegram_id
from app.modules.support.models import ARCHIVED_SUPPORT_STATUSES
from app.shared.db.connection import pooled_connect


ALLOWED_ORDER_EVENTS = {
    "payment_reported",
    "payment_confirmed",
    "payment_rejected",
    "order_delivered",
    "order_completed",
    "order_cancelled",
    "order_cancelled_by_remitter",
    "order_cancelled_by_timeout",
    "order_expired",
    "dispute_opened",
    "admin_order_resolved",
}
ALLOWED_SUPPORT_EVENTS = {
    "support_ticket_resolved",
    "support_ticket_closed",
}
TABLE_COLUMNS = {
    "users": "id, telegram_id, username, first_name, role, status, created_at, updated_at",
    "businesses": "id, owner_user_id, business_name, verification_status, created_at, updated_at",
    "business_intake_requests": (
        "id, telegram_user_id, status, referral_code, business_name, city, submitted_at, reviewed_at, "
        "created_business_id, linked_telegram_user_id, created_at, updated_at"
    ),
    "orders": (
        "id, public_order_code, business_id, remitter_user_id, status, amount_usd, "
        "created_at, updated_at"
    ),
    "support_tickets": (
        "id, requester_user_id, requester_role, scope, category, status, priority, "
        "business_id, order_id, assigned_support_user_id, created_at, updated_at"
    ),
}


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _record_value(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def _sort_key(record: Any, field: str) -> tuple[datetime, str]:
    return (_record_value(record, field), str(_record_value(record, "id")))


def _page(
    records: Iterable[Any],
    *,
    field: str,
    position: dict[str, str] | None,
    limit: int,
) -> tuple[list[Any], dict[str, str] | None, int]:
    items = sorted(records, key=lambda item: _sort_key(item, field), reverse=True)
    total_count = len(items)
    if position:
        position_key = (datetime.fromisoformat(position["at"]), position["id"])
        items = [item for item in items if _sort_key(item, field) < position_key]
    page = items[: limit + 1]
    truncated = len(page) > limit
    page = page[:limit]
    next_position = None
    if truncated and page:
        next_position = {"at": _record_value(page[-1], field).isoformat(), "id": str(_record_value(page[-1], "id"))}
    return page, next_position, total_count


def _order_payload(order: Any) -> dict[str, Any]:
    return {
        "id": _record_value(order, "id"),
        "public_order_code": _record_value(order, "public_order_code"),
        "status": _record_value(order, "status"),
        "business_id": _record_value(order, "business_id"),
        "remitter_user_id": _record_value(order, "remitter_user_id"),
        "amount_usd": str(_record_value(order, "amount_usd")),
        "created_at": _iso(_record_value(order, "created_at")),
        "updated_at": _iso(_record_value(order, "updated_at")),
        "action_route": f"admin://order/{_record_value(order, 'id')}",
    }


def _ticket_payload(ticket: Any) -> dict[str, Any]:
    return {
        "id": _record_value(ticket, "id"),
        "status": _record_value(ticket, "status"),
        "scope": _record_value(ticket, "scope"),
        "category": _record_value(ticket, "category"),
        "priority": _record_value(ticket, "priority"),
        "requester_user_id": _record_value(ticket, "requester_user_id"),
        "business_id": _record_value(ticket, "business_id"),
        "order_id": _record_value(ticket, "order_id"),
        "created_at": _iso(_record_value(ticket, "created_at")),
        "updated_at": _iso(_record_value(ticket, "updated_at")),
        "action_route": f"admin://support-ticket/{_record_value(ticket, 'id')}",
    }


def _intake_payload(intake: Any) -> dict[str, Any]:
    return {
        "id": _record_value(intake, "id"),
        "status": _record_value(intake, "status"),
        "referral_code": _record_value(intake, "referral_code"),
        "business_name": _record_value(intake, "business_name"),
        "city": _record_value(intake, "city"),
        "created_business_id": _record_value(intake, "created_business_id"),
        "created_at": _iso(_record_value(intake, "created_at")),
        "submitted_at": _iso(_record_value(intake, "submitted_at")),
        "reviewed_at": _iso(_record_value(intake, "reviewed_at")),
        "action_route": f"admin://business-intake/{_record_value(intake, 'id')}",
    }


def _timeline_payload(
    *,
    event_id: str,
    event_type: str,
    label: str,
    entity_type: str,
    entity_id: str,
    created_at: datetime,
    action_route: str,
    from_status: str | None = None,
    to_status: str | None = None,
) -> dict[str, Any]:
    return {
        "id": event_id,
        "event_type": event_type,
        "label": label,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "from_status": from_status,
        "to_status": to_status,
        "created_at": created_at.isoformat(),
        "action_route": action_route,
    }


class InMemoryAdminInvestigationCaseFileRepository:
    def __init__(self, *, users, businesses, business_intake, orders, support, chat) -> None:  # type: ignore[no-untyped-def]
        self._users = users
        self._businesses = businesses
        self._business_intake = business_intake
        self._orders = orders
        self._support = support
        self._chat = chat

    def resolve_context(self, *, anchor_type: str, anchor_id: str) -> dict[str, Any] | None:
        users = getattr(self._users, "_users_by_id", {})
        businesses = getattr(self._businesses, "businesses", {})
        intakes = getattr(self._business_intake, "intakes", {})
        orders = getattr(self._orders, "orders", {})
        tickets = getattr(self._support, "tickets", {})
        anchor_collections = {
            "user": users,
            "business": businesses,
            "business_intake": intakes,
            "order": orders,
            "support_ticket": tickets,
        }
        anchor = anchor_collections[anchor_type].get(anchor_id)
        if anchor is None:
            return None

        related_users: set[str] = set()
        related_businesses: set[str] = set()
        related_orders: set[str] = set()
        related_tickets: set[str] = set()
        related_intakes: set[str] = set()

        def include_order(order: Any) -> None:
            related_orders.add(order.id)
            related_businesses.add(order.business_id)
            related_users.add(order.remitter_user_id)

        def include_ticket(ticket: Any) -> None:
            related_tickets.add(ticket.id)
            related_users.add(ticket.requester_user_id)
            if ticket.business_id:
                related_businesses.add(ticket.business_id)
            if ticket.order_id and ticket.order_id in orders:
                include_order(orders[ticket.order_id])

        if anchor_type == "user":
            related_users.add(anchor.id)
            for business in businesses.values():
                if business.owner_user_id == anchor.id:
                    related_businesses.add(business.id)
            for order in orders.values():
                if order.remitter_user_id == anchor.id or order.business_id in related_businesses:
                    include_order(order)
            for ticket in tickets.values():
                if ticket.requester_user_id == anchor.id or ticket.business_id in related_businesses:
                    include_ticket(ticket)
            for intake in intakes.values():
                if (
                    intake.telegram_user_id == anchor.telegram_id
                    or intake.linked_telegram_user_id == anchor.telegram_id
                    or intake.created_business_id in related_businesses
                ):
                    related_intakes.add(intake.id)
        elif anchor_type == "business":
            related_businesses.add(anchor.id)
            related_users.add(anchor.owner_user_id)
            for order in orders.values():
                if order.business_id == anchor.id:
                    include_order(order)
            for ticket in tickets.values():
                if ticket.business_id == anchor.id:
                    include_ticket(ticket)
            for intake in intakes.values():
                if intake.created_business_id == anchor.id:
                    related_intakes.add(intake.id)
        elif anchor_type == "business_intake":
            related_intakes.add(anchor.id)
            if anchor.created_business_id and anchor.created_business_id in businesses:
                business = businesses[anchor.created_business_id]
                related_businesses.add(business.id)
                related_users.add(business.owner_user_id)
                for order in orders.values():
                    if order.business_id == business.id:
                        include_order(order)
                for ticket in tickets.values():
                    if ticket.business_id == business.id:
                        include_ticket(ticket)
            for user in users.values():
                if user.telegram_id in {anchor.telegram_user_id, anchor.linked_telegram_user_id}:
                    related_users.add(user.id)
        elif anchor_type == "order":
            include_order(anchor)
            for ticket in tickets.values():
                if ticket.order_id == anchor.id:
                    include_ticket(ticket)
            for intake in intakes.values():
                if intake.created_business_id == anchor.business_id:
                    related_intakes.add(intake.id)
        else:
            include_ticket(anchor)
            for ticket in tickets.values():
                same_order = bool(anchor.order_id and ticket.order_id == anchor.order_id)
                same_general_case = not anchor.order_id and ticket.requester_user_id == anchor.requester_user_id and ticket.business_id == anchor.business_id
                if same_order or same_general_case:
                    include_ticket(ticket)
            for intake in intakes.values():
                if anchor.business_id and intake.created_business_id == anchor.business_id:
                    related_intakes.add(intake.id)

        for business_id in list(related_businesses):
            business = businesses.get(business_id)
            if business:
                related_users.add(business.owner_user_id)

        return {
            "anchor_type": anchor_type,
            "anchor_id": anchor_id,
            "anchor_record": anchor,
            "user_ids": related_users,
            "business_ids": related_businesses,
            "order_ids": related_orders,
            "ticket_ids": related_tickets,
            "intake_ids": related_intakes,
            "ticket_records": [tickets[ticket_id] for ticket_id in related_tickets if ticket_id in tickets],
        }

    def anchor_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        record = context["anchor_record"]
        anchor_type = context["anchor_type"]
        title = {
            "user": f"Usuario {_record_value(record, 'first_name') or _record_value(record, 'username') or ''}".strip(),
            "business": _record_value(record, "business_name"),
            "business_intake": _record_value(record, "business_name") or "Solicitud de negocio",
            "order": f"Orden {_record_value(record, 'public_order_code')}",
            "support_ticket": "Ticket de soporte",
        }[anchor_type]
        route_names = {
            "user": "user",
            "business": "business",
            "business_intake": "business-intake",
            "order": "order",
            "support_ticket": "support-ticket",
        }
        return {
            "type": anchor_type,
            "id": context["anchor_id"],
            "title": title,
            "status": _record_value(record, "status") or _record_value(record, "verification_status"),
            "action_route": f"admin://{route_names[anchor_type]}/{context['anchor_id']}",
        }

    def participants_payload(self, context: dict[str, Any], *, allowed_ids: dict[str, set[str]] | None) -> dict[str, Any]:
        users = getattr(self._users, "_users_by_id", {})
        businesses = getattr(self._businesses, "businesses", {})
        visible_users = context["user_ids"] if allowed_ids is None else context["user_ids"] & allowed_ids["user"]
        visible_businesses = context["business_ids"] if allowed_ids is None else context["business_ids"] & allowed_ids["business"]
        visible_business_records = [businesses[business_id] for business_id in sorted(visible_businesses) if business_id in businesses]
        owner_ids = {item.owner_user_id for item in visible_business_records}
        client = next(
            (
                users[user_id]
                for user_id in sorted(visible_users)
                if users.get(user_id) and users[user_id].role == "remitter" and user_id not in owner_ids
            ),
            None,
        )
        business = visible_business_records[0] if visible_business_records else None
        owner = users.get(business.owner_user_id) if business else None
        return {
            "client": (
                {
                    "user_id": client.id,
                    "display_name": client.first_name or client.username or "Cliente",
                    "telegram_hint": mask_telegram_id(client.telegram_id),
                    "action_route": f"admin://user/{client.id}",
                }
                if client
                else None
            ),
            "business": (
                {
                    "business_id": business.id,
                    "name": business.business_name,
                    "status": business.verification_status,
                    "action_route": f"admin://business/{business.id}",
                }
                if business
                else None
            ),
            "business_owner": (
                {
                    "user_id": owner.id,
                    "telegram_hint": mask_telegram_id(owner.telegram_id),
                    "action_route": f"admin://user/{owner.id}",
                }
                if owner and owner.id in visible_users
                else None
            ),
        }

    def page_orders(
        self,
        context: dict[str, Any],
        *,
        visible_ids: set[str] | None,
        position: dict[str, str] | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, str] | None, int]:
        ids = context["order_ids"] if visible_ids is None else context["order_ids"] & visible_ids
        records = [self._orders.orders[item_id] for item_id in ids if item_id in self._orders.orders]
        page, next_position, total = _page(records, field="created_at", position=position, limit=limit)
        return [_order_payload(item) for item in page], next_position, total

    def page_support_tickets(
        self,
        context: dict[str, Any],
        *,
        visible_ids: set[str] | None,
        include_archived: bool,
        position: dict[str, str] | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, str] | None, int]:
        ids = context["ticket_ids"] if visible_ids is None else context["ticket_ids"] & visible_ids
        records = [
            self._support.tickets[item_id]
            for item_id in ids
            if item_id in self._support.tickets
            and (include_archived or self._support.tickets[item_id].status not in ARCHIVED_SUPPORT_STATUSES)
        ]
        page, next_position, total = _page(records, field="updated_at", position=position, limit=limit)
        return [_ticket_payload(item) for item in page], next_position, total

    def page_business_intakes(
        self,
        context: dict[str, Any],
        *,
        visible_ids: set[str] | None,
        position: dict[str, str] | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, str] | None, int]:
        ids = context["intake_ids"] if visible_ids is None else context["intake_ids"] & visible_ids
        records = [self._business_intake.intakes[item_id] for item_id in ids if item_id in self._business_intake.intakes]
        page, next_position, total = _page(records, field="created_at", position=position, limit=limit)
        return [_intake_payload(item) for item in page], next_position, total

    def evidence_payload(
        self,
        context: dict[str, Any],
        *,
        visible_ids: dict[str, set[str]] | None,
        support_limited: bool,
        position: dict[str, str] | None,
        limit: int,
    ) -> tuple[dict[str, Any], dict[str, str] | None, int]:
        order_ids = context["order_ids"] if visible_ids is None else context["order_ids"] & visible_ids["order"]
        ticket_ids = context["ticket_ids"] if visible_ids is None else context["ticket_ids"] & visible_ids["support_ticket"]
        intake_ids = context["intake_ids"] if visible_ids is None else context["intake_ids"] & visible_ids["business_intake"]
        payment_report_present = any(report.order_id in order_ids for report in self._orders.payment_reports.values())
        chat_order_ids = {
            message.order_id for message in self._chat.messages.values() if message.order_id in order_ids and message.deleted_at is None
        }
        evidence_items: list[dict[str, Any]] = []
        if not support_limited:
            for document in self._business_intake.documents.values():
                if document.resource_id in intake_ids and document.deleted_at is None:
                    evidence_items.append(
                        {
                            "id": f"document:{document.id}",
                            "kind": "document",
                            "document_type": document.document_kind,
                            "mime_type": document.mime_type,
                            "size_bytes": document.size_bytes,
                            "created_at": document.created_at.isoformat(),
                            "download_available": False,
                            "action_route": f"admin://business-intake/{document.resource_id}",
                            "_created_at": document.created_at,
                        }
                    )
        message_ids = {message.id for message in self._support.messages.values() if message.ticket_id in ticket_ids}
        for file in self._support.files.values():
            if file.deleted_at is not None or file.file_type != "support_attachment":
                continue
            ticket_id = file.resource_id if file.resource_type == "support_ticket" else None
            if file.resource_type == "support_message" and file.resource_id in message_ids:
                message = self._support.messages.get(file.resource_id)
                ticket_id = message.ticket_id if message else None
            if ticket_id not in ticket_ids:
                continue
            evidence_items.append(
                {
                    "id": f"attachment:{file.id}",
                    "kind": "attachment",
                    "attachment_type": file.file_type,
                    "mime_type": file.mime_type,
                    "size_bytes": file.size_bytes,
                    "created_at": file.created_at.isoformat(),
                    "download_available": False,
                    "action_route": f"admin://support-ticket/{ticket_id}",
                    "_created_at": file.created_at,
                }
            )
        page, next_position, total = _page(evidence_items, field="_created_at", position=position, limit=limit)
        documents = [
            {key: value for key, value in item.items() if key not in {"id", "kind", "_created_at"}}
            for item in page
            if item["kind"] == "document"
        ]
        attachments = [
            {key: value for key, value in item.items() if key not in {"id", "kind", "_created_at"}}
            for item in page
            if item["kind"] == "attachment"
        ]
        return {
            "payment_report_present": payment_report_present,
            "chat_evidence_available": bool(chat_order_ids),
            "chat_action_routes": [f"admin://order/{order_id}" for order_id in sorted(chat_order_ids)[:50]],
            "documents": documents,
            "attachments": attachments,
        }, next_position, total

    def page_timeline(
        self,
        context: dict[str, Any],
        *,
        visible_ids: dict[str, set[str]] | None,
        position: dict[str, str] | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, str] | None, int]:
        order_ids = context["order_ids"] if visible_ids is None else context["order_ids"] & visible_ids["order"]
        ticket_ids = context["ticket_ids"] if visible_ids is None else context["ticket_ids"] & visible_ids["support_ticket"]
        intake_ids = context["intake_ids"] if visible_ids is None else context["intake_ids"] & visible_ids["business_intake"]
        events: list[dict[str, Any]] = []
        for order_id in order_ids:
            order = self._orders.orders.get(order_id)
            if order:
                events.append(
                    {
                        **_timeline_payload(
                            event_id=f"order:{order.id}:created",
                            event_type="order_created",
                            label="Orden creada",
                            entity_type="order",
                            entity_id=order.id,
                            created_at=order.created_at,
                            action_route=f"admin://order/{order.id}",
                        ),
                        "_created_at": order.created_at,
                    }
                )
        for event in self._orders.events:
            if event.order_id in order_ids and event.event_type in ALLOWED_ORDER_EVENTS:
                events.append(
                    {
                        **_timeline_payload(
                            event_id=f"order-event:{event.id}",
                            event_type=event.event_type,
                            label="Estado de orden actualizado",
                            entity_type="order",
                            entity_id=event.order_id,
                            created_at=event.created_at,
                            action_route=f"admin://order/{event.order_id}",
                            from_status=event.from_status,
                            to_status=event.to_status,
                        ),
                        "_created_at": event.created_at,
                    }
                )
        for report in self._orders.payment_reports.values():
            if report.order_id in order_ids:
                events.append(
                    {
                        **_timeline_payload(
                            event_id=f"payment-report:{report.id}",
                            event_type="payment_report_received",
                            label="Reporte de pago recibido",
                            entity_type="order",
                            entity_id=report.order_id,
                            created_at=report.created_at,
                            action_route=f"admin://order/{report.order_id}",
                        ),
                        "_created_at": report.created_at,
                    }
                )
        for ticket_id in ticket_ids:
            ticket = self._support.tickets.get(ticket_id)
            if ticket:
                events.append(
                    {
                        **_timeline_payload(
                            event_id=f"support:{ticket.id}:created",
                            event_type="support_ticket_created",
                            label="Ticket de soporte creado",
                            entity_type="support_ticket",
                            entity_id=ticket.id,
                            created_at=ticket.created_at,
                            action_route=f"admin://support-ticket/{ticket.id}",
                        ),
                        "_created_at": ticket.created_at,
                    }
                )
        for event in self._support.events.values():
            if event.ticket_id in ticket_ids and event.event_type in ALLOWED_SUPPORT_EVENTS:
                events.append(
                    {
                        **_timeline_payload(
                            event_id=f"support-event:{event.id}",
                            event_type=event.event_type,
                            label="Estado de soporte actualizado",
                            entity_type="support_ticket",
                            entity_id=event.ticket_id,
                            created_at=event.created_at,
                            action_route=f"admin://support-ticket/{event.ticket_id}",
                            from_status=event.from_status,
                            to_status=event.to_status,
                        ),
                        "_created_at": event.created_at,
                    }
                )
        for intake_id in intake_ids:
            intake = self._business_intake.intakes.get(intake_id)
            if intake:
                events.append(
                    {
                        **_timeline_payload(
                            event_id=f"intake:{intake.id}:created",
                            event_type="business_intake_received",
                            label="Solicitud de negocio recibida",
                            entity_type="business_intake",
                            entity_id=intake.id,
                            created_at=intake.created_at,
                            action_route=f"admin://business-intake/{intake.id}",
                        ),
                        "_created_at": intake.created_at,
                    }
                )
                if intake.reviewed_at and intake.status in {"accepted", "rejected"}:
                    events.append(
                        {
                            **_timeline_payload(
                                event_id=f"intake:{intake.id}:reviewed",
                                event_type=f"business_intake_{intake.status}",
                                label="Solicitud de negocio revisada",
                                entity_type="business_intake",
                                entity_id=intake.id,
                                created_at=intake.reviewed_at,
                                action_route=f"admin://business-intake/{intake.id}",
                                to_status=intake.status,
                            ),
                            "_created_at": intake.reviewed_at,
                        }
                    )
        page, next_position, total = _page(events, field="_created_at", position=position, limit=limit)
        return [{key: value for key, value in item.items() if key != "_created_at"} for item in page], next_position, total


class PostgresAdminInvestigationCaseFileRepository:
    """Postgres adapter that reads the same allowlisted case-file shape."""

    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def resolve_context(self, *, anchor_type: str, anchor_id: str) -> dict[str, Any] | None:
        table_map = {
            "user": "users",
            "business": "businesses",
            "business_intake": "business_intake_requests",
            "order": "orders",
            "support_ticket": "support_tickets",
        }
        with self._connect() as connection, connection.cursor() as cursor:
            table = table_map[anchor_type]
            cursor.execute(f"select {TABLE_COLUMNS[table]} from {table} where id = %s", (anchor_id,))  # noqa: S608
            anchor = cursor.fetchone()
            if anchor is None:
                return None
            anchor = dict(anchor)
            user_ids: set[str] = set()
            business_ids: set[str] = set()
            order_ids: set[str] = set()
            ticket_ids: set[str] = set()
            intake_ids: set[str] = set()

            def select_ids(query: str, params: tuple[Any, ...]) -> set[str]:
                cursor.execute(query, params)
                return {str(row["id"]) for row in cursor.fetchall()}

            if anchor_type == "user":
                user_ids.add(anchor_id)
                business_ids |= select_ids("select id from businesses where owner_user_id = %s", (anchor_id,))
                order_ids |= select_ids("select id from orders where remitter_user_id = %s", (anchor_id,))
                ticket_ids |= select_ids("select id from support_tickets where requester_user_id = %s", (anchor_id,))
                if business_ids:
                    order_ids |= select_ids("select id from orders where business_id = any(%s::uuid[])", (list(business_ids),))
                    ticket_ids |= select_ids("select id from support_tickets where business_id = any(%s::uuid[])", (list(business_ids),))
                    intake_ids |= select_ids(
                        "select id from business_intake_requests where created_business_id = any(%s::uuid[])",
                        (list(business_ids),),
                    )
                if anchor.get("telegram_id") is not None:
                    intake_ids |= select_ids(
                        "select id from business_intake_requests where telegram_user_id = %s or linked_telegram_user_id = %s",
                        (anchor["telegram_id"], anchor["telegram_id"]),
                    )
            elif anchor_type == "business":
                business_ids.add(anchor_id)
                user_ids.add(str(anchor["owner_user_id"]))
                order_ids |= select_ids("select id from orders where business_id = %s", (anchor_id,))
                ticket_ids |= select_ids("select id from support_tickets where business_id = %s", (anchor_id,))
                intake_ids |= select_ids("select id from business_intake_requests where created_business_id = %s", (anchor_id,))
            elif anchor_type == "business_intake":
                intake_ids.add(anchor_id)
                if anchor.get("created_business_id"):
                    business_ids.add(str(anchor["created_business_id"]))
                    order_ids |= select_ids("select id from orders where business_id = %s", (anchor["created_business_id"],))
                    ticket_ids |= select_ids("select id from support_tickets where business_id = %s", (anchor["created_business_id"],))
                telegram_ids = [value for value in {anchor.get("telegram_user_id"), anchor.get("linked_telegram_user_id")} if value is not None]
                if telegram_ids:
                    cursor.execute("select id from users where telegram_id = any(%s)", (telegram_ids,))
                    user_ids |= {str(row["id"]) for row in cursor.fetchall()}
            elif anchor_type == "order":
                order_ids.add(anchor_id)
                business_ids.add(str(anchor["business_id"]))
                user_ids.add(str(anchor["remitter_user_id"]))
                ticket_ids |= select_ids("select id from support_tickets where order_id = %s", (anchor_id,))
                intake_ids |= select_ids("select id from business_intake_requests where created_business_id = %s", (anchor["business_id"],))
            else:
                ticket_ids.add(anchor_id)
                user_ids.add(str(anchor["requester_user_id"]))
                if anchor.get("business_id"):
                    business_ids.add(str(anchor["business_id"]))
                if anchor.get("order_id"):
                    order_ids.add(str(anchor["order_id"]))
                    ticket_ids |= select_ids("select id from support_tickets where order_id = %s", (anchor["order_id"],))
                else:
                    cursor.execute(
                        """
                        select id from support_tickets
                        where requester_user_id = %s and business_id is not distinct from %s and order_id is null
                        """,
                        (anchor["requester_user_id"], anchor.get("business_id")),
                    )
                    ticket_ids |= {str(row["id"]) for row in cursor.fetchall()}
                if anchor.get("business_id"):
                    intake_ids |= select_ids(
                        "select id from business_intake_requests where created_business_id = %s",
                        (anchor["business_id"],),
                    )

            if order_ids:
                cursor.execute("select business_id, remitter_user_id from orders where id = any(%s::uuid[])", (list(order_ids),))
                for row in cursor.fetchall():
                    business_ids.add(str(row["business_id"]))
                    user_ids.add(str(row["remitter_user_id"]))
            if business_ids:
                cursor.execute("select owner_user_id from businesses where id = any(%s::uuid[])", (list(business_ids),))
                user_ids |= {str(row["owner_user_id"]) for row in cursor.fetchall()}
            ticket_records: list[dict[str, Any]] = []
            if ticket_ids:
                cursor.execute(
                    """
                    select id, requester_user_id, requester_role, scope, category, status, priority,
                           business_id, order_id, assigned_support_user_id, created_at, updated_at
                    from support_tickets where id = any(%s::uuid[])
                    """,
                    (list(ticket_ids),),
                )
                ticket_records = [dict(row) for row in cursor.fetchall()]
            return {
                "anchor_type": anchor_type,
                "anchor_id": anchor_id,
                "anchor_record": anchor,
                "user_ids": user_ids,
                "business_ids": business_ids,
                "order_ids": order_ids,
                "ticket_ids": ticket_ids,
                "intake_ids": intake_ids,
                "ticket_records": ticket_records,
            }

    def _fetch_records(self, table: str, ids: set[str]) -> list[dict[str, Any]]:
        if not ids:
            return []
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(
                f"select {TABLE_COLUMNS[table]} from {table} where id = any(%s::uuid[])",  # noqa: S608
                (list(ids),),
            )
            return [dict(row) for row in cursor.fetchall()]

    def anchor_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        record = context["anchor_record"]
        anchor_type = context["anchor_type"]
        title = {
            "user": f"Usuario {record.get('first_name') or record.get('username') or ''}".strip(),
            "business": record.get("business_name"),
            "business_intake": record.get("business_name") or "Solicitud de negocio",
            "order": f"Orden {record.get('public_order_code')}",
            "support_ticket": "Ticket de soporte",
        }[anchor_type]
        route_names = {
            "user": "user",
            "business": "business",
            "business_intake": "business-intake",
            "order": "order",
            "support_ticket": "support-ticket",
        }
        return {
            "type": anchor_type,
            "id": context["anchor_id"],
            "title": title,
            "status": record.get("status") or record.get("verification_status"),
            "action_route": f"admin://{route_names[anchor_type]}/{context['anchor_id']}",
        }

    def participants_payload(self, context: dict[str, Any], *, allowed_ids: dict[str, set[str]] | None) -> dict[str, Any]:
        user_ids = context["user_ids"] if allowed_ids is None else context["user_ids"] & allowed_ids["user"]
        business_ids = context["business_ids"] if allowed_ids is None else context["business_ids"] & allowed_ids["business"]
        users = self._fetch_records("users", user_ids)
        businesses = self._fetch_records("businesses", business_ids)
        businesses.sort(key=lambda item: str(item["id"]))
        owner_ids = {str(item["owner_user_id"]) for item in businesses}
        client = next(
            (
                item
                for item in sorted(users, key=lambda value: str(value["id"]))
                if item.get("role") == "remitter" and str(item["id"]) not in owner_ids
            ),
            None,
        )
        business = businesses[0] if businesses else None
        owner = next((item for item in users if business and str(item["id"]) == str(business["owner_user_id"])), None)
        return {
            "client": (
                {
                    "user_id": str(client["id"]),
                    "display_name": client.get("first_name") or client.get("username") or "Cliente",
                    "telegram_hint": mask_telegram_id(client.get("telegram_id")),
                    "action_route": f"admin://user/{client['id']}",
                }
                if client
                else None
            ),
            "business": (
                {
                    "business_id": str(business["id"]),
                    "name": business["business_name"],
                    "status": business["verification_status"],
                    "action_route": f"admin://business/{business['id']}",
                }
                if business
                else None
            ),
            "business_owner": (
                {
                    "user_id": str(owner["id"]),
                    "telegram_hint": mask_telegram_id(owner.get("telegram_id")),
                    "action_route": f"admin://user/{owner['id']}",
                }
                if owner
                else None
            ),
        }

    def _page_table(
        self,
        *,
        table: str,
        ids: set[str],
        field: str,
        position: dict[str, str] | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, str] | None, int]:
        if not ids:
            return [], None, 0
        where = ["id = any(%s::uuid[])"]
        page_params: list[Any] = [list(ids)]
        if position:
            where.append(f"({field}, id::text) < (%s::timestamptz, %s)")  # noqa: S608
            page_params.extend([position["at"], position["id"]])
        page_params.append(limit + 1)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(f"select count(*) as total from {table} where id = any(%s::uuid[])", (list(ids),))  # noqa: S608
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                f"""
                select {TABLE_COLUMNS[table]}
                from {table}
                where {" and ".join(where)}
                order by {field} desc, id::text desc
                limit %s
                """,  # noqa: S608
                page_params,
            )
            rows = [dict(row) for row in cursor.fetchall()]
        truncated = len(rows) > limit
        page = rows[:limit]
        next_position = None
        if truncated and page:
            next_position = {"at": page[-1][field].isoformat(), "id": str(page[-1]["id"])}
        return page, next_position, total

    def page_orders(self, context: dict[str, Any], *, visible_ids: set[str] | None, position: dict[str, str] | None, limit: int):
        ids = context["order_ids"] if visible_ids is None else context["order_ids"] & visible_ids
        page, next_position, total = self._page_table(
            table="orders",
            ids=ids,
            field="created_at",
            position=position,
            limit=limit,
        )
        return [_order_payload(item) for item in page], next_position, total

    def page_support_tickets(
        self,
        context: dict[str, Any],
        *,
        visible_ids: set[str] | None,
        include_archived: bool,
        position: dict[str, str] | None,
        limit: int,
    ):
        ids = context["ticket_ids"] if visible_ids is None else context["ticket_ids"] & visible_ids
        page, next_position, total = self._page_table(
            table="support_tickets",
            ids=ids,
            field="updated_at",
            position=position,
            limit=limit,
        )
        return [_ticket_payload(item) for item in page], next_position, total

    def page_business_intakes(self, context: dict[str, Any], *, visible_ids: set[str] | None, position: dict[str, str] | None, limit: int):
        ids = context["intake_ids"] if visible_ids is None else context["intake_ids"] & visible_ids
        page, next_position, total = self._page_table(
            table="business_intake_requests",
            ids=ids,
            field="created_at",
            position=position,
            limit=limit,
        )
        return [_intake_payload(item) for item in page], next_position, total

    def evidence_payload(
        self,
        context: dict[str, Any],
        *,
        visible_ids: dict[str, set[str]] | None,
        support_limited: bool,
        position: dict[str, str] | None,
        limit: int,
    ) -> tuple[dict[str, Any], dict[str, str] | None, int]:
        order_ids = context["order_ids"] if visible_ids is None else context["order_ids"] & visible_ids["order"]
        ticket_ids = context["ticket_ids"] if visible_ids is None else context["ticket_ids"] & visible_ids["support_ticket"]
        intake_ids = context["intake_ids"] if visible_ids is None else context["intake_ids"] & visible_ids["business_intake"]
        evidence_items: list[dict[str, Any]] = []
        position_at = position["at"] if position else None
        position_id = position["id"] if position else None
        with self._connect() as connection, connection.cursor() as cursor:
            payment_report_present = False
            chat_order_ids: set[str] = set()
            if order_ids:
                cursor.execute("select exists(select 1 from payment_reports where order_id = any(%s::uuid[])) as present", (list(order_ids),))
                payment_report_present = bool(cursor.fetchone()["present"])
                cursor.execute(
                    """
                    select distinct order_id
                    from messages
                    where order_id = any(%s::uuid[]) and deleted_at is null
                    order by order_id
                    limit 50
                    """,
                    (list(order_ids),),
                )
                chat_order_ids = {str(row["order_id"]) for row in cursor.fetchall()}
            documents_total = 0
            if intake_ids and not support_limited:
                cursor.execute(
                    """
                    select count(*) as total from file_assets
                    where resource_type = 'business_intake'
                      and resource_id = any(%s::uuid[])
                      and deleted_at is null
                    """,
                    (list(intake_ids),),
                )
                documents_total = int(cursor.fetchone()["total"])
                cursor.execute(
                    """
                    select 'document:' || id::text as evidence_id,
                           coalesce(metadata_json->>'document_kind', file_type) as document_kind,
                           mime_type, size_bytes, created_at, resource_id
                    from file_assets
                    where resource_type = 'business_intake'
                      and resource_id = any(%s::uuid[])
                      and deleted_at is null
                      and (
                        %s::timestamptz is null
                        or (created_at, 'document:' || id::text) < (%s::timestamptz, %s)
                      )
                    order by created_at desc, evidence_id desc
                    limit %s
                    """,
                    (list(intake_ids), position_at, position_at, position_id, limit + 1),
                )
                evidence_items.extend(
                    {
                        "id": row["evidence_id"],
                        "kind": "document",
                        "document_type": row["document_kind"],
                        "mime_type": row["mime_type"],
                        "size_bytes": row["size_bytes"],
                        "created_at": row["created_at"].isoformat(),
                        "download_available": False,
                        "action_route": f"admin://business-intake/{row['resource_id']}",
                        "_created_at": row["created_at"],
                    }
                    for row in cursor.fetchall()
                )
            attachments_total = 0
            if ticket_ids:
                cursor.execute(
                    """
                    select count(*) as total
                    from file_assets f
                    left join support_tickets t on f.resource_type = 'support_ticket' and f.resource_id = t.id
                    left join support_messages sm on f.resource_type = 'support_message' and f.resource_id = sm.id
                    where coalesce(t.id, sm.ticket_id) = any(%s::uuid[])
                      and f.file_type = 'support_attachment'
                      and f.deleted_at is null
                    """,
                    (list(ticket_ids),),
                )
                attachments_total = int(cursor.fetchone()["total"])
                cursor.execute(
                    """
                    select 'attachment:' || f.id::text as evidence_id,
                           f.file_type, f.mime_type, f.size_bytes, f.created_at,
                           coalesce(t.id, sm.ticket_id) as ticket_id
                    from file_assets f
                    left join support_tickets t on f.resource_type = 'support_ticket' and f.resource_id = t.id
                    left join support_messages sm on f.resource_type = 'support_message' and f.resource_id = sm.id
                    where coalesce(t.id, sm.ticket_id) = any(%s::uuid[])
                      and f.file_type = 'support_attachment'
                      and f.deleted_at is null
                      and (
                        %s::timestamptz is null
                        or (f.created_at, 'attachment:' || f.id::text) < (%s::timestamptz, %s)
                      )
                    order by f.created_at desc, evidence_id desc
                    limit %s
                    """,
                    (list(ticket_ids), position_at, position_at, position_id, limit + 1),
                )
                evidence_items.extend(
                    {
                        "id": row["evidence_id"],
                        "kind": "attachment",
                        "attachment_type": row["file_type"],
                        "mime_type": row["mime_type"],
                        "size_bytes": row["size_bytes"],
                        "created_at": row["created_at"].isoformat(),
                        "download_available": False,
                        "action_route": f"admin://support-ticket/{row['ticket_id']}",
                        "_created_at": row["created_at"],
                    }
                    for row in cursor.fetchall()
                )
        evidence_items.sort(key=lambda item: (item["_created_at"], item["id"]), reverse=True)
        truncated = len(evidence_items) > limit
        page = evidence_items[:limit]
        next_position = None
        if truncated and page:
            next_position = {"at": page[-1]["_created_at"].isoformat(), "id": page[-1]["id"]}
        documents = [
            {key: value for key, value in item.items() if key not in {"id", "kind", "_created_at"}}
            for item in page
            if item["kind"] == "document"
        ]
        attachments = [
            {key: value for key, value in item.items() if key not in {"id", "kind", "_created_at"}}
            for item in page
            if item["kind"] == "attachment"
        ]
        return {
            "payment_report_present": payment_report_present,
            "chat_evidence_available": bool(chat_order_ids),
            "chat_action_routes": [f"admin://order/{order_id}" for order_id in sorted(chat_order_ids)],
            "documents": documents,
            "attachments": attachments,
        }, next_position, documents_total + attachments_total

    def page_timeline(
        self,
        context: dict[str, Any],
        *,
        visible_ids: dict[str, set[str]] | None,
        position: dict[str, str] | None,
        limit: int,
    ):
        order_ids = context["order_ids"] if visible_ids is None else context["order_ids"] & visible_ids["order"]
        ticket_ids = context["ticket_ids"] if visible_ids is None else context["ticket_ids"] & visible_ids["support_ticket"]
        intake_ids = context["intake_ids"] if visible_ids is None else context["intake_ids"] & visible_ids["business_intake"]
        events_sql = """
            select 'order:' || id::text || ':created' as event_id,
                   'order_created'::text as event_type, 'order'::text as entity_type,
                   id::text as entity_id, null::text as from_status, status::text as to_status,
                   created_at
            from orders where id = any(%s::uuid[])
            union all
            select 'order-event:' || id::text, event_type::text, 'order'::text,
                   order_id::text, from_status::text, to_status::text, created_at
            from order_state_events
            where order_id = any(%s::uuid[]) and event_type = any(%s)
            union all
            select 'payment-report:' || id::text, 'payment_report_received'::text, 'order'::text,
                   order_id::text, null::text, null::text, created_at
            from payment_reports where order_id = any(%s::uuid[])
            union all
            select 'support:' || id::text || ':created', 'support_ticket_created'::text,
                   'support_ticket'::text, id::text, null::text, status::text, created_at
            from support_tickets where id = any(%s::uuid[])
            union all
            select 'support-event:' || id::text, event_type::text, 'support_ticket'::text,
                   ticket_id::text, from_status::text, to_status::text, created_at
            from support_ticket_events
            where ticket_id = any(%s::uuid[]) and event_type = any(%s)
            union all
            select 'intake:' || id::text || ':created', 'business_intake_received'::text,
                   'business_intake'::text, id::text, null::text, status::text, created_at
            from business_intake_requests where id = any(%s::uuid[])
            union all
            select 'intake:' || id::text || ':reviewed', 'business_intake_' || status,
                   'business_intake'::text, id::text, null::text, status::text, reviewed_at
            from business_intake_requests
            where id = any(%s::uuid[]) and status in ('accepted', 'rejected') and reviewed_at is not null
        """
        event_params = [
            list(order_ids),
            list(order_ids),
            list(ALLOWED_ORDER_EVENTS),
            list(order_ids),
            list(ticket_ids),
            list(ticket_ids),
            list(ALLOWED_SUPPORT_EVENTS),
            list(intake_ids),
            list(intake_ids),
        ]
        position_clause = ""
        page_params = [*event_params]
        if position:
            position_clause = "where (created_at, event_id) < (%s::timestamptz, %s)"
            page_params.extend([position["at"], position["id"]])
        page_params.append(limit + 1)
        with self._connect() as connection, connection.cursor() as cursor:
            cursor.execute(f"with events as ({events_sql}) select count(*) as total from events", event_params)
            total = int(cursor.fetchone()["total"])
            cursor.execute(
                f"""
                with events as ({events_sql})
                select * from events
                {position_clause}
                order by created_at desc, event_id desc
                limit %s
                """,
                page_params,
            )
            rows = [dict(row) for row in cursor.fetchall()]
        truncated = len(rows) > limit
        page = rows[:limit]
        next_position = None
        if truncated and page:
            next_position = {"at": page[-1]["created_at"].isoformat(), "id": page[-1]["event_id"]}
        items = []
        for row in page:
            entity_type = row["entity_type"]
            entity_id = row["entity_id"]
            label = {
                "order_created": "Orden creada",
                "payment_report_received": "Reporte de pago recibido",
                "support_ticket_created": "Ticket de soporte creado",
                "business_intake_received": "Solicitud de negocio recibida",
                "business_intake_accepted": "Solicitud de negocio revisada",
                "business_intake_rejected": "Solicitud de negocio revisada",
            }.get(row["event_type"], "Estado actualizado")
            route_name = "business-intake" if entity_type == "business_intake" else entity_type.replace("_", "-")
            items.append(
                _timeline_payload(
                    event_id=row["event_id"],
                    event_type=row["event_type"],
                    label=label,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    created_at=row["created_at"],
                    action_route=f"admin://{route_name}/{entity_id}",
                    from_status=row["from_status"],
                    to_status=row["to_status"],
                )
            )
        return items, next_position, total
