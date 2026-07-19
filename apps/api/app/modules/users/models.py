from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class UserRecord:
    id: str
    telegram_id: int | None
    username: str | None
    first_name: str | None
    last_name: str | None
    phone: str | None = None
    role: str = "remitter"
    status: str = "active"
    trust_level: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    last_seen_at: datetime | None = None
    terms_accepted_at: datetime | None = None
    terms_version: str | None = None


@dataclass
class SessionRecord:
    id: str
    user_id: str
    refresh_token_hash: str
    status: str
    access_token_jti: str | None
    expires_at: datetime
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)
    revoked_at: datetime | None = None
    last_used_at: datetime | None = None
    ip_hash: str | None = None
    user_agent: str | None = None


def new_user_id() -> str:
    return str(uuid4())


def new_session_id() -> str:
    return str(uuid4())


@dataclass
class AdminCredentialRecord:
    id: str
    user_id: str
    username: str
    username_normalized: str
    password_hash: str
    status: str
    failed_attempts: int = 0
    locked_until: datetime | None = None
    last_login_at: datetime | None = None
    password_changed_at: datetime | None = None
    created_at: datetime = field(default_factory=utc_now)
    updated_at: datetime = field(default_factory=utc_now)


def new_admin_credential_id() -> str:
    return str(uuid4())
