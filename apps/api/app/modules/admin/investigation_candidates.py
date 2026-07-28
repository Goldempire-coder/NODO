from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from app.core.errors import ApiError
from app.modules.admin.investigation import query_fingerprint
from app.modules.admin.policy import require_admin_read
from app.modules.orders.models import ORDER_STATUSES
from app.modules.users.models import UserRecord


SUPPORT_STATUS_GROUPS = {"all", "active", "archived"}
DISCLAIMER = "Resultados candidatos. Verifica evidencia antes de decidir."
MAX_DATE_WINDOW_DAYS = 31
CURSOR_MAX_AGE_SECONDS = 1800


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone_required")
    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class CandidateFilters:
    client_hint: str | None
    business_hint: str | None
    amount_min_usd: Decimal | None
    amount_max_usd: Decimal | None
    created_from: datetime | None
    created_to: datetime | None
    order_status: str | None
    support_status_group: str

    def cursor_fingerprint(self) -> str:
        payload = {
            "client_hint_hash": query_fingerprint(self.client_hint) if self.client_hint else None,
            "business_hint_hash": query_fingerprint(self.business_hint) if self.business_hint else None,
            "amount_min_usd": str(self.amount_min_usd) if self.amount_min_usd is not None else None,
            "amount_max_usd": str(self.amount_max_usd) if self.amount_max_usd is not None else None,
            "created_from": self.created_from.isoformat() if self.created_from else None,
            "created_to": self.created_to.isoformat() if self.created_to else None,
            "order_status": self.order_status,
            "support_status_group": self.support_status_group,
        }
        return hashlib.sha256(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")).hexdigest()


def _clean_hint(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    return cleaned or None


def _amount_pair(minimum: str | None, maximum: str | None) -> tuple[Decimal | None, Decimal | None]:
    if (minimum is None) != (maximum is None):
        raise ApiError("ADMIN_INVESTIGATION_AMOUNT_RANGE_INVALID", status_code=400)
    if minimum is None:
        return None, None
    try:
        low = Decimal(minimum)
        high = Decimal(maximum or "")
    except (InvalidOperation, ValueError) as exc:
        raise ApiError("ADMIN_INVESTIGATION_AMOUNT_RANGE_INVALID", status_code=400) from exc
    if not low.is_finite() or not high.is_finite() or low <= 0 or high <= 0 or low > high:
        raise ApiError("ADMIN_INVESTIGATION_AMOUNT_RANGE_INVALID", status_code=400)
    return low, high


def _date_pair(start: str | None, end: str | None) -> tuple[datetime | None, datetime | None]:
    if (start is None) != (end is None):
        raise ApiError("ADMIN_INVESTIGATION_DATE_RANGE_INVALID", status_code=400)
    if start is None:
        return None, None
    try:
        low = _parse_datetime(start)
        high = _parse_datetime(end or "")
    except (TypeError, ValueError) as exc:
        raise ApiError("ADMIN_INVESTIGATION_DATE_RANGE_INVALID", status_code=400) from exc
    if low > high or (high - low).total_seconds() > MAX_DATE_WINDOW_DAYS * 86400:
        raise ApiError("ADMIN_INVESTIGATION_DATE_RANGE_INVALID", status_code=400)
    return low, high


def normalize_candidate_filters(
    *,
    client_hint: str | None,
    business_hint: str | None,
    amount_min_usd: str | None,
    amount_max_usd: str | None,
    created_from: str | None,
    created_to: str | None,
    order_status: str | None,
    support_status_group: str,
) -> CandidateFilters:
    client = _clean_hint(client_hint)
    business = _clean_hint(business_hint)
    if (client and len(client) < 3) or (business and len(business) < 3):
        raise ApiError("ADMIN_INVESTIGATION_FILTER_REQUIRED", status_code=400)
    amounts = _amount_pair(amount_min_usd, amount_max_usd)
    dates = _date_pair(created_from, created_to)
    normalized_status = order_status.strip().lower() if order_status else None
    if normalized_status and normalized_status not in ORDER_STATUSES:
        raise ApiError("VALIDATION_ERROR", status_code=422)
    normalized_support = support_status_group.strip().lower()
    if normalized_support not in SUPPORT_STATUS_GROUPS:
        raise ApiError("VALIDATION_ERROR", status_code=422)
    strong_count = sum(
        (
            client is not None,
            business is not None,
            amounts[0] is not None,
            dates[0] is not None,
            normalized_status is not None,
        )
    )
    if strong_count < 2:
        raise ApiError("ADMIN_INVESTIGATION_FILTER_REQUIRED", status_code=400)
    return CandidateFilters(
        client_hint=client,
        business_hint=business,
        amount_min_usd=amounts[0],
        amount_max_usd=amounts[1],
        created_from=dates[0],
        created_to=dates[1],
        order_status=normalized_status,
        support_status_group=normalized_support,
    )


class AdminInvestigationCandidatesService:
    def __init__(self, *, settings, repository, staff_repository, audit_writer, rate_limiter) -> None:  # type: ignore[no-untyped-def]
        self._settings = settings
        self._repository = repository
        self._staff = staff_repository
        self._audit = audit_writer
        self._rate = rate_limiter
        if not settings.jwt_secret:
            raise RuntimeError("admin_investigation_cursor_secret_unavailable")
        self._cursor_secret = settings.jwt_secret.encode("utf-8")

    def _rate_limit(self, user: UserRecord) -> None:
        if not self._rate.allow(
            f"admin:investigation_candidates:{user.id}",
            max_attempts=self._settings.business_rate_limit_max_attempts,
            window_seconds=self._settings.business_rate_limit_window_seconds,
        ):
            raise ApiError("RATE_LIMITED", status_code=429)

    def _visibility(self, user: UserRecord) -> dict[str, Any]:
        if user.role in {"admin", "super_admin"}:
            return {"mode": "admin"}
        profile = self._staff.get_active_profile_for_user(user.id) if self._staff is not None else None
        if profile is None:
            raise ApiError("FORBIDDEN", status_code=403)
        permissions = self._staff.list_active_permissions_for_user(user.id)
        if any(item.permission == "view_orders_masked" for item in permissions):
            return {"mode": "all_orders"}
        rule_values = {
            (item.permission, item.scope, item.scope_value)
            for item in permissions
            if item.permission in {"view_support_queue", "view_assigned_support_tickets"}
        }
        ticket_rules = [
            {"permission": permission, "scope": scope, "scope_value": scope_value}
            for permission, scope, scope_value in sorted(
                rule_values,
                key=lambda value: (value[0], value[1], value[2] is not None, value[2] or ""),
            )
        ]
        if not ticket_rules:
            raise ApiError("FORBIDDEN", status_code=403)
        return {"mode": "ticket_scope", "user_id": user.id, "ticket_rules": ticket_rules}

    @staticmethod
    def _visibility_fingerprint(visibility: dict[str, Any]) -> str:
        return hashlib.sha256(
            json.dumps(visibility, separators=(",", ":"), sort_keys=True).encode("utf-8")
        ).hexdigest()

    def _encode_cursor(
        self,
        *,
        filters: CandidateFilters,
        user: UserRecord,
        visibility: dict[str, Any],
        position: dict[str, str] | None,
    ) -> str | None:
        if position is None:
            return None
        payload = {
            "v": 1,
            "filter": filters.cursor_fingerprint(),
            "actor": user.id,
            "role": user.role,
            "visibility": self._visibility_fingerprint(visibility),
            "issued_at": int(time.time()),
            "position": position,
        }
        encoded = _b64encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))
        signature = _b64encode(hmac.new(self._cursor_secret, encoded.encode("ascii"), hashlib.sha256).digest())
        return f"{encoded}.{signature}"

    def _decode_cursor(
        self,
        cursor: str | None,
        *,
        filters: CandidateFilters,
        user: UserRecord,
        visibility: dict[str, Any],
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
                or payload.get("filter") != filters.cursor_fingerprint()
                or payload.get("actor") != user.id
                or payload.get("role") != user.role
                or payload.get("visibility") != self._visibility_fingerprint(visibility)
                or not isinstance(payload.get("issued_at"), int)
                or payload["issued_at"] < int(time.time()) - CURSOR_MAX_AGE_SECONDS
                or payload["issued_at"] > int(time.time()) + 60
            ):
                raise ValueError("scope")
            position = payload.get("position")
            if not isinstance(position, dict) or not isinstance(position.get("at"), str) or not isinstance(position.get("id"), str):
                raise ValueError("position")
            _parse_datetime(position["at"])
            return {"at": position["at"], "id": position["id"]}
        except (ValueError, TypeError, KeyError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
            raise ApiError("ADMIN_INVESTIGATION_CURSOR_INVALID", status_code=400) from exc

    def search(
        self,
        *,
        user: UserRecord,
        client_hint: str | None,
        business_hint: str | None,
        amount_min_usd: str | None,
        amount_max_usd: str | None,
        created_from: str | None,
        created_to: str | None,
        order_status: str | None,
        support_status_group: str,
        cursor: str | None,
        limit: int,
        request_id: str,
    ) -> dict[str, Any]:
        require_admin_read(user)
        filters = normalize_candidate_filters(
            client_hint=client_hint,
            business_hint=business_hint,
            amount_min_usd=amount_min_usd,
            amount_max_usd=amount_max_usd,
            created_from=created_from,
            created_to=created_to,
            order_status=order_status,
            support_status_group=support_status_group,
        )
        visibility = self._visibility(user)
        self._rate_limit(user)
        position = self._decode_cursor(cursor, filters=filters, user=user, visibility=visibility)
        items, next_position = self._repository.search(
            filters=filters,
            visibility=visibility,
            position=position,
            limit=limit,
        )
        next_cursor = self._encode_cursor(
            filters=filters,
            user=user,
            visibility=visibility,
            position=next_position,
        )
        self._audit.write(
            event_type="admin_investigation_candidates_searched",
            actor_user_id=user.id,
            actor_role=user.role,
            resource_type="admin_investigation",
            resource_id=None,
            request_id=request_id,
            metadata_json={
                "client_hint_present": filters.client_hint is not None,
                "client_hint_hash": query_fingerprint(filters.client_hint) if filters.client_hint else None,
                "business_hint_present": filters.business_hint is not None,
                "business_hint_hash": query_fingerprint(filters.business_hint) if filters.business_hint else None,
                "amount_range": (
                    [str(filters.amount_min_usd), str(filters.amount_max_usd)]
                    if filters.amount_min_usd is not None
                    else None
                ),
                "date_range": (
                    [filters.created_from.isoformat(), filters.created_to.isoformat()]
                    if filters.created_from is not None and filters.created_to is not None
                    else None
                ),
                "order_status": filters.order_status,
                "support_status_group": filters.support_status_group,
                "result_count": len(items),
                "truncated": next_cursor is not None,
                "request_id": request_id,
            },
        )
        return {
            "items": items,
            "next_cursor": next_cursor,
            "truncated": next_cursor is not None,
            "disclaimer": DISCLAIMER,
        }
