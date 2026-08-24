from __future__ import annotations

import hashlib
from contextvars import ContextVar

from starlette.types import ASGIApp, Receive, Scope, Send

_request_ip_hash: ContextVar[str] = ContextVar("nodo_rate_limit_ip_hash", default="unknown")


def current_request_ip_hash() -> str:
    return _request_ip_hash.get()


class RateLimitRequestIdentityMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        client = scope.get("client")
        ip_address = client[0] if client else "unknown"
        token = _request_ip_hash.set(hashlib.sha256(ip_address.encode("utf-8")).hexdigest())
        try:
            await self._app(scope, receive, send)
        finally:
            _request_ip_hash.reset(token)
