from __future__ import annotations

import logging
import re
from typing import Any

SECRET_PATTERNS = [
    re.compile(r"(postgres(?:ql)?://)([^@\s]+)@", re.IGNORECASE),
    re.compile(r"(redis://)([^@\s]+)@", re.IGNORECASE),
    re.compile(r"(https://api\.telegram\.org/(?:file/)?bot)[^/\s\"]+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"\b(?:BOT|JWT|SECRET|TOKEN|KEY)[A-Z0-9_]*=[^\s]+", re.IGNORECASE),
]


def redact_secret(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    redacted = value
    redacted = SECRET_PATTERNS[0].sub(r"\1[REDACTED]@", redacted)
    redacted = SECRET_PATTERNS[1].sub(r"\1[REDACTED]@", redacted)
    redacted = SECRET_PATTERNS[2].sub(r"\1[REDACTED]", redacted)
    redacted = SECRET_PATTERNS[3].sub(r"\1[REDACTED]", redacted)
    for pattern in SECRET_PATTERNS[4:]:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


class SecretRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_secret(record.getMessage())
        record.args = ()
        for key, value in list(record.__dict__.items()):
            if isinstance(value, str):
                setattr(record, key, redact_secret(value))
        return True


def configure_logging(app_env: str) -> None:
    level = logging.INFO if app_env != "test" else logging.WARNING
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    redaction_filter = SecretRedactionFilter()
    root_logger = logging.getLogger()
    root_logger.addFilter(redaction_filter)
    for handler in root_logger.handlers:
        handler.addFilter(redaction_filter)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.addFilter(SecretRedactionFilter())
    return logger
