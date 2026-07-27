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


class InMemoryAdminInvestigationMixin:
    def operational_search(self, *, query: str, limit: int, full_sensitive: bool) -> dict[str, Any]:
        needle = query.strip().lower()
        digits = compact_digits(query)
        groups = empty_investigation_groups()
        matched_user_ids: set[str] = set()
        matched_business_ids: set[str] = set()
        matched_order_ids: set[str] = set()

        for user in sorted(getattr(self._users, "_users_by_id", {}).values(), key=lambda item: item.created_at, reverse=True):
            matches: list[str] = []
            if contains_text(user.id, needle):
                matches.append("user_id")
            if contains_text(user.username, needle):
                matches.append("username")
            if contains_text(user.first_name, needle) or contains_text(user.last_name, needle):
                matches.append("nombre")
            if contains_digits(user.phone, digits):
                matches.append("telefono")
            if contains_digits(user.telegram_id, digits):
                matches.append("telegram_id")
            if not matches:
                continue
            matched_user_ids.add(user.id)
            payload = admin_user_payload(user.__dict__, full_sensitive=full_sensitive)
            append_group_item(
                groups,
                "users",
                investigation_item(
                    item_type="user",
                    item_id=user.id,
                    title=payload.get("username") or payload.get("first_name") or "Cliente",
                    subtitle=f"{payload.get('role')} - {payload.get('status')} - {payload.get('phone_masked') or payload.get('telegram_id_masked') or 'sin contacto'}",
                    matched_on=matches,
                    action_route=f"admin://user/{user.id}",
                    status=payload.get("status"),
                    created_at=payload.get("created_at"),
                    context={"role": payload.get("role"), "phone_masked": payload.get("phone_masked"), "telegram_id_masked": payload.get("telegram_id_masked")},
                ),
                limit=limit,
            )

        for business in sorted(getattr(self._businesses, "businesses", {}).values(), key=lambda item: item.created_at, reverse=True):
            matches = []
            if contains_text(business.id, needle):
                matches.append("business_id")
            if contains_text(business.owner_user_id, needle):
                matches.append("owner_user_id")
            if contains_text(business.business_name, needle):
                matches.append("nombre_negocio")
            if contains_text(business.rif, needle):
                matches.append("rif")
            if contains_digits(business.phone, digits):
                matches.append("telefono_negocio")
            if contains_text(business.referral_code, needle):
                matches.append("codigo_referencia")
            if not matches:
                continue
            matched_business_ids.add(business.id)
            append_group_item(
                groups,
                "businesses",
                investigation_item(
                    item_type="business",
                    item_id=business.id,
                    title=business.business_name,
                    subtitle=f"{business.verification_status} - {mask_phone(business.phone) or 'sin telefono'}",
                    matched_on=matches,
                    action_route=f"admin://business/{business.id}",
                    status=business.verification_status,
                    reference=business.referral_code,
                    created_at=business.created_at.isoformat(),
                    context={"owner_user_id": business.owner_user_id, "phone_masked": mask_phone(business.phone)},
                ),
                limit=limit,
            )

        for intake in sorted(getattr(getattr(self, "_business_intake", None), "intakes", {}).values(), key=lambda item: item.created_at, reverse=True):
            matches = []
            if contains_text(intake.id, needle):
                matches.append("intake_id")
            if contains_digits(intake.telegram_user_id, digits):
                matches.append("telegram_id")
            if contains_digits(intake.contact_phone, digits) or contains_digits(intake.business_phone, digits):
                matches.append("telefono")
            if contains_text(intake.business_name, needle):
                matches.append("nombre_negocio")
            if contains_text(intake.business_tax_id, needle):
                matches.append("rif")
            if contains_text(intake.referral_code, needle):
                matches.append("codigo_referencia")
            if contains_text(intake.created_business_id, needle):
                matches.append("negocio_creado")
            if not matches:
                continue
            if intake.created_business_id:
                matched_business_ids.add(intake.created_business_id)
            append_group_item(
                groups,
                "business_intakes",
                investigation_item(
                    item_type="business_intake",
                    item_id=intake.id,
                    title=intake.business_name or "Solicitud de negocio",
                    subtitle=f"{intake.status} - {mask_phone(intake.contact_phone or intake.business_phone) or 'sin telefono'}",
                    matched_on=matches,
                    action_route=f"admin://business-intake/{intake.id}",
                    status=intake.status,
                    reference=intake.referral_code,
                    created_at=intake.created_at.isoformat(),
                    context={"created_business_id": intake.created_business_id, "phone_masked": mask_phone(intake.contact_phone or intake.business_phone)},
                ),
                limit=limit,
            )

        for order in sorted(getattr(self._orders, "orders", {}).values(), key=lambda item: item.created_at, reverse=True):
            matches = []
            if contains_text(order.id, needle):
                matches.append("order_id")
            if contains_text(order.public_order_code, needle):
                matches.append("codigo_orden")
            if contains_text(order.business_id, needle):
                matches.append("business_id")
            if contains_text(order.remitter_user_id, needle):
                matches.append("cliente_id")
            if contains_text(order.business_name_snapshot, needle):
                matches.append("nombre_negocio")
            if contains_text(str(order.amount_usd), needle):
                matches.append("monto")
            if order.remitter_user_id in matched_user_ids:
                matches.append("cliente_relacionado")
            if order.business_id in matched_business_ids:
                matches.append("negocio_relacionado")
            if not matches:
                continue
            matched_order_ids.add(order.id)
            append_group_item(
                groups,
                "orders",
                investigation_item(
                    item_type="order",
                    item_id=order.id,
                    title=order.public_order_code,
                    subtitle=f"{order.business_name_snapshot} - USD {order.amount_usd}",
                    matched_on=matches,
                    action_route=f"admin://order/{order.id}",
                    status=order.status,
                    reference=order.public_order_code,
                    created_at=order.created_at.isoformat(),
                    context={"business_id": order.business_id, "remitter_user_id": order.remitter_user_id, "amount_usd": str(order.amount_usd)},
                ),
                limit=limit,
            )

        for ticket in sorted(getattr(getattr(self, "_support", None), "tickets", {}).values(), key=lambda item: item.updated_at, reverse=True):
            matches = []
            if contains_text(ticket.id, needle):
                matches.append("ticket_id")
            if contains_text(ticket.subject, needle):
                matches.append("asunto")
            if contains_text(ticket.requester_user_id, needle):
                matches.append("solicitante_id")
            if contains_text(ticket.business_id, needle):
                matches.append("business_id")
            if contains_text(ticket.order_id, needle):
                matches.append("order_id")
            if ticket.requester_user_id in matched_user_ids:
                matches.append("cliente_relacionado")
            if ticket.business_id in matched_business_ids:
                matches.append("negocio_relacionado")
            if ticket.order_id in matched_order_ids:
                matches.append("orden_relacionada")
            if not matches:
                continue
            append_group_item(
                groups,
                "support_tickets",
                investigation_item(
                    item_type="support_ticket",
                    item_id=ticket.id,
                    title=ticket.subject,
                    subtitle=f"{ticket.requester_role} - {ticket.scope}",
                    matched_on=matches,
                    action_route=f"admin://support-ticket/{ticket.id}",
                    status=ticket.status,
                    reference=ticket.order_id or ticket.business_id,
                    created_at=ticket.created_at.isoformat(),
                    context={"business_id": ticket.business_id, "order_id": ticket.order_id, "requester_user_id": ticket.requester_user_id},
                ),
                limit=limit,
            )

        return {"groups": groups, "result_counts": investigation_result_counts(groups)}
