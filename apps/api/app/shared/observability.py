from __future__ import annotations

import os
import re
import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import get_logger
from app.shared.logging_redaction import redact_mapping

REQUEST_ID_HEADER = "x-request-id"
CORRELATION_ID_HEADER = "x-correlation-id"
OPERATION_ID_HEADER = "x-nodo-operation-id"
SURFACE_HEADER = "x-nodo-surface"

REQUEST_ID_RESPONSE_HEADER = "X-Request-Id"
CORRELATION_ID_RESPONSE_HEADER = "X-Correlation-Id"
OPERATION_ID_RESPONSE_HEADER = "X-NODO-Operation-Id"
SURFACE_RESPONSE_HEADER = "X-NODO-Surface"

_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_SURFACE_PATTERN = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")

logger = get_logger("nodo.observability")


def is_valid_observability_id(value: str | None) -> bool:
    return bool(value and _ID_PATTERN.fullmatch(value))


def _generated_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"


def safe_request_id(value: str | None) -> str:
    return value if is_valid_observability_id(value) else _generated_id("req")


def safe_correlation_id(value: str | None) -> str:
    return value if is_valid_observability_id(value) else _generated_id("corr")


def safe_operation_id(value: str | None) -> str:
    return value if is_valid_observability_id(value) else _generated_id("op")


def safe_surface(value: str | None) -> str:
    if value and _SURFACE_PATTERN.fullmatch(value):
        return value
    return "unknown"


def observability_enabled() -> bool:
    return os.environ.get("OBSERVABILITY_REQUEST_LOGGING_ENABLED", "1").strip().lower() not in {"0", "false", "off", "no"}


def get_request_id(request: Any) -> str:
    return str(getattr(request.state, "request_id", "") or request.headers.get(REQUEST_ID_HEADER) or "request_id_unavailable")


def get_correlation_id(request: Any) -> str:
    return str(getattr(request.state, "correlation_id", "") or request.headers.get(CORRELATION_ID_HEADER) or "")


def get_operation_id(request: Any) -> str:
    return str(getattr(request.state, "operation_id", "") or request.headers.get(OPERATION_ID_HEADER) or "")


def route_template(request: Any) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path or request.url.path)


def _replace_header(scope: dict[str, Any], name: str, value: str) -> None:
    raw_name = name.encode("latin-1")
    raw_value = value.encode("latin-1")
    headers = [(key, val) for key, val in scope.get("headers", []) if key.lower() != raw_name]
    headers.append((raw_name, raw_value))
    scope["headers"] = headers


def _status_code(response: Any) -> int:
    return int(getattr(response, "status_code", 500))


def _error_code(response: Any) -> str | None:
    return response.headers.get("X-NODO-Error-Code") if hasattr(response, "headers") else None


class ObservabilityMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):  # type: ignore[no-untyped-def]
        request_id = safe_request_id(request.headers.get(REQUEST_ID_HEADER))
        correlation_id = safe_correlation_id(request.headers.get(CORRELATION_ID_HEADER))
        operation_id = safe_operation_id(request.headers.get(OPERATION_ID_HEADER))
        surface = safe_surface(request.headers.get(SURFACE_HEADER))

        _replace_header(request.scope, REQUEST_ID_HEADER, request_id)
        _replace_header(request.scope, CORRELATION_ID_HEADER, correlation_id)
        _replace_header(request.scope, OPERATION_ID_HEADER, operation_id)
        _replace_header(request.scope, SURFACE_HEADER, surface)

        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        request.state.operation_id = operation_id
        request.state.surface = surface

        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 4)

        response.headers[REQUEST_ID_RESPONSE_HEADER] = request_id
        response.headers[CORRELATION_ID_RESPONSE_HEADER] = correlation_id
        response.headers[OPERATION_ID_RESPONSE_HEADER] = operation_id
        response.headers[SURFACE_RESPONSE_HEADER] = surface

        if observability_enabled():
            fields = redact_mapping(
                {
                    "event": "backend_request_completed",
                    "method": request.method,
                    "route_template": route_template(request),
                    "status": _status_code(response),
                    "duration_ms": duration_ms,
                    "request_id": request_id,
                    "correlation_id": correlation_id,
                    "operation_id": operation_id,
                    "surface": surface,
                    "error_code": _error_code(response),
                }
            )
            logger.info("backend_request_completed", extra=fields)

        return response
