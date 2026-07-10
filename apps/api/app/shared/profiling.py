from __future__ import annotations

import os
import time
from contextvars import ContextVar, Token
from typing import Any

from fastapi import Request


_CURRENT_PROFILE: ContextVar[list[dict[str, Any]] | None] = ContextVar("nodo_current_profile", default=None)


def internal_profile_enabled() -> bool:
    return os.environ.get("NODO_INTERNAL_PROFILING") == "1"


def staging_response_profile_enabled(request: Request) -> bool:
    app_env = os.environ.get("APP_ENV", "").strip().lower()
    return (
        app_env == "staging"
        and os.environ.get("ENABLE_STAGING_PROFILING") == "1"
        and request.headers.get("X-NODO-Profile") == "1"
    )


def activate_profile(profile: list[dict[str, Any]] | None) -> Token[list[dict[str, Any]] | None]:
    return _CURRENT_PROFILE.set(profile)


def reset_profile(token: Token[list[dict[str, Any]] | None]) -> None:
    _CURRENT_PROFILE.reset(token)


def current_profile() -> list[dict[str, Any]] | None:
    return _CURRENT_PROFILE.get()


def profile_mark(
    profile: list[dict[str, Any]] | None,
    stage: str,
    started: float,
    metadata: dict[str, Any] | None = None,
) -> None:
    if profile is None:
        return
    item: dict[str, Any] = {"stage": stage, "elapsed_ms": round((time.perf_counter() - started) * 1000, 4)}
    if metadata:
        item["metadata"] = _safe_metadata(metadata)
    profile.append(item)


def profile_attach(payload: dict[str, Any], profile: list[dict[str, Any]] | None, started: float) -> dict[str, Any]:
    if profile is None:
        return payload
    payload["_profile"] = {
        "total_ms": round((time.perf_counter() - started) * 1000, 4),
        "stages": profile,
    }
    return payload


def _safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in metadata.items():
        key_lower = str(key).lower()
        if any(blocked in key_lower for blocked in ("token", "secret", "authorization", "account_value", "storage_path", "sql")):
            continue
        if isinstance(value, str):
            safe[str(key)] = value[:80]
        elif isinstance(value, (int, float, bool)) or value is None:
            safe[str(key)] = value
        else:
            safe[str(key)] = str(value)[:80]
    return safe
