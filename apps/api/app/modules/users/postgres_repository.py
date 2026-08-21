from __future__ import annotations

from app.modules.users.admin_passwords import normalize_admin_username
from datetime import datetime

from psycopg.errors import UniqueViolation

from app.modules.users.models import AdminCredentialRecord, AdminTelegramLinkCodeRecord, UserRecord
from app.modules.users.postgres_sessions import PostgresUserSessionsMixin
from app.modules.users.row_mappers import admin_credential_from_row, user_from_row
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

    def list_active_admin_telegram_recipients(self) -> list[UserRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select *
                from users
                where status = 'active'
                  and role in ('admin', 'super_admin')
                  and admin_alert_telegram_id is not null
                order by created_at asc, id asc
                """
            ).fetchall()
        return [user_from_row(row) for row in rows]

    def create_admin_telegram_link_code(self, *, user_id: str, code_hash: str, expires_at: datetime) -> AdminTelegramLinkCodeRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into admin_telegram_link_codes (
                    user_id, code_hash, status, expires_at, created_at, updated_at
                )
                values (%s, %s, 'pending', %s, now(), now())
                returning id, user_id, code_hash, status, expires_at, created_at, updated_at, used_at, telegram_hash
                """,
                (user_id, code_hash, expires_at),
            ).fetchone()
            conn.commit()
        return _admin_telegram_link_code_from_row(row)

    def consume_admin_telegram_link_code(
        self,
        *,
        code_hash: str,
        telegram_chat_id: int,
        telegram_hash: str,
        now: datetime,
    ) -> tuple[AdminTelegramLinkCodeRecord | None, UserRecord | None, str]:
        with self._connect() as conn:
            row = conn.execute(
                """
                select
                    c.id as code_id,
                    c.user_id as code_user_id,
                    c.code_hash,
                    c.status as code_status,
                    c.expires_at,
                    c.created_at as code_created_at,
                    c.updated_at as code_updated_at,
                    c.used_at,
                    c.telegram_hash,
                    u.*
                from admin_telegram_link_codes c
                left join users u on u.id = c.user_id
                where c.code_hash = %s
                for update of c
                """,
                (code_hash,),
            ).fetchone()
            if row is None:
                return None, None, "not_found"
            record = _admin_telegram_link_code_from_joined_row(row)
            user = user_from_row(row) if row["id"] is not None else None
            if record.status != "pending":
                return record, user, record.status
            if record.expires_at <= now:
                updated = conn.execute(
                    """
                    update admin_telegram_link_codes
                    set status = 'expired', updated_at = %s
                    where id = %s
                    returning id, user_id, code_hash, status, expires_at, created_at, updated_at, used_at, telegram_hash
                    """,
                    (now, record.id),
                ).fetchone()
                conn.commit()
                return _admin_telegram_link_code_from_row(updated), user, "expired"
            if user is None or user.status != "active" or user.role not in {"admin", "super_admin"}:
                return record, user, "user_not_allowed"
            conflict = conn.execute(
                """
                select id
                from users
                where admin_alert_telegram_id = %s
                  and id <> %s
                limit 1
                """,
                (telegram_chat_id, user.id),
            ).fetchone()
            if conflict is not None:
                return record, user, "telegram_already_linked"
            try:
                user_row = conn.execute(
                    """
                    update users
                    set admin_alert_telegram_id = %s,
                        updated_at = %s
                    where id = %s
                    returning *
                    """,
                    (telegram_chat_id, now, user.id),
                ).fetchone()
                code_row = conn.execute(
                    """
                    update admin_telegram_link_codes
                    set status = 'used',
                        used_at = %s,
                        updated_at = %s,
                        telegram_hash = %s
                    where id = %s
                    returning id, user_id, code_hash, status, expires_at, created_at, updated_at, used_at, telegram_hash
                    """,
                    (now, now, telegram_hash, record.id),
                ).fetchone()
                conn.commit()
            except UniqueViolation:
                conn.rollback()
                return record, user, "telegram_already_linked"
        return _admin_telegram_link_code_from_row(code_row), user_from_row(user_row), "linked"

    def create_admin_user_with_credentials(
        self,
        *,
        username: str,
        password_hash: str,
        role: str,
        first_name: str | None = None,
    ) -> UserRecord:
        normalized = normalize_admin_username(username)
        with self._connect() as conn:
            user_row = conn.execute(
                """
                insert into users (
                    telegram_id, username, first_name, last_name, role, status,
                    orders_created_count, orders_completed_count, orders_expired_count,
                    created_at, updated_at, last_seen_at
                )
                values (null, %s, %s, null, %s, 'active', 0, 0, 0, now(), now(), now())
                returning *
                """,
                (normalized, first_name, role),
            ).fetchone()
            conn.execute(
                """
                insert into admin_credentials (
                    user_id, username, username_normalized, password_hash, status,
                    failed_attempts, password_changed_at, created_at, updated_at
                )
                values (%s, %s, %s, %s, 'active', 0, now(), now(), now())
                """,
                (user_row["id"], username.strip(), normalized, password_hash),
            )
            conn.commit()
        return user_from_row(user_row)

    def get_admin_credential_by_username(self, username_normalized: str) -> AdminCredentialRecord | None:
        with self._connect() as conn:
            row = conn.execute("select * from admin_credentials where username_normalized = %s", (username_normalized,)).fetchone()
        return admin_credential_from_row(row) if row else None

    def record_admin_credential_failure(self, credential: AdminCredentialRecord, *, attempt_limit: int, minutes: int) -> AdminCredentialRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                update admin_credentials
                set failed_attempts = failed_attempts + 1,
                    locked_until = case
                        when failed_attempts + 1 >= %s then now() + (%s || ' minutes')::interval
                        else locked_until
                    end,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (attempt_limit, minutes, credential.id),
            ).fetchone()
            conn.commit()
        return admin_credential_from_row(row)

    def record_admin_credential_success(self, credential: AdminCredentialRecord) -> AdminCredentialRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                update admin_credentials
                set failed_attempts = 0,
                    locked_until = null,
                    last_login_at = now(),
                    updated_at = now()
                where id = %s
                returning *
                """,
                (credential.id,),
            ).fetchone()
            conn.execute("update users set last_seen_at = now(), updated_at = now() where id = %s", (credential.user_id,))
            conn.commit()
        return admin_credential_from_row(row)

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
                set terms_accepted_at = now(),
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


def _admin_telegram_link_code_from_row(row) -> AdminTelegramLinkCodeRecord:  # type: ignore[no-untyped-def]
    return AdminTelegramLinkCodeRecord(
        id=str(row["id"]),
        user_id=str(row["user_id"]),
        code_hash=row["code_hash"],
        status=row["status"],
        expires_at=row["expires_at"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        used_at=row["used_at"],
        telegram_hash=row["telegram_hash"],
    )


def _admin_telegram_link_code_from_joined_row(row) -> AdminTelegramLinkCodeRecord:  # type: ignore[no-untyped-def]
    return AdminTelegramLinkCodeRecord(
        id=str(row["code_id"]),
        user_id=str(row["code_user_id"]),
        code_hash=row["code_hash"],
        status=row["code_status"],
        expires_at=row["expires_at"],
        created_at=row["code_created_at"],
        updated_at=row["code_updated_at"],
        used_at=row["used_at"],
        telegram_hash=row["telegram_hash"],
    )
