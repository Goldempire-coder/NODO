from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.core.errors import ApiError
from app.modules.ads.models import AdRecord


_CURSOR_VERSION = 1
_MAX_CURSOR_LENGTH = 512
_MAX_RATE_LENGTH = 64


@dataclass(frozen=True)
class MarketplacePosition:
    rate: Decimal
    created_at: datetime
    ad_id: str


def encode_marketplace_cursor(ad: AdRecord) -> str:
    payload = json.dumps(
        {
            "ad_id": ad.id,
            "created_at": ad.created_at.isoformat(),
            "rate": format(ad.rate_bs_per_usd, "f"),
            "v": _CURSOR_VERSION,
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_marketplace_cursor(cursor: str) -> MarketplacePosition:
    try:
        if not cursor or len(cursor) > _MAX_CURSOR_LENGTH:
            raise ValueError("invalid cursor length")
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.b64decode(padded, altchars=b"-_", validate=True)
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or set(payload) != {"ad_id", "created_at", "rate", "v"}:
            raise ValueError("invalid cursor payload")
        if payload["v"] != _CURSOR_VERSION:
            raise ValueError("unsupported cursor version")
        ad_id = str(UUID(payload["ad_id"]))
        rate_value = payload["rate"]
        if not isinstance(rate_value, str) or not 1 <= len(rate_value) <= _MAX_RATE_LENGTH:
            raise ValueError("invalid cursor rate")
        rate = Decimal(rate_value)
        if not rate.is_finite() or rate <= 0:
            raise ValueError("invalid cursor rate")
        created_at_value = payload["created_at"]
        if not isinstance(created_at_value, str):
            raise ValueError("invalid cursor timestamp")
        created_at = datetime.fromisoformat(created_at_value)
        if created_at.tzinfo is None or created_at.utcoffset() is None:
            raise ValueError("cursor timestamp must include timezone")
        return MarketplacePosition(rate=rate, created_at=created_at, ad_id=ad_id)
    except (
        AttributeError,
        binascii.Error,
        InvalidOperation,
        json.JSONDecodeError,
        TypeError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        raise ApiError("PAGINATION_CURSOR_INVALID", status_code=400) from exc


def paginate_marketplace_ads(
    items: list[AdRecord],
    *,
    cursor: str | None,
    limit: int,
) -> tuple[list[AdRecord], str | None]:
    position = decode_marketplace_cursor(cursor) if cursor else None
    ordered = sorted(
        items,
        key=lambda ad: (ad.rate_bs_per_usd, ad.created_at, ad.id),
        reverse=True,
    )
    if position is not None:
        ordered = [
            ad
            for ad in ordered
            if (ad.rate_bs_per_usd, ad.created_at, ad.id)
            < (position.rate, position.created_at, position.ad_id)
        ]
    window = ordered[: limit + 1]
    page = window[:limit]
    next_cursor = encode_marketplace_cursor(page[-1]) if len(window) > limit else None
    return page, next_cursor
