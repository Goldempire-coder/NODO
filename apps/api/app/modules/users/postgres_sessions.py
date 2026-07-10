from __future__ import annotations

from datetime import datetime, timezone

from app.modules.users.models import SessionRecord
from app.modules.users.row_mappers import session_from_row


class PostgresUserSessionsMixin:
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
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                insert into sessions (
                    user_id, refresh_token_hash, status, access_token_jti,
                    expires_at, last_used_at, ip_hash, user_agent, created_at, updated_at
                )
                values (%s, %s, 'active', %s, %s, now(), %s, %s, now(), now())
                returning *
                """,
                (user_id, refresh_token_hash, access_token_jti, expires_at, ip_hash, user_agent),
            ).fetchone()
            conn.commit()
        return session_from_row(row)

    def get_session_by_refresh_hash(self, refresh_token_hash: str) -> SessionRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute("select * from sessions where refresh_token_hash = %s", (refresh_token_hash,)).fetchone()
        return session_from_row(row) if row else None

    def rotate_session(self, session: SessionRecord, *, refresh_token_hash: str, access_token_jti: str, expires_at: datetime) -> None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            conn.execute(
                """
                update sessions
                set refresh_token_hash = %s,
                    access_token_jti = %s,
                    expires_at = %s,
                    last_used_at = now(),
                    updated_at = now()
                where id = %s and status = 'active'
                """,
                (refresh_token_hash, access_token_jti, expires_at, session.id),
            )
            conn.commit()

    def revoke_session(self, session: SessionRecord) -> None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            conn.execute(
                """
                update sessions
                set status = 'revoked', revoked_at = now(), updated_at = now()
                where id = %s and status <> 'revoked'
                """,
                (session.id,),
            )
            conn.commit()

    def session_is_expired(self, session: SessionRecord) -> bool:
        return session.expires_at <= datetime.now(timezone.utc)
