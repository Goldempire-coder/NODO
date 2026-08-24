from __future__ import annotations

import hashlib
import ipaddress
from contextvars import ContextVar

from starlette.types import ASGIApp, Receive, Scope, Send

_request_ip_hash: ContextVar[str] = ContextVar("nodo_rate_limit_ip_hash", default="unknown")


def current_request_ip_hash() -> str:
    return _request_ip_hash.get()


def client_ip_for_rate_limit(scope: Scope) -> str:
    forwarded_for = _x_forwarded_for_values(scope)
    for raw_value in reversed(forwarded_for):
        parsed = _parse_ip_candidate(raw_value)
        if parsed is not None:
            return parsed

    client = scope.get("client")
    return client[0] if client else "unknown"


def _x_forwarded_for_values(scope: Scope) -> list[str]:
    values: list[str] = []
    for name, value in scope.get("headers", []):
        if name.lower() != b"x-forwarded-for":
            continue
        values.extend(part.strip() for part in value.decode("latin1").split(","))
    return values


def _parse_ip_candidate(raw_value: str) -> str | None:
    candidate = raw_value.strip()
    if not candidate:
        return None
    if candidate.startswith("["):
        closing = candidate.find("]")
        if closing != -1:
            candidate = candidate[1:closing]
    elif candidate.count(":") == 1 and "." in candidate:
        candidate = candidate.split(":", 1)[0]
    try:
        return ipaddress.ip_address(candidate).compressed
    except ValueError:
        return None


class RateLimitRequestIdentityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        ip_address = client_ip_for_rate_limit(scope)
        token = _request_ip_hash.set(hashlib.sha256(ip_address.encode("utf-8")).hexdigest())
        try:
            await self._app(scope, receive, send)
        finally:
            _request_ip_hash.reset(token)
