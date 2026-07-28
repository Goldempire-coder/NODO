from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import logging
from datetime import datetime
from types import SimpleNamespace
from typing import Any, Callable
from uuid import UUID

from app.core.errors import ApiError
from app.modules.admin.policy import require_admin_read
from app.modules.staff.service import has_staff_permission
from app.modules.support.models import ARCHIVED_SUPPORT_STATUSES
from app.modules.users.models import UserRecord


logger = logging.getLogger(__name__)

ANCHOR_TYPES = {"user", "business", "business_intake", "order", "support_ticket"}
SECTIONS = {"all", "orders", "support_tickets", "business_intakes", "evidence", "timeline"}
DISCLAIMER = "Ficha de investigacion. No determina responsabilidad ni garantiza recuperacion."


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _require_uuid(value: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError("ADMIN_CASE_FILE_ANCHOR_INVALID", status_code=404) from exc


def _ticket_object(ticket: Any) -> Any:
    return SimpleNamespace(**ticket) if isinstance(ticket, dict) else ticket


class AdminInvestigationCaseFileService:
    def __init__(self, *, settings, repository, staff_repository, audit_writer, rate_limiter) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._staff = staff_repository
        self._audit = audit_writer
        self._rate = rate_limiter
        if not settings.jwt_secret:
            raise RuntimeError("admin_case_file_cursor_secret_unavailable")
        self._cursor_secret = settings.jwt_secret.encode("utf-8")

    def _rate_limit(self, *, user: UserRecord, anchor_type: str, anchor_id: str) -> None:
        if not self._rate.allow(
            f"admin:case_file:{user.id}:{anchor_type}:{anchor_id}",
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _encode_cursor(
        self,
        *,
        anchor_type: str,
        anchor_id: str,
        section: str,
        include_archived: bool,
        position: dict[str, str] | None,
    ) -> str | None:
        if position is None:
            return None
        payload = {
            "v": 1,
            "anchor_type": anchor_type,
            "anchor_id": anchor_id,
            "section": section,
            "include_archived": include_archived,
            "position": position,
        }
        encoded = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signature = _b64encode(hmac.new(self._cursor_secret, encoded.encode("ascii"), hashlib.sha256).digest())
        return f"{encoded}.{signature}"

    def _decode_cursor(
        self,
        cursor: str | None,
        *,
        anchor_type: str,
        anchor_id: str,
        section: str,
        include_archived: bool,
    ) -> dict[str, str] | None:
        if cursor is None:
            return None
        try:
            encoded, signature = cursor.split(".", 1)
            expected = _b64encode(hmac.new(self._cursor_secret, encoded.encode("ascii"), hashlib.sha256).digest())
            if not hmac.compare_digest(signature, expected):
                raise ValueError("signature")
            payload = json.loads(_b64decode(encoded))
            if (
                payload.get("v") != 1
                or payload.get("anchor_type") != anchor_type
                or payload.get("anchor_id") != anchor_id
                or payload.get("section") != section
                or payload.get("include_archived") is not include_archived
            ):
                raise ValueError("scope")
            position = payload.get("position")
            if not isinstance(position, dict) or not isinstance(position.get("at"), str) or not isinstance(position.get("id"), str):
                raise ValueError("position")
            datetime_value = position["at"]
            datetime.fromisoformat(datetime_value)
            return {"at": datetime_value, "id": position["id"]}
        except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
            raise ApiError("ADMIN_CASE_FILE_CURSOR_INVALID", status_code=400) from exc

    def _support_visibility(self, *, user: UserRecord, context: dict[str, Any]) -> dict[str, set[str]] | None:
        if user.role in {"admin", "super_admin"}:
            return None
        profile = self._staff.get_active_profile_for_user(user.id) if self._staff is not None else None
        if profile is None:
            raise ApiError("ADMIN_CASE_FILE_ANCHOR_NOT_FOUND", status_code=404)

        visible_ticket_ids: set[str] = set()
        visible_ticket_records = []
        for ticket in context["ticket_records"]:
            ticket_object = _ticket_object(ticket)
            if has_staff_permission(self._staff, user=user, permission="view_support_queue", ticket=ticket_object) or has_staff_permission(
                self._staff,
                user=user,
                permission="view_assigned_support_tickets",
                ticket=ticket_object,
            ):
                visible_ticket_ids.add(str(ticket_object.id))
                visible_ticket_records.append(ticket_object)

        all_orders = has_staff_permission(self._staff, user=user, permission="view_orders_masked")
        all_businesses = has_staff_permission(self._staff, user=user, permission="view_businesses_masked")
        all_users = has_staff_permission(self._staff, user=user, permission="view_users_masked")
        visible_order_ids = set(context["order_ids"]) if all_orders else {
            str(ticket.order_id) for ticket in visible_ticket_records if ticket.order_id
        }
        visible_business_ids = set(context["business_ids"]) if all_businesses else {
            str(ticket.business_id) for ticket in visible_ticket_records if ticket.business_id
        }
        visible_user_ids = set(context["user_ids"]) if all_users else {
            str(ticket.requester_user_id) for ticket in visible_ticket_records
        }
        visible_intake_ids = set(context["intake_ids"]) if all_businesses else set()
        visible_ids = {
            "user": visible_user_ids,
            "business": visible_business_ids,
            "business_intake": visible_intake_ids,
            "order": visible_order_ids,
            "support_ticket": visible_ticket_ids,
        }
        if context["anchor_id"] not in visible_ids[context["anchor_type"]]:
            raise ApiError("ADMIN_CASE_FILE_ANCHOR_NOT_FOUND", status_code=404)
        return visible_ids

    def _page_section(
        self,
        *,
        section: str,
        load: Callable[[], tuple[list[dict[str, Any]], dict[str, str] | None, int]],
        anchor_type: str,
        anchor_id: str,
        include_archived: bool,
        request_id: str,
    ) -> dict[str, Any]:
        try:
            items, next_position, total_count = load()
            return {
                "status": "ok",
                "items": items,
                "truncated": next_position is not None,
                "next_cursor": self._encode_cursor(
                    anchor_type=anchor_type,
                    anchor_id=anchor_id,
                    section=section,
                    include_archived=include_archived,
                    position=next_position,
                ),
                "total_count": total_count,
                "error": None,
            }
        except Exception as exc:
            logger.warning(
                "admin_case_file_section_failed",
                extra={
                    "anchor_type": anchor_type,
                    "anchor_id": anchor_id,
                    "section": section,
                    "request_id": request_id,
                    "error_type": type(exc).__name__,
                },
            )
            return {
                "status": "partial_error",
                "items": [],
                "truncated": False,
                "next_cursor": None,
                "total_count": None,
                "error": {"code": "ADMIN_CASE_FILE_SECTION_UNAVAILABLE", "message": "No pudimos cargar esta seccion."},
            }

    def get_case_file(
        self,
        *,
        user: UserRecord,
        anchor_type: str,
        anchor_id: str,
        section: str,
        cursor: str | None,
        limit: int,
        include_archived: bool,
        request_id: str,
    ) -> dict[str, Any]:
        require_admin_read(user)
        if anchor_type not in ANCHOR_TYPES or section not in SECTIONS:
            raise ApiError("ADMIN_CASE_FILE_ANCHOR_INVALID", status_code=404)
        anchor_id = _require_uuid(anchor_id)
        if section == "all" and cursor is not None:
            raise ApiError("ADMIN_CASE_FILE_CURSOR_INVALID", status_code=400)
        self._rate_limit(user=user, anchor_type=anchor_type, anchor_id=anchor_id)
        context = self._repository.resolve_context(anchor_type=anchor_type, anchor_id=anchor_id)
        if context is None:
            raise ApiError("ADMIN_CASE_FILE_ANCHOR_NOT_FOUND", status_code=404)
        visible_ids = self._support_visibility(user=user, context=context)
        section_visible_ids = (
            {
                "user": set(context["user_ids"]),
                "business": set(context["business_ids"]),
                "business_intake": set(context["intake_ids"]),
                "order": set(context["order_ids"]),
                "support_ticket": set(context["ticket_ids"]),
            }
            if visible_ids is None
            else {name: set(values) for name, values in visible_ids.items()}
        )
        if not include_archived:
            section_visible_ids["support_ticket"] -= {
                str(ticket.id if not isinstance(ticket, dict) else ticket["id"])
                for ticket in context["ticket_records"]
                if (ticket.status if not isinstance(ticket, dict) else ticket["status"]) in ARCHIVED_SUPPORT_STATUSES
            }
        position = self._decode_cursor(
            cursor,
            anchor_type=anchor_type,
            anchor_id=anchor_id,
            section=section,
            include_archived=include_archived,
        )
        requested = {"orders", "support_tickets", "business_intakes", "evidence", "timeline"} if section == "all" else {section}
        sections_with_error: list[str] = []

        def not_requested() -> dict[str, Any]:
            return {
                "status": "not_requested",
                "items": [],
                "truncated": False,
                "next_cursor": None,
                "total_count": None,
                "error": None,
            }

        orders = not_requested()
        if "orders" in requested:
            orders = self._page_section(
                section="orders",
                load=lambda: self._repository.page_orders(
                    context,
                    visible_ids=section_visible_ids["order"],
                    position=position if section == "orders" else None,
                    limit=limit,
                ),
                anchor_type=anchor_type,
                anchor_id=anchor_id,
                include_archived=include_archived,
                request_id=request_id,
            )
        support_tickets = not_requested()
        if "support_tickets" in requested:
            support_tickets = self._page_section(
                section="support_tickets",
                load=lambda: self._repository.page_support_tickets(
                    context,
                    visible_ids=section_visible_ids["support_ticket"],
                    include_archived=include_archived,
                    position=position if section == "support_tickets" else None,
                    limit=limit,
                ),
                anchor_type=anchor_type,
                anchor_id=anchor_id,
                include_archived=include_archived,
                request_id=request_id,
            )
        intakes = not_requested()
        if "business_intakes" in requested:
            intakes = self._page_section(
                section="business_intakes",
                load=lambda: self._repository.page_business_intakes(
                    context,
                    visible_ids=section_visible_ids["business_intake"],
                    position=position if section == "business_intakes" else None,
                    limit=limit,
                ),
                anchor_type=anchor_type,
                anchor_id=anchor_id,
                include_archived=include_archived,
                request_id=request_id,
            )
        evidence: dict[str, Any] = {
            "status": "not_requested",
            "payment_report_present": False,
            "chat_evidence_available": False,
            "chat_action_routes": [],
            "documents": [],
            "attachments": [],
            "truncated": False,
            "next_cursor": None,
            "total_count": None,
            "error": None,
        }
        if "evidence" in requested:
            try:
                evidence_data, evidence_next_position, evidence_total = self._repository.evidence_payload(
                    context,
                    visible_ids=section_visible_ids,
                    support_limited=user.role == "support",
                    position=position if section == "evidence" else None,
                    limit=limit,
                )
                evidence = {
                    "status": "ok",
                    **evidence_data,
                    "truncated": evidence_next_position is not None,
                    "next_cursor": self._encode_cursor(
                        anchor_type=anchor_type,
                        anchor_id=anchor_id,
                        section="evidence",
                        include_archived=include_archived,
                        position=evidence_next_position,
                    ),
                    "total_count": evidence_total,
                    "error": None,
                }
            except Exception as exc:
                logger.warning(
                    "admin_case_file_section_failed",
                    extra={
                        "anchor_type": anchor_type,
                        "anchor_id": anchor_id,
                        "section": "evidence",
                        "request_id": request_id,
                        "error_type": type(exc).__name__,
                    },
                )
                evidence = {
                    "status": "partial_error",
                    "payment_report_present": False,
                    "chat_evidence_available": False,
                    "chat_action_routes": [],
                    "documents": [],
                    "attachments": [],
                    "truncated": False,
                    "next_cursor": None,
                    "total_count": None,
                    "error": {"code": "ADMIN_CASE_FILE_SECTION_UNAVAILABLE", "message": "No pudimos cargar esta seccion."},
                }
        timeline = not_requested()
        if "timeline" in requested:
            timeline = self._page_section(
                section="timeline",
                load=lambda: self._repository.page_timeline(
                    context,
                    visible_ids=section_visible_ids,
                    position=position if section == "timeline" else None,
                    limit=limit,
                ),
                anchor_type=anchor_type,
                anchor_id=anchor_id,
                include_archived=include_archived,
                request_id=request_id,
            )
        section_payloads = {
            "orders": orders,
            "support_tickets": support_tickets,
            "business_intakes": intakes,
            "evidence": evidence,
            "timeline": timeline,
        }
        sections_with_error = [
            name for name, payload in section_payloads.items() if payload.get("status") in {"partial_error", "error"}
        ]
        allowed_order_ids = section_visible_ids["order"]
        allowed_ticket_ids = section_visible_ids["support_ticket"]
        allowed_intake_ids = section_visible_ids["business_intake"]
        participants = self._repository.participants_payload(context, allowed_ids=visible_ids)
        checklist = [
            {
                "code": "RELATED_ORDER_PRESENT",
                "label": "Orden relacionada encontrada",
                "status": "present" if allowed_order_ids else "missing",
                "action_route": f"admin://order/{next(iter(sorted(allowed_order_ids)))}" if allowed_order_ids else None,
            },
            {
                "code": "SUPPORT_TICKET_PRESENT",
                "label": "Ticket de soporte relacionado",
                "status": "present" if allowed_ticket_ids else "missing",
                "action_route": f"admin://support-ticket/{next(iter(sorted(allowed_ticket_ids)))}" if allowed_ticket_ids else None,
            },
            {
                "code": "BUSINESS_INTAKE_PRESENT",
                "label": "Solicitud de negocio relacionada",
                "status": "present" if allowed_intake_ids else ("not_authorized" if user.role == "support" else "missing"),
                "action_route": f"admin://business-intake/{next(iter(sorted(allowed_intake_ids)))}" if allowed_intake_ids else None,
            },
            {
                "code": "PAYMENT_REPORT_PRESENT",
                "label": "Reporte de pago relacionado",
                "status": (
                    "present"
                    if evidence["status"] == "ok" and evidence["payment_report_present"]
                    else "missing"
                    if evidence["status"] == "ok"
                    else "not_checked"
                ),
                "action_route": None,
            },
            {
                "code": "CHAT_EVIDENCE_AVAILABLE",
                "label": "Conversacion de orden disponible",
                "status": (
                    "present"
                    if evidence["status"] == "ok" and evidence["chat_evidence_available"]
                    else "missing"
                    if evidence["status"] == "ok"
                    else "not_checked"
                ),
                "action_route": evidence.get("chat_action_routes", [None])[0] if evidence.get("chat_action_routes") else None,
            },
        ]
        counts = {
            "orders": len(allowed_order_ids),
            "support_tickets": len(allowed_ticket_ids),
            "business_intakes": len(allowed_intake_ids),
            "timeline_events": timeline.get("total_count"),
        }
        truncated_sections = [
            name for name, payload in section_payloads.items() if isinstance(payload, dict) and payload.get("truncated") is True
        ]
        self._audit.write(
            event_type="admin_investigation_case_file_viewed",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="admin_investigation_case_file",
            resource_id=anchor_id,
            request_id=request_id,
            metadata_json={
                "anchor_type": anchor_type,
                "anchor_id": anchor_id,
                "counts": counts,
                "section": section,
                "include_archived": include_archived,
                "truncated_sections": truncated_sections,
                "sections_with_error": sections_with_error,
                "request_id": request_id,
            },
        )
        return {
            "anchor": self._repository.anchor_payload(context),
            "summary": {
                "case_title": "Ficha de investigacion",
                "anchor_reason": f"{anchor_type}_anchor",
                "last_activity_at": max(
                    [
                        item.get("updated_at") or item.get("created_at")
                        for payload in (orders, support_tickets, intakes, timeline)
                        for item in payload.get("items", [])
                        if item.get("updated_at") or item.get("created_at")
                    ],
                    default=None,
                ),
                "counts": counts,
            },
            "participants": participants,
            "orders": orders,
            "support_tickets": support_tickets,
            "business_intakes": intakes,
            "evidence": evidence,
            "timeline": timeline,
            "review_checklist": checklist,
            "warnings": [
                {"code": "SECTION_UNAVAILABLE", "section": name, "message": "Una seccion no esta disponible temporalmente."}
                for name in sections_with_error
            ],
            "disclaimer": DISCLAIMER,
        }
