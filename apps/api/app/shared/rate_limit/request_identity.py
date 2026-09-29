from __future__ import annotations

import hashlib
import ipaddress
from contextvars import ContextVar
from functools import lru_cache

from starlette.types import ASGIApp, Receive, Scope, Send

_request_ip_hash: ContextVar[str] = ContextVar(
    "nodo_rate_limit_ip_hash", default="unknown"
)


def current_request_ip_hash() -> str:
    return _request_ip_hash.get()


@lru_cache(maxsize=16)
def _trusted_networks(
    proxies: tuple[str, ...],
) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    return tuple(ipaddress.ip_network(proxy) for proxy in proxies)


def client_ip_for_rate_limit(
    scope: Scope, *, trusted_proxies: tuple[str, ...] = ()
) -> str:
    client = scope.get("client")
    peer = _parse_ip_candidate(client[0]) if client else None
    fallback = peer or (client[0] if client else "unknown")
    networks = _trusted_networks(trusted_proxies)
    if peer is None or not any(
        ipaddress.ip_address(peer) in network for network in networks
    ):
        return fallback
    # Stop at the first untrusted hop; never skip malformed hops toward client input.
    for raw_value in reversed(_x_forwarded_for_values(scope)):
        parsed = _parse_ip_candidate(raw_value)
        if parsed is None:
            return fallback
        if not any(ipaddress.ip_address(parsed) in network for network in networks):
            return parsed
    return fallback


def _x_forwarded_for_values(scope: Scope) -> list[str]:
    values: list[str] = []
    for name, value in scope.get("headers", []):
        if name.lower() != b"x-forwarded-for":
            continue
        values.extend(part.strip() for part in value.decode("latin1").split(","))
    return values


def _parse_ip_candidate(raw_value: str) -> str | None:
    candidate = raw_value.strip()
    if not candidate or "%" in candidate:
        return None
    port = None
    if candidate.startswith("["):
        closing = candidate.find("]")
        if closing == -1:
            return None
        remainder = candidate[closing + 1 :]
        if remainder:
            if not remainder.startswith(":"):
                return None
            port = remainder[1:]
        candidate = candidate[1:closing]
    elif candidate.count(":") == 1 and "." in candidate:
        candidate, port = candidate.split(":", 1)
    if port is not None and (
        not port.isascii() or not port.isdecimal() or len(port) > 5 or int(port) > 65535
    ):
        return None
    try:
        return ipaddress.ip_address(candidate).compressed
    except ValueError:
        return None


class RateLimitRequestIdentityMiddleware:
    def __init__(self, app: ASGIApp, *, trusted_proxies: tuple[str, ...] = ()) -> None:
        self._app = app
        self._trusted_proxies = trusted_proxies

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        ip_address = client_ip_for_rate_limit(
            scope, trusted_proxies=self._trusted_proxies
        )
        token = _request_ip_hash.set(
            hashlib.sha256(ip_address.encode("utf-8")).hexdigest()
        )
        try:
            await self._app(scope, receive, send)
        finally:
            _request_ip_hash.reset(token)
