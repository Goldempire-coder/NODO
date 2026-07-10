from __future__ import annotations

from app.modules.users.models import UserRecord
from app.modules.users.postgres_sessions import PostgresUserSessionsMixin
from app.modules.users.row_mappers import user_from_row
from app.shared.db.connection import pooled_connect


class PostgresUserRepository(PostgresUserSessionsMixin):
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def upsert_telegram_user(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> tuple[UserRecord, bool]:
        with self._connect() as conn:
            existing_row = conn.execute("select * from users where telegram_id = %s", (telegram_id,)).fetchone()
            created = existing_row is None
            row = conn.execute(
                """
                insert into users (
                    telegram_id, username, first_name, last_name, role, status,
                    orders_created_count, orders_completed_count, orders_expired_count,
                    created_at, updated_at, last_seen_at
                )
                values (%s, %s, %s, %s, 'remitter', 'active', 0, 0, 0, now(), now(), now())
                on conflict (telegram_id) where telegram_id is not null
                do update set
                    username = excluded.username,
                    first_name = excluded.first_name,
                    last_name = excluded.last_name,
                    updated_at = now(),
                    last_seen_at = now()
                returning *
                """,
                (telegram_id, username, first_name, last_name),
            ).fetchone()
            conn.commit()
        return user_from_row(row), created

    def get_user_by_id(self, user_id: str) -> UserRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from users where id = %s", (user_id,)).fetchone()
        return user_from_row(row) if row else None

    def get_user_by_telegram_id(self, telegram_id: int) -> UserRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from users where telegram_id = %s", (telegram_id,)).fetchone()
        return user_from_row(row) if row else None

    def set_user_status(self, user_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute("update users set status = %s, updated_at = now() where id = %s", (status, user_id))
            conn.commit()

    def set_user_role(self, user_id: str, role: str) -> None:
        with self._connect() as conn:
            conn.execute("update users set role = %s, updated_at = now() where id = %s", (role, user_id))
            conn.commit()

    def accept_terms(self, user_id: str, terms_version: str) -> UserRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                update users
                set terms_accepted_at = coalesce(terms_accepted_at, now()),
                    terms_version = %s,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (terms_version, user_id),
            ).fetchone()
            conn.commit()
        return user_from_row(row)

    def update_profile(self, user_id: str, *, first_name: str, phone: str) -> UserRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                update users
                set first_name = %s,
                    phone = %s,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (first_name, phone, user_id),
            ).fetchone()
            conn.commit()
        return user_from_row(row)
