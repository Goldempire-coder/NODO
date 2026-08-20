from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "password",
    "secret",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "initdata",
    "init_data",
    "telegram_init_data",
    "bot_token",
    "business_intake_bot_token",
    "jwt_secret",
    "jwt_refresh_secret",
    "supabase_service_role_key",
    "database_url",
    "redis_url",
    "private_key",
    "seed_phrase",
    "mnemonic",
    "account_value",
    "storage_path",
    "signed_url",
    "signedurl",
}

SECRET_PATTERNS = [
    re.compile(r"(postgres(?:ql)?://)([^@\s]+)@", re.IGNORECASE),
    re.compile(r"(redis://)([^@\s]+)@", re.IGNORECASE),
    re.compile(r"(https://api\.telegram\.org/(?:file/)?bot)[^/\s\"]+", re.IGNORECASE),
    re.compile(r"(Bearer\s+)[A-Za-z0-9._\-]+", re.IGNORECASE),
    re.compile(r"\b(?:access_token|refresh_token|BOT_TOKEN|BUSINESS_INTAKE_BOT_TOKEN|NODO_ADMIN_TELEGRAM_BOT_TOKEN|JWT_SECRET|JWT_REFRESH_SECRET|SUPABASE_SERVICE_ROLE_KEY|DATABASE_URL|REDIS_URL|storage_path|account_value|signed_url|signedUrl)=([^\s&]+)", re.IGNORECASE),
    re.compile(r"\b(?:password|secret|api_key|apikey|token)=([^\s&]+)", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.IGNORECASE | re.DOTALL),
    re.compile(r"\b0x[a-fA-F0-9]{64}\b"),
    re.compile(r"([?&](?:token|signature|X-Amz-Signature|expires|X-Amz-Credential)=)[^&\s]+", re.IGNORECASE),
]


def mask_tx_hash(value: str) -> str:
    if len(value) >= 12 and value.startswith("0x"):
        return f"{value[:6]}...{value[-4:]}"
    return "[REDACTED]"


def redact_text(value: str) -> str:
    redacted = value
    redacted = SECRET_PATTERNS[0].sub(r"\1[REDACTED]@", redacted)
    redacted = SECRET_PATTERNS[1].sub(r"\1[REDACTED]@", redacted)
    redacted = SECRET_PATTERNS[2].sub(r"\1[REDACTED]", redacted)
    redacted = SECRET_PATTERNS[3].sub(r"\1[REDACTED]", redacted)
    redacted = SECRET_PATTERNS[4].sub(lambda match: match.group(0).split("=", 1)[0] + "=[REDACTED]", redacted)
    redacted = SECRET_PATTERNS[5].sub(lambda match: match.group(0).split("=", 1)[0] + "=[REDACTED]", redacted)
    redacted = SECRET_PATTERNS[6].sub("[REDACTED_PRIVATE_KEY]", redacted)
    redacted = SECRET_PATTERNS[7].sub(lambda match: mask_tx_hash(match.group(0)), redacted)
    redacted = SECRET_PATTERNS[8].sub(r"\1[REDACTED]", redacted)
    return redacted


def redact_value(value: Any, *, key: str | None = None) -> Any:
    normalized_key = (key or "").lower()
    if normalized_key in SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {str(item_key): redact_value(item_value, key=str(item_key)) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_value(item) for item in value)
    return value


def redact_mapping(values: Mapping[str, Any]) -> dict[str, Any]:
    return {key: redact_value(value, key=key) for key, value in values.items()}
