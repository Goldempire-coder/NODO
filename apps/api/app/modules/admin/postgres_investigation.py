from __future__ import annotations

from typing import Any

from app.modules.admin.investigation import (
    append_group_item,
    compact_digits,
    contains_digits,
    contains_text,
    empty_investigation_groups,
    investigation_item,
    investigation_result_counts,
)
from app.modules.admin.user_presenters import admin_user_payload, mask_phone


def _like(query: str) -> str:
    return f"%{query.strip()}%"


def _digits_like(query: str) -> str:
    return f"%{compact_digits(query)}%"


def _in_condition(column: str, values: set[str], params: list[Any]) -> str | None:
    if not values:
        return None
    params.extend(sorted(values))
    placeholders = ", ".join(["%s"] * len(values))
    return f"{column} in ({placeholders})"


class PostgresAdminInvestigationMixin:
    def operational_search(self, *, query: str, limit: int, full_sensitive: bool) -> dict[str, Any]:
        needle = query.strip().lower()
        digits = compact_digits(query)
        text_like = _like(query)
        digit_like = _digits_like(query)
        groups = empty_investigation_groups()
        matched_user_ids: set[str] = set()
        matched_business_ids: set[str] = set()
        matched_order_ids: set[str] = set()

        with self._connect() as conn:  # type: ignore[attr-defined]
            user_conditions = [
                "id::text ilike %s",
                "lower(coalesce(username, '')) like lower(%s)",
                "lower(coalesce(first_name, '')) like lower(%s)",
                "lower(coalesce(last_name, '')) like lower(%s)",
            ]
            user_params: list[Any] = [text_like, text_like, text_like, text_like]
            if digits:
                user_conditions.extend(["regexp_replace(coalesce(phone, ''), '[^0-9]', '', 'g') like %s", "coalesce(telegram_id::text, '') like %s"])
                user_params.extend([digit_like, digit_like])
            user_params.append(limit)
            users = conn.execute(
                f"select * from users where {' or '.join(user_conditions)} order by created_at desc limit %s",
                user_params,
            ).fetchall()

            for row in users:
                payload = admin_user_payload(dict(row), full_sensitive=full_sensitive)
                matches = []
                if contains_text(payload["id"], needle):
                    matches.append("user_id")
                if contains_text(payload.get("username"), needle):
                    matches.append("username")
                if contains_text(payload.get("first_name"), needle) or contains_text(payload.get("last_name"), needle):
                    matches.append("nombre")
                if contains_digits(row.get("phone"), digits):
                    matches.append("telefono")
                if contains_digits(row.get("telegram_id"), digits):
                    matches.append("telegram_id")
                matched_user_ids.add(payload["id"])
                append_group_item(
                    groups,
                    "users",
                    investigation_item(
                        item_type="user",
                        item_id=payload["id"],
                        title=payload.get("username") or payload.get("first_name") or "Cliente",
                        subtitle=f"{payload.get('role')} - {payload.get('status')} - {payload.get('phone_masked') or payload.get('telegram_id_masked') or 'sin contacto'}",
                        matched_on=matches,
                        action_route=f"admin://user/{payload['id']}",
                        status=payload.get("status"),
                        created_at=payload.get("created_at"),
                        context={"role": payload.get("role"), "phone_masked": payload.get("phone_masked"), "telegram_id_masked": payload.get("telegram_id_masked")},
                    ),
                    limit=limit,
                )

            business_conditions = [
                "id::text ilike %s",
                "owner_user_id::text ilike %s",
                "lower(coalesce(business_name, '')) like lower(%s)",
                "lower(coalesce(rif, '')) like lower(%s)",
                "lower(coalesce(referral_code, '')) like lower(%s)",
            ]
            business_params: list[Any] = [text_like, text_like, text_like, text_like, text_like]
            related_owner_condition = _in_condition("owner_user_id::text", matched_user_ids, business_params)
            if related_owner_condition:
                business_conditions.append(related_owner_condition)
            if digits:
                business_conditions.append("regexp_replace(coalesce(phone, ''), '[^0-9]', '', 'g') like %s")
                business_params.append(digit_like)
            business_params.append(limit)
            businesses = conn.execute(
                f"""
                select id, owner_user_id, business_name, rif, phone, verification_status, referral_code, created_at
                from businesses
                where {' or '.join(business_conditions)}
                order by created_at desc
                limit %s
                """,
                business_params,
            ).fetchall()

            for row in businesses:
                business_id = str(row["id"])
                matches = []
                if contains_text(business_id, needle):
                    matches.append("business_id")
                if contains_text(row["owner_user_id"], needle) or str(row["owner_user_id"]) in matched_user_ids:
                    matches.append("owner_user_id")
                if contains_text(row["business_name"], needle):
                    matches.append("nombre_negocio")
                if contains_text(row["rif"], needle):
                    matches.append("rif")
                if contains_digits(row["phone"], digits):
                    matches.append("telefono_negocio")
                if contains_text(row["referral_code"], needle):
                    matches.append("codigo_referencia")
                matched_business_ids.add(business_id)
                append_group_item(
                    groups,
                    "businesses",
                    investigation_item(
                        item_type="business",
                        item_id=business_id,
                        title=row["business_name"],
                        subtitle=f"{row['verification_status']} - {mask_phone(row['phone']) or 'sin telefono'}",
                        matched_on=matches,
                        action_route=f"admin://business/{business_id}",
                        status=row["verification_status"],
                        reference=row["referral_code"],
                        created_at=row["created_at"].isoformat(),
                        context={"owner_user_id": str(row["owner_user_id"]), "phone_masked": mask_phone(row["phone"])},
                    ),
                    limit=limit,
                )

            intake_conditions = [
                "id::text ilike %s",
                "lower(coalesce(business_name, '')) like lower(%s)",
                "lower(coalesce(business_tax_id, '')) like lower(%s)",
                "lower(coalesce(referral_code, '')) like lower(%s)",
                "created_business_id::text ilike %s",
            ]
            intake_params: list[Any] = [text_like, text_like, text_like, text_like, text_like]
            related_business_condition = _in_condition("created_business_id::text", matched_business_ids, intake_params)
            if related_business_condition:
                intake_conditions.append(related_business_condition)
            if digits:
                intake_conditions.extend(
                    [
                        "coalesce(telegram_user_id::text, '') like %s",
                        "regexp_replace(coalesce(contact_phone, ''), '[^0-9]', '', 'g') like %s",
                        "regexp_replace(coalesce(business_phone, ''), '[^0-9]', '', 'g') like %s",
                    ]
                )
                intake_params.extend([digit_like, digit_like, digit_like])
            intake_params.append(limit)
            intakes = conn.execute(
                f"""
                select id, telegram_user_id, status, business_name, business_tax_id, contact_phone,
                       business_phone, referral_code, created_business_id, created_at
                from business_intake_requests
                where {' or '.join(intake_conditions)}
                order by created_at desc
                limit %s
                """,
                intake_params,
            ).fetchall()

            for row in intakes:
                intake_id = str(row["id"])
                matches = []
                if contains_text(intake_id, needle):
                    matches.append("intake_id")
                if contains_digits(row["telegram_user_id"], digits):
                    matches.append("telegram_id")
                if contains_digits(row["contact_phone"], digits) or contains_digits(row["business_phone"], digits):
                    matches.append("telefono")
                if contains_text(row["business_name"], needle):
                    matches.append("nombre_negocio")
                if contains_text(row["business_tax_id"], needle):
                    matches.append("rif")
                if contains_text(row["referral_code"], needle):
                    matches.append("codigo_referencia")
                if contains_text(row["created_business_id"], needle):
                    matches.append("negocio_creado")
                if row["created_business_id"]:
                    matched_business_ids.add(str(row["created_business_id"]))
                append_group_item(
                    groups,
                    "business_intakes",
                    investigation_item(
                        item_type="business_intake",
                        item_id=intake_id,
                        title=row["business_name"] or "Solicitud de negocio",
                        subtitle=f"{row['status']} - {mask_phone(row['contact_phone'] or row['business_phone']) or 'sin telefono'}",
                        matched_on=matches,
                        action_route=f"admin://business-intake/{intake_id}",
                        status=row["status"],
                        reference=row["referral_code"],
                        created_at=row["created_at"].isoformat(),
                        context={"created_business_id": str(row["created_business_id"]) if row["created_business_id"] else None, "phone_masked": mask_phone(row["contact_phone"] or row["business_phone"])},
                    ),
                    limit=limit,
                )

            order_conditions = [
                "id::text ilike %s",
                "lower(coalesce(public_order_code, '')) like lower(%s)",
                "business_id::text ilike %s",
                "remitter_user_id::text ilike %s",
                "lower(coalesce(business_name_snapshot, '')) like lower(%s)",
                "amount_usd::text = %s",
            ]
            order_params: list[Any] = [text_like, text_like, text_like, text_like, text_like, query.strip()]
            related_user_condition = _in_condition("remitter_user_id::text", matched_user_ids, order_params)
            related_business_condition = _in_condition("business_id::text", matched_business_ids, order_params)
            if related_user_condition:
                order_conditions.append(related_user_condition)
            if related_business_condition:
                order_conditions.append(related_business_condition)
            order_params.append(limit)
            orders = conn.execute(
                f"""
                select id, public_order_code, status, business_id, remitter_user_id, amount_usd,
                       business_name_snapshot, created_at
                from orders
                where {' or '.join(order_conditions)}
                order by created_at desc
                limit %s
                """,
                order_params,
            ).fetchall()

            for row in orders:
                order_id = str(row["id"])
                business_id = str(row["business_id"])
                remitter_user_id = str(row["remitter_user_id"])
                matches = []
                if contains_text(order_id, needle):
                    matches.append("order_id")
                if contains_text(row["public_order_code"], needle):
                    matches.append("codigo_orden")
                if contains_text(business_id, needle):
                    matches.append("business_id")
                if contains_text(remitter_user_id, needle):
                    matches.append("cliente_id")
                if contains_text(row["business_name_snapshot"], needle):
                    matches.append("nombre_negocio")
                if contains_text(str(row["amount_usd"]), needle):
                    matches.append("monto")
                if remitter_user_id in matched_user_ids:
                    matches.append("cliente_relacionado")
                if business_id in matched_business_ids:
                    matches.append("negocio_relacionado")
                matched_order_ids.add(order_id)
                append_group_item(
                    groups,
                    "orders",
                    investigation_item(
                        item_type="order",
                        item_id=order_id,
                        title=row["public_order_code"],
                        subtitle=f"{row['business_name_snapshot']} - USD {row['amount_usd']}",
                        matched_on=matches,
                        action_route=f"admin://order/{order_id}",
                        status=row["status"],
                        reference=row["public_order_code"],
                        created_at=row["created_at"].isoformat(),
                        context={"business_id": business_id, "remitter_user_id": remitter_user_id, "amount_usd": str(row["amount_usd"])},
                    ),
                    limit=limit,
                )

            ticket_conditions = [
                "id::text ilike %s",
                "lower(coalesce(subject, '')) like lower(%s)",
                "requester_user_id::text ilike %s",
                "business_id::text ilike %s",
                "order_id::text ilike %s",
            ]
            ticket_params: list[Any] = [text_like, text_like, text_like, text_like, text_like]
            related_requester_condition = _in_condition("requester_user_id::text", matched_user_ids, ticket_params)
            related_ticket_business_condition = _in_condition("business_id::text", matched_business_ids, ticket_params)
            related_order_condition = _in_condition("order_id::text", matched_order_ids, ticket_params)
            for condition in (related_requester_condition, related_ticket_business_condition, related_order_condition):
                if condition:
                    ticket_conditions.append(condition)
            ticket_params.append(limit)
            tickets = conn.execute(
                f"""
                select id, requester_user_id, requester_role, scope, status, subject,
                       business_id, order_id, created_at, updated_at
                from support_tickets
                where {' or '.join(ticket_conditions)}
                order by updated_at desc
                limit %s
                """,
                ticket_params,
            ).fetchall()

        for row in tickets:
            ticket_id = str(row["id"])
            requester_user_id = str(row["requester_user_id"])
            business_id = str(row["business_id"]) if row["business_id"] else None
            order_id = str(row["order_id"]) if row["order_id"] else None
            matches = []
            if contains_text(ticket_id, needle):
                matches.append("ticket_id")
            if contains_text(row["subject"], needle):
                matches.append("asunto")
            if contains_text(requester_user_id, needle):
                matches.append("solicitante_id")
            if contains_text(business_id, needle):
                matches.append("business_id")
            if contains_text(order_id, needle):
                matches.append("order_id")
            if requester_user_id in matched_user_ids:
                matches.append("cliente_relacionado")
            if business_id in matched_business_ids:
                matches.append("negocio_relacionado")
            if order_id in matched_order_ids:
                matches.append("orden_relacionada")
            append_group_item(
                groups,
                "support_tickets",
                investigation_item(
                    item_type="support_ticket",
                    item_id=ticket_id,
                    title=row["subject"],
                    subtitle=f"{row['requester_role']} - {row['scope']}",
                    matched_on=matches,
                    action_route=f"admin://support-ticket/{ticket_id}",
                    status=row["status"],
                    reference=order_id or business_id,
                    created_at=row["created_at"].isoformat(),
                    context={"business_id": business_id, "order_id": order_id, "requester_user_id": requester_user_id},
                ),
                limit=limit,
            )

        return {"groups": groups, "result_counts": investigation_result_counts(groups)}
