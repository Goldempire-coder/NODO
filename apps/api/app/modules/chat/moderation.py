from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from app.modules.chat.payment_sharing import redact_configured_payment_account


@dataclass(frozen=True)
class ChatModerationMatch:
    rule_id: str
    severity: str
    matched_phrase: str
    reason: str


MAX_MATCHED_PHRASE_LENGTH = 160

_PLATFORM_BYPASS_PATTERNS = (
    re.compile(r"\bpor fuera\b(?!\s+(?:del|de la)\b)"),
    re.compile(r"\bfuera de (?:la )?(?:app|plataforma|nodo)\b"),
    re.compile(r"\bsin nodo\b"),
    re.compile(r"\bno uses nodo\b"),
    re.compile(r"\bdirecto conmigo\b"),
    re.compile(r"\bhagamos directo\b"),
    re.compile(r"\bmejor tasa fuera\b"),
)

_EXTERNAL_CHANNEL_PATTERN = re.compile(r"\b(?:whatsapp|wasap|wsp|telegram|instagram|ig)\b")
_CONTACT_CONTEXT_PATTERN = re.compile(
    r"\b(?:escribeme|escribe|hablame|habla|contactame|contacta|coordinemos|coordina|pasame|te paso|mi numero|numero|usuario|directo)\b"
)
_PHONE_PATTERN = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{6,}\d)(?!\w)")
_EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
_URL_PATTERN = re.compile(r"\bhttps?://[^\s]+", re.IGNORECASE)
_HANDLE_PATTERN = re.compile(r"(?<!\w)@[A-Za-z0-9_]{3,32}\b")
_EXTERNAL_CHANNEL_LABELS = {
    "whatsapp": "WhatsApp",
    "wasap": "WhatsApp",
    "wsp": "WhatsApp",
    "telegram": "Telegram",
    "instagram": "Instagram",
    "ig": "Instagram",
}


def detect_off_platform_solicitation(
    body: str | None,
    *,
    allowed_contact_values: tuple[str, ...] = (),
) -> ChatModerationMatch | None:
    clean = _clean_text(body)
    if not clean:
        return None
    normalized = _normalize(clean)
    bypass_signals: list[str] = []
    for pattern in _PLATFORM_BYPASS_PATTERNS:
        match = pattern.search(normalized)
        if match:
            bypass_signals.append(match.group(0))
    if bypass_signals:
        return ChatModerationMatch(
            rule_id="off_platform_platform_bypass",
            severity="high",
            matched_phrase=_bounded_signal("; ".join(dict.fromkeys(bypass_signals))),
            reason="business_invited_platform_bypass",
        )
    contact_text = _without_allowed_contact_values(clean, allowed_contact_values)
    normalized_contact_text = _normalize(contact_text)
    channel_match = _EXTERNAL_CHANNEL_PATTERN.search(normalized_contact_text)
    has_contact_value = _has_contact_value(contact_text)
    if channel_match and _CONTACT_CONTEXT_PATTERN.search(normalized_contact_text):
        channel = _EXTERNAL_CHANNEL_LABELS.get(channel_match.group(0), "Canal externo")
        signal = f"{channel} [contacto redactado]" if has_contact_value else channel
        return ChatModerationMatch(
            rule_id="off_platform_external_contact",
            severity="attention",
            matched_phrase=_bounded_signal(signal),
            reason="business_shared_external_contact_channel",
        )
    if has_contact_value and _CONTACT_CONTEXT_PATTERN.search(normalized_contact_text):
        return ChatModerationMatch(
            rule_id="off_platform_external_contact",
            severity="attention",
            matched_phrase="[contacto externo redactado]",
            reason="business_shared_external_contact_value",
        )
    return None


def _clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def _normalize(value: str) -> str:
    folded = unicodedata.normalize("NFKD", value)
    ascii_text = "".join(char for char in folded if not unicodedata.combining(char))
    return ascii_text.lower()


def _has_contact_value(value: str) -> bool:
    return bool(_PHONE_PATTERN.search(value) or _EMAIL_PATTERN.search(value) or _URL_PATTERN.search(value) or _HANDLE_PATTERN.search(value))


def _without_allowed_contact_values(value: str, allowed_values: tuple[str, ...]) -> str:
    result = value
    for allowed_value in allowed_values:
        clean_allowed = _clean_text(allowed_value)
        if clean_allowed:
            result = redact_configured_payment_account(result, clean_allowed)
    return result


def _bounded_signal(value: str) -> str:
    signal = re.sub(r"\s+", " ", value).strip()
    return signal[:MAX_MATCHED_PHRASE_LENGTH]
