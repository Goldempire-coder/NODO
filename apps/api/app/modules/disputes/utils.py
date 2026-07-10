from __future__ import annotations

from uuid import UUID

from app.core.errors import ApiError


def require_uuid(value: str, code: str) -> str:
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError(code, status_code=404 if code.endswith("NOT_FOUND") else 400) from exc
