from __future__ import annotations

import json
import logging
import math
import re
from datetime import datetime, timezone
from typing import Any

from app.shared.logging_redaction import redact_text, redact_value

_LABEL_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}")
_EVENT_PATTERN = re.compile(r"[a-z][a-z0-9_]{0,79}")
_ROUTE_PATTERN = re.compile(r"/[A-Za-z0-9_/{.}:-]{0,255}")
_PRIVATE_LABEL_PATTERN = re.compile(
    r"0x[a-fA-F0-9]{40}|T[1-9A-HJ-NP-Za-km-z]{33}"
    r"|eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"
)
_TEXT_FIELDS = (
    "request_id", "correlation_id", "operation_id", "surface", "method",
    "error_code", "exception_class", "app_version", "notification_type",
)
_NUMBER_FIELDS = (
    "duration_ms", "attempts", "processed", "sent", "retryable_failed",
    "failed_permanent", "scanned", "eligible", "contract_scanned",
    "contract_eligible", "verified_attempts", "contract_verified_attempts",
    "credited", "contract_credited", "under_review", "contract_under_review",
    "pending", "contract_pending", "errors_count", "rpc_calls",
    "api_thread_limit", "previous_limit",
)


def _safe_label(value: Any, pattern: re.Pattern[str] = _LABEL_PATTERN) -> str | None:
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        return None
    redacted = redact_text(value)
    return redacted if redacted == value and not _PRIVATE_LABEL_PATTERN.search(value) else "[REDACTED]"


class OperationalJsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        # Never serialize the whole record, free text, or exception/stack bodies.
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, timezone.utc).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": _safe_label(record.name) or "unknown",
            "event": _safe_label(getattr(record, "event", None), _EVENT_PATTERN)
            or _safe_label(record.msg, _EVENT_PATTERN)
            or "unstructured_log",
        }
        if not record.name.startswith(("app.", "nodo.")):
            payload["event"] = "unstructured_log"
            return json.dumps(payload, ensure_ascii=True, separators=(",", ":"))
        for key in _TEXT_FIELDS:
            value = _safe_label(getattr(record, key, None))
            if value is not None:
                payload[key] = value
        for key in _NUMBER_FIELDS:
            value = getattr(record, key, None)
            if type(value) in (int, float) and 0 <= value <= 2**63 - 1 and math.isfinite(value):
                payload[key] = value
        status = getattr(record, "status", None)
        if type(status) is int and 100 <= status <= 599:
            payload["status"] = status
            # The middleware may fall back to a raw path without a matched route.
            if status not in (404, 405) and not 300 <= status < 400:
                route = _safe_label(getattr(record, "route_template", None), _ROUTE_PATTERN)
                if route is not None:
                    payload["route_template"] = route
        return json.dumps(payload, ensure_ascii=True, allow_nan=False, separators=(",", ":"))


def redact_secret(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value)
    return redact_value(value)


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_secret(record.getMessage())
        record.args = ()
        for key, value in list(record.__dict__.items()):
            setattr(record, key, redact_secret(value))
        return True


def _add_secret_filter(target: logging.Logger | logging.Handler) -> None:
    if not any(isinstance(item, SecretRedactionFilter) for item in target.filters):
        target.addFilter(SecretRedactionFilter())


def configure_logging(app_env: str) -> None:
    level = logging.INFO if app_env != "test" else logging.WARNING
    logging.basicConfig(level=level)
    root_logger = logging.getLogger()
    _add_secret_filter(root_logger)
    for handler in root_logger.handlers:
        handler.setFormatter(OperationalJsonFormatter())
        _add_secret_filter(handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    _add_secret_filter(logger)
    return logger
