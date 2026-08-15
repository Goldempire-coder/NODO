from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from app.core.errors import ApiError


INTAKE_READINESS_FILTERS = {"all", "ready", "needs_info"}
READY_PRIORITY = 0
NEEDS_INFO_PRIORITY = 1
_CURSOR_VERSION = 1
_MAX_CURSOR_LENGTH = 512


@dataclass(frozen=True)
class IntakeListCursor:
    priority: int
    created_at: datetime
    item_id: str


def normalize_readiness_filter(value: str | None) -> str:
    normalized = (value or "all").strip().lower() or "all"
    if normalized not in INTAKE_READINESS_FILTERS:
        raise ApiError("VALIDATION_ERROR", status_code=422)
    return normalized


def priority_for_ready(ready_for_review: bool) -> int:
    return READY_PRIORITY if ready_for_review else NEEDS_INFO_PRIORITY


def encode_intake_list_cursor(*, priority: int, created_at: datetime, item_id: str) -> str:
    payload = json.dumps(
        {"v": _CURSOR_VERSION, "p": priority, "at": created_at.isoformat(), "id": item_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_intake_list_cursor(cursor: str) -> IntakeListCursor:
    try:
        if not cursor or len(cursor) > _MAX_CURSOR_LENGTH:
            raise ValueError("invalid cursor length")
        padded = cursor + "=" * (-len(cursor) % 4)
        payload = json.loads(base64.b64decode(padded, altchars=b"-_", validate=True).decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"at", "id", "p", "v"}:
            raise ValueError("invalid cursor payload")
        if payload["v"] != _CURSOR_VERSION:
            raise ValueError("unsupported cursor version")
        priority = payload["p"]
        if priority not in {READY_PRIORITY, NEEDS_INFO_PRIORITY}:
            raise ValueError("invalid cursor priority")
        item_id = str(UUID(payload["id"]))
        timestamp = datetime.fromisoformat(payload["at"])
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("cursor timestamp must include timezone")
        return IntakeListCursor(priority=priority, created_at=timestamp, item_id=item_id)
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError) as exc:
        raise ApiError("PAGINATION_CURSOR_INVALID", status_code=400) from exc


def intake_is_after_cursor(*, priority: int, created_at: datetime, item_id: str, cursor: IntakeListCursor) -> bool:
    if priority != cursor.priority:
        return priority > cursor.priority
    if created_at != cursor.created_at:
        return created_at < cursor.created_at
    return UUID(item_id).int < UUID(cursor.item_id).int
