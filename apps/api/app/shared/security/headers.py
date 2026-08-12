from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware


PRIVATE_NO_STORE = "private, no-store"

_PRIVATE_API_SURFACES = (
    "/api/v1/admin",
    "/api/v1/auth",
    "/api/v1/telegram",
    "/api/v1/users",
    "/api/v1/surface",
    "/api/v1/businesses",
    "/api/v1/business",
    "/api/v1/business-intake",
    "/api/v1/orders",
    "/api/v1/support",
    "/api/v1/notifications",
    "/api/v1/observability",
)


def _is_private_api_path(path: str) -> bool:
    return any(path == surface or path.startswith(f"{surface}/") for surface in _PRIVATE_API_SURFACES)


class RuntimeTimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):  # type: ignore[no-untyped-def]
        started = time.perf_counter()
        response = await call_next(request)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 4)
        response.headers["X-NODO-Process-Time-Ms"] = str(elapsed_ms)
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms}"
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):  # type: ignore[no-untyped-def]
        response = await call_next(request)
        if _is_private_api_path(request.url.path):
            response.headers["Cache-Control"] = PRIVATE_NO_STORE
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response
