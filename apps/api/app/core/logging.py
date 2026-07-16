from __future__ import annotations

import logging
from typing import Any

from app.shared.logging_redaction import redact_text, redact_value


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
