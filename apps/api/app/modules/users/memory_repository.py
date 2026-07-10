from __future__ import annotations

from datetime import datetime, timezone
from threading import RLock

from app.modules.users.models import SessionRecord, UserRecord, new_session_id, new_user_id, utc_now


class InMemoryUserRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._users_by_id: dict[str, UserRecord] = {}
        self._users_by_telegram_id: dict[int, UserRecord] = {}
        self._sessions_by_hash: dict[str, SessionRecord] = {}
        self._sessions_by_id: dict[str, SessionRecord] = {}

    def upsert_telegram_user(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> tuple[UserRecord, bool]:
        with self._lock:
            now = utc_now()
            existing = self._users_by_telegram_id.get(telegram_id)
            if existing is not None:
                existing.username = username
                existing.first_name = first_name
                existing.last_name = last_name
                existing.updated_at = now
                existing.last_seen_at = now
                return existing, False

            user = UserRecord(
                id=new_user_id(),
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                last_seen_at=now,
            )
            self._users_by_id[user.id] = user
            self._users_by_telegram_id[user.telegram_id] = user
            return user, True

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        return self._users_by_id.get(user_id)

    def get_user_by_telegram_id(self, telegram_id: int) -> UserRecord | None:
        return self._users_by_telegram_id.get(telegram_id)

    def set_user_status(self, user_id: str, status: str) -> None:
        with self._lock:
            user = self._users_by_id[user_id]
            user.status = status
            user.updated_at = utc_now()

    def set_user_role(self, user_id: str, role: str) -> None:
        with self._lock:
            user = self._users_by_id[user_id]
            user.role = role
            user.updated_at = utc_now()

    def accept_terms(self, user_id: str, terms_version: str) -> UserRecord:
        with self._lock:
            user = self._users_by_id[user_id]
            now = utc_now()
            user.terms_accepted_at = user.terms_accepted_at or now
            user.terms_version = terms_version
            user.updated_at = now
            return user

    def update_profile(self, user_id: str, *, first_name: str, phone: str) -> UserRecord:
        with self._lock:
            user = self._users_by_id[user_id]
            now = utc_now()
            user.first_name = first_name
            user.phone = phone
            user.updated_at = now
            return user

    def create_session(
        self,
        *,
        user_id: str,
        refresh_token_hash: str,
        access_token_jti: str,
        expires_at: datetime,
        ip_hash: str | None,
        user_agent: str | None,
    ) -> SessionRecord:
        with self._lock:
            session = SessionRecord(
                id=new_session_id(),
                user_id=user_id,
                refresh_token_hash=refresh_token_hash,
                status="active",
                access_token_jti=access_token_jti,
                expires_at=expires_at,
                last_used_at=utc_now(),
                ip_hash=ip_hash,
                user_agent=user_agent,
            )
            self._sessions_by_id[session.id] = session
            self._sessions_by_hash[session.refresh_token_hash] = session
            return session

    def get_session_by_refresh_hash(self, refresh_token_hash: str) -> SessionRecord | None:
        return self._sessions_by_hash.get(refresh_token_hash)

    def rotate_session(self, session: SessionRecord, *, refresh_token_hash: str, access_token_jti: str, expires_at: datetime) -> None:
        with self._lock:
            self._sessions_by_hash.pop(session.refresh_token_hash, None)
            session.refresh_token_hash = refresh_token_hash
            session.access_token_jti = access_token_jti
            session.expires_at = expires_at
            session.last_used_at = utc_now()
            session.updated_at = utc_now()
            self._sessions_by_hash[session.refresh_token_hash] = session

    def revoke_session(self, session: SessionRecord) -> None:
        with self._lock:
            session.status = "revoked"
            session.revoked_at = utc_now()
            session.updated_at = utc_now()

    def session_is_expired(self, session: SessionRecord) -> bool:
        return session.expires_at <= datetime.now(timezone.utc)
