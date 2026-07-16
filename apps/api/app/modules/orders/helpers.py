from __future__ import annotations

import os
import time
from contextvars import ContextVar, Token
from typing import Any
from uuid import UUID

from app.core.errors import ApiError

_ORDER_RESPONSE_PROFILE_ENABLED: ContextVar[bool] = ContextVar("nodo_order_response_profile_enabled", default=False)


def require_uuid(value: str | None, error_code: str) -> str | None:
    if value is None:
        return None
    try:
        return str(UUID(value))
    except (TypeError, ValueError) as exc:
        raise ApiError(error_code, status_code=400 if error_code != "ORDER_NOT_FOUND" else 404) from exc


def profile_enabled() -> bool:
    return os.environ.get("NODO_INTERNAL_PROFILING") == "1" or _ORDER_RESPONSE_PROFILE_ENABLED.get()


def activate_response_profile(enabled: bool) -> Token[bool]:
    return _ORDER_RESPONSE_PROFILE_ENABLED.set(enabled)


def reset_response_profile(token: Token[bool]) -> None:
    _ORDER_RESPONSE_PROFILE_ENABLED.reset(token)


def profile_mark(profile: list[dict[str, Any]] | None, stage: str, started: float) -> None:
    if profile is None:
        return
    profile.append({"stage": stage, "elapsed_ms": round((time.perf_counter() - started) * 1000, 4)})


def profile_attach(payload: dict[str, Any], profile: list[dict[str, Any]] | None, started: float) -> dict[str, Any]:
    if profile is None:
        return payload
    payload["_profile"] = {
        "total_ms": round((time.perf_counter() - started) * 1000, 4),
        "stages": profile,
    }
    return payload
