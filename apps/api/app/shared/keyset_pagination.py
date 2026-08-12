from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, TypeVar
from uuid import UUID

from app.core.errors import ApiError


T = TypeVar("T")
_CURSOR_VERSION = 1
_MAX_CURSOR_LENGTH = 512
_MAX_ID_LENGTH = 128


@dataclass(frozen=True)
class KeysetPosition:
    timestamp: datetime
    item_id: str


def encode_keyset_cursor(timestamp: datetime, item_id: str) -> str:
    payload = json.dumps(
        {"v": _CURSOR_VERSION, "at": timestamp.isoformat(), "id": item_id},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_keyset_cursor(cursor: str) -> KeysetPosition:
    try:
        if not cursor or len(cursor) > _MAX_CURSOR_LENGTH:
            raise ValueError("invalid cursor length")
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.b64decode(padded, altchars=b"-_", validate=True)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"at", "id", "v"}:
            raise ValueError("invalid cursor payload")
        if payload["v"] != _CURSOR_VERSION:
            raise ValueError("unsupported cursor version")
        item_id = payload["id"]
        if not isinstance(item_id, str) or not 1 <= len(item_id) <= _MAX_ID_LENGTH:
            raise ValueError("invalid cursor id")
        item_id = str(UUID(item_id))
        timestamp_value = payload["at"]
        if not isinstance(timestamp_value, str):
            raise ValueError("invalid cursor timestamp")
        timestamp = datetime.fromisoformat(timestamp_value)
        if timestamp.tzinfo is None or timestamp.utcoffset() is None:
            raise ValueError("cursor timestamp must include timezone")
        return KeysetPosition(timestamp=timestamp, item_id=item_id)
    except (binascii.Error, json.JSONDecodeError, UnicodeDecodeError, ValueError, TypeError) as exc:
        raise ApiError("PAGINATION_CURSOR_INVALID", status_code=400) from exc


def paginate_descending(
    items: list[T],
    *,
    timestamp_of: Callable[[T], datetime],
    id_of: Callable[[T], str],
    cursor: str | None,
    limit: int,
) -> tuple[list[T], str | None]:
    position = decode_keyset_cursor(cursor) if cursor else None
    ordered = sorted(items, key=lambda item: (timestamp_of(item), id_of(item)), reverse=True)
    if position is not None:
        ordered = [
            item
            for item in ordered
            if (timestamp_of(item), id_of(item)) < (position.timestamp, position.item_id)
        ]
    window = ordered[: limit + 1]
    page = window[:limit]
    next_cursor = (
        encode_keyset_cursor(timestamp_of(page[-1]), id_of(page[-1]))
        if len(window) > limit
        else None
    )
    return page, next_cursor
