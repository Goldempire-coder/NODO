from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from app.modules.admin.investigation import compact_digits, contains_digits, contains_text
from app.modules.admin.investigation_candidates import CandidateFilters
from app.modules.admin.user_presenters import mask_telegram_id
from app.modules.support.models import ACTIVE_SUPPORT_STATUSES, ARCHIVED_SUPPORT_STATUSES
from app.shared.db.connection import pooled_connect


def _escape_like_literal(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _display_name(user: Any) -> str:
    full = " ".join(part for part in (getattr(user, "first_name", None), getattr(user, "last_name", None)) if part)
    return full or getattr(user, "username", None) or "Cliente"


def _ticket_matches_visibility(ticket: Any, visibility: dict[str, Any]) -> bool:
    if visibility["mode"] in {"admin", "all_orders"}:
        return True
    for rule in visibility["ticket_rules"]:
        if rule["permission"] == "view_assigned_support_tickets" and rule["scope"] == "assigned_only":
            if ticket.assigned_support_user_id == visibility["user_id"]:
                return True
        if rule["permission"] != "view_support_queue":
            continue
        if rule["scope"] == "queue_scope" and (rule["scope_value"] is None or ticket.scope == rule["scope_value"]):
            return True
        if rule["scope"] == "category_scope" and ticket.category == rule["scope_value"]:
            return True
    return False


def _status_matches(ticket: Any, group: str) -> bool:
    if group == "active":
        return ticket.status in ACTIVE_SUPPORT_STATUSES
    if group == "archived":
        return ticket.status in ARCHIVED_SUPPORT_STATUSES
    return True


class InMemoryAdminInvestigationCandidatesRepository:
    def __init__(self, *, users, businesses, orders, support) -> None:  # type: ignore[no-untyped-def]
        self._users = users
        self._businesses = businesses
        self._orders = orders
        self._support = support

    def search(
        self,
        *,
        filters: CandidateFilters,
        visibility: dict[str, Any],
        position: dict[str, str] | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, str] | None]:
        candidates: list[tuple[Any, Any, Any, list[Any]]] = []
        for order in self._orders.orders.values():
            user = self._users.get_user_by_id(order.remitter_user_id)
            business = self._businesses.get_business(order.business_id)
            if user is None or business is None:
                continue
            tickets = [ticket for ticket in self._support.tickets.values() if ticket.order_id == order.id]
            visible_tickets = [ticket for ticket in tickets if _ticket_matches_visibility(ticket, visibility)]
            if visibility["mode"] == "ticket_scope" and not visible_tickets:
                continue
            if filters.support_status_group != "all" and not any(
                _status_matches(ticket, filters.support_status_group) for ticket in visible_tickets
            ):
                continue
            if not self._matches(order=order, user=user, business=business, filters=filters):
                continue
            if position is not None:
                cursor_key = (datetime.fromisoformat(position["at"]), position["id"])
                if (order.created_at, order.id) >= cursor_key:
                    continue
            candidates.append((order, user, business, visible_tickets))
        candidates.sort(key=lambda item: (item[0].created_at, item[0].id), reverse=True)
        page = candidates[: limit + 1]
        has_more = len(page) > limit
        page = page[:limit]
        items = [
            self._item(order=order, user=user, business=business, tickets=tickets, filters=filters)
            for order, user, business, tickets in page
        ]
        next_position = (
            {"at": page[-1][0].created_at.isoformat(), "id": page[-1][0].id}
            if has_more and page
            else None
        )
        return items, next_position

    @staticmethod
    def _matches(*, order: Any, user: Any, business: Any, filters: CandidateFilters) -> bool:
        if filters.client_hint:
            hint = filters.client_hint
            digits = compact_digits(hint)
            matched = any(
                (
                    contains_text(user.id, hint),
                    contains_text(user.username, hint),
                    contains_text(user.first_name, hint),
                    contains_text(user.last_name, hint),
                    contains_digits(user.phone, digits),
                    contains_digits(user.telegram_id, digits),
                    contains_text(order.public_order_code, hint),
                )
            )
            if not matched:
                return False
        if filters.business_hint:
            hint = filters.business_hint
            if not any(
                (
                    contains_text(business.id, hint),
                    contains_text(business.business_name, hint),
                    contains_text(business.referral_code, hint),
                    contains_text(order.business_name_snapshot, hint),
                )
            ):
                return False
        if filters.amount_min_usd is not None and not (
            filters.amount_min_usd <= order.amount_usd <= filters.amount_max_usd
        ):
            return False
        if filters.created_from is not None and not (
            filters.created_from <= order.created_at <= filters.created_to
        ):
            return False
        return filters.order_status is None or order.status == filters.order_status

    def _item(self, *, order: Any, user: Any, business: Any, tickets: list[Any], filters: CandidateFilters) -> dict[str, Any]:
        payment_report_present = any(report.order_id == order.id for report in self._orders.payment_reports.values())
        signals = []
        if filters.amount_min_usd is not None:
            signals.append("amount_in_range")
        if filters.created_from is not None:
            signals.append("created_in_window")
        if filters.client_hint:
            signals.append("client_hint_match")
        if filters.business_hint:
            signals.append("business_hint_match")
        if filters.order_status:
            signals.append("order_status_match")
        if tickets:
            signals.append("support_ticket_related")
        if payment_report_present:
            signals.append("payment_report_present")
        return {
            "type": "order_candidate",
            "order_id": order.id,
            "public_order_code": order.public_order_code,
            "status": order.status,
            "amount_usd": str(order.amount_usd),
            "created_at": order.created_at.isoformat(),
            "updated_at": order.updated_at.isoformat(),
            "business": {
                "business_id": business.id,
                "name": business.business_name,
                "status": business.verification_status,
                "action_route": f"admin://business/{business.id}",
            },
            "client": {
                "user_id": user.id,
                "display_name": _display_name(user),
                "telegram_hint": mask_telegram_id(user.telegram_id),
                "action_route": f"admin://user/{user.id}",
            },
            "signals": sorted(signals),
            "payment_report_present": payment_report_present,
            "support_ticket_count": len(tickets),
            "case_file_route": f"admin://case-file/order/{order.id}",
            "order_route": f"admin://order/{order.id}",
        }


class PostgresAdminInvestigationCandidatesRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    @staticmethod
    def _visibility_sql(visibility: dict[str, Any], params: list[Any], *, alias: str = "st") -> str:
        if visibility["mode"] in {"admin", "all_orders"}:
            return "true"
        clauses: list[str] = []
        for rule in visibility["ticket_rules"]:
            if rule["permission"] == "view_assigned_support_tickets" and rule["scope"] == "assigned_only":
                clauses.append(f"{alias}.assigned_support_user_id = %s")
                params.append(visibility["user_id"])
            elif rule["permission"] == "view_support_queue" and rule["scope"] == "queue_scope":
                if rule["scope_value"] is None:
                    clauses.append("true")
                else:
                    clauses.append(f"{alias}.scope = %s")
                    params.append(rule["scope_value"])
            elif rule["permission"] == "view_support_queue" and rule["scope"] == "category_scope":
                clauses.append(f"{alias}.category = %s")
                params.append(rule["scope_value"])
        return f"({' or '.join(clauses)})" if clauses else "false"

    def search(
        self,
        *,
        filters: CandidateFilters,
        visibility: dict[str, Any],
        position: dict[str, str] | None,
        limit: int,
    ) -> tuple[list[dict[str, Any]], dict[str, str] | None]:
        where_params: list[Any] = []
        where = ["true"]
        if filters.client_hint:
            like = f"%{_escape_like_literal(filters.client_hint)}%"
            digits = compact_digits(filters.client_hint)
            client_clauses = [
                "lower(u.id::text) like %s escape E'\\\\'",
                "lower(coalesce(u.username, '')) like %s escape E'\\\\'",
                "lower(coalesce(u.first_name, '')) like %s escape E'\\\\'",
                "lower(coalesce(u.last_name, '')) like %s escape E'\\\\'",
                "lower(o.public_order_code) like %s escape E'\\\\'",
            ]
            where_params.extend([like, like, like, like, like])
            if digits:
                client_clauses.extend(
                    [
                        "regexp_replace(coalesce(u.phone, ''), '[^0-9]', '', 'g') like %s escape E'\\\\'",
                        "regexp_replace(coalesce(u.telegram_id::text, ''), '[^0-9]', '', 'g') like %s escape E'\\\\'",
                    ]
                )
                where_params.extend([f"%{digits}%", f"%{digits}%"])
            where.append(f"({' or '.join(client_clauses)})")
        if filters.business_hint:
            like = f"%{_escape_like_literal(filters.business_hint)}%"
            where.append(
                """
                (
                    lower(b.id::text) like %s escape E'\\\\'
                    or lower(b.business_name) like %s escape E'\\\\'
                    or lower(coalesce(b.referral_code, '')) like %s escape E'\\\\'
                    or lower(o.business_name_snapshot) like %s escape E'\\\\'
                )
                """
            )
            where_params.extend([like, like, like, like])
        if filters.amount_min_usd is not None:
            where.append("o.amount_usd between %s and %s")
            where_params.extend([filters.amount_min_usd, filters.amount_max_usd])
        if filters.created_from is not None:
            where.append("o.created_at between %s and %s")
            where_params.extend([filters.created_from, filters.created_to])
        if filters.order_status:
            where.append("o.status = %s")
            where_params.append(filters.order_status)

        visible_params: list[Any] = []
        visible_sql = self._visibility_sql(visibility, visible_params)
        status_sql = "true"
        if filters.support_status_group == "active":
            status_sql = "st.status = any(%s)"
            visible_params.append(sorted(ACTIVE_SUPPORT_STATUSES))
        elif filters.support_status_group == "archived":
            status_sql = "st.status = any(%s)"
            visible_params.append(sorted(ARCHIVED_SUPPORT_STATUSES))
        if visibility["mode"] == "ticket_scope" or filters.support_status_group != "all":
            where.append(
                f"""
                exists (
                    select 1 from support_tickets st
                    where st.order_id = o.id and {visible_sql} and {status_sql}
                )
                """
            )
            where_params.extend(visible_params)
        if position is not None:
            where.append("(o.created_at, o.id) < (%s, %s::uuid)")
            where_params.extend([datetime.fromisoformat(position["at"]), position["id"]])

        count_params: list[Any] = []
        count_visibility = self._visibility_sql(visibility, count_params)
        params = [*count_params, *where_params, limit + 1]
        query = f"""
            select
                o.id as order_id, o.public_order_code, o.status, o.amount_usd,
                o.created_at, o.updated_at,
                b.id as business_id, b.business_name, b.verification_status,
                u.id as user_id, u.username, u.first_name, u.last_name, u.telegram_id,
                exists(select 1 from payment_reports pr where pr.order_id = o.id) as payment_report_present,
                (
                    select count(*) from support_tickets st_count
                    where st_count.order_id = o.id and {count_visibility.replace('st.', 'st_count.')}
                ) as support_ticket_count
            from orders o
            join businesses b on b.id = o.business_id
            join users u on u.id = o.remitter_user_id
            where {' and '.join(where)}
            order by o.created_at desc, o.id desc
            limit %s
        """
        with pooled_connect(self._database_url) as conn:
            rows = conn.execute(query, params).fetchall()
        has_more = len(rows) > limit
        page = rows[:limit]
        items = [self._row_item(row=row, filters=filters) for row in page]
        next_position = (
            {"at": page[-1]["created_at"].isoformat(), "id": str(page[-1]["order_id"])}
            if has_more and page
            else None
        )
        return items, next_position

    @staticmethod
    def _row_item(*, row: dict[str, Any], filters: CandidateFilters) -> dict[str, Any]:
        signals = []
        if filters.amount_min_usd is not None:
            signals.append("amount_in_range")
        if filters.created_from is not None:
            signals.append("created_in_window")
        if filters.client_hint:
            signals.append("client_hint_match")
        if filters.business_hint:
            signals.append("business_hint_match")
        if filters.order_status:
            signals.append("order_status_match")
        if int(row["support_ticket_count"]) > 0:
            signals.append("support_ticket_related")
        if row["payment_report_present"]:
            signals.append("payment_report_present")
        display_name = " ".join(part for part in (row.get("first_name"), row.get("last_name")) if part)
        return {
            "type": "order_candidate",
            "order_id": str(row["order_id"]),
            "public_order_code": row["public_order_code"],
            "status": row["status"],
            "amount_usd": str(Decimal(row["amount_usd"])),
            "created_at": row["created_at"].isoformat(),
            "updated_at": row["updated_at"].isoformat(),
            "business": {
                "business_id": str(row["business_id"]),
                "name": row["business_name"],
                "status": row["verification_status"],
                "action_route": f"admin://business/{row['business_id']}",
            },
            "client": {
                "user_id": str(row["user_id"]),
                "display_name": display_name or row.get("username") or "Cliente",
                "telegram_hint": mask_telegram_id(row.get("telegram_id")),
                "action_route": f"admin://user/{row['user_id']}",
            },
            "signals": sorted(signals),
            "payment_report_present": bool(row["payment_report_present"]),
            "support_ticket_count": int(row["support_ticket_count"]),
            "case_file_route": f"admin://case-file/order/{row['order_id']}",
            "order_route": f"admin://order/{row['order_id']}",
        }
