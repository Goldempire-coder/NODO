from __future__ import annotations

from datetime import datetime

from app.core.errors import ApiError
from app.modules.businesses.access_link_selection import preferred_access_link
from app.modules.businesses.models import BUSINESS_ACCESS_ROLES, BUSINESS_ACCESS_STATUSES, BusinessAccessLinkRecord
from app.modules.businesses.row_mappers import access_link_from_row


class PostgresBusinessAccessLinksMixin:
    def create_access_link(
        self,
        *,
        business_id: str,
        user_id: str,
        telegram_id_snapshot: int,
        role_in_business: str,
        linked_by_admin_id: str,
        reason: str,
    ) -> BusinessAccessLinkRecord:
        if role_in_business not in BUSINESS_ACCESS_ROLES:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        with self._connect() as conn:  # type: ignore[attr-defined]
            existing = conn.execute(
                """
                select * from business_access_links
                where business_id = %s and user_id = %s and role_in_business = %s and status = 'active'
                order by updated_at desc, id desc
                limit 1
                """,
                (business_id, user_id, role_in_business),
            ).fetchone()
            if existing:
                return access_link_from_row(existing)
            if role_in_business == "owner":
                active_owner = conn.execute(
                    """
                    select id from business_access_links
                    where business_id = %s and role_in_business = 'owner' and status = 'active'
                      and not (user_id = %s and role_in_business = %s)
                    limit 1
                    """,
                    (business_id, user_id, role_in_business),
                ).fetchone()
                if active_owner:
                    raise ApiError("CONFLICT", status_code=409)
            existing_same_role = conn.execute(
                """
                select * from business_access_links
                where business_id = %s and user_id = %s and role_in_business = %s
                order by updated_at desc, id desc
                """,
                (business_id, user_id, role_in_business),
            ).fetchall()
            if existing_same_role:
                rows = conn.execute(
                    """
                    update business_access_links
                    set status = 'active',
                        telegram_id_snapshot = %s,
                        linked_by_admin_id = %s,
                        reason = %s,
                        suspended_at = null,
                        blocked_at = null,
                        revoked_at = null,
                        updated_at = now()
                    where business_id = %s and user_id = %s and role_in_business = %s
                    returning *
                    """,
                    (telegram_id_snapshot, linked_by_admin_id, reason, business_id, user_id, role_in_business),
                ).fetchall()
                conn.commit()
                selected = preferred_access_link([access_link_from_row(row) for row in rows])
                if selected is None:
                    raise ApiError("BUSINESS_ACCESS_LINK_REQUIRED", status_code=404)
                return selected
            row = conn.execute(
                """
                insert into business_access_links (
                    business_id, user_id, telegram_id_snapshot, role_in_business, status,
                    linked_by_admin_id, linked_at, reason, created_at, updated_at
                )
                values (%s, %s, %s, %s, 'active', %s, now(), %s, now(), now())
                returning *
                """,
                (business_id, user_id, telegram_id_snapshot, role_in_business, linked_by_admin_id, reason),
            ).fetchone()
            conn.commit()
        return access_link_from_row(row)

    def set_access_link_pin_hash(self, *, link_id: str, pin_hash: str) -> BusinessAccessLinkRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update business_access_links
                set business_pin_hash = %s,
                    business_pin_set_at = now(),
                    business_pin_verified_at = null,
                    business_pin_unlocked_until = null,
                    business_pin_failed_attempts = 0,
                    business_pin_locked_until = null,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (pin_hash, link_id),
            ).fetchone()
            conn.commit()
        return access_link_from_row(row)

    def mark_access_link_pin_verified(self, *, link_id: str, unlocked_until: datetime) -> BusinessAccessLinkRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update business_access_links
                set business_pin_verified_at = now(),
                    business_pin_unlocked_until = %s,
                    business_pin_failed_attempts = 0,
                    business_pin_locked_until = null,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (unlocked_until, link_id),
            ).fetchone()
            conn.commit()
        return access_link_from_row(row)

    def record_access_link_pin_failure(self, *, link_id: str, failed_attempts: int, locked_until: datetime | None) -> BusinessAccessLinkRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update business_access_links
                set business_pin_failed_attempts = %s,
                    business_pin_locked_until = %s,
                    business_pin_unlocked_until = null,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (failed_attempts, locked_until, link_id),
            ).fetchone()
            conn.commit()
        return access_link_from_row(row)

    def lock_access_link_pin(self, *, link_id: str) -> BusinessAccessLinkRecord:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                update business_access_links
                set business_pin_unlocked_until = null,
                    updated_at = now()
                where id = %s
                returning *
                """,
                (link_id,),
            ).fetchone()
            conn.commit()
        return access_link_from_row(row)

    def get_access_link(self, link_id: str) -> BusinessAccessLinkRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute("select * from business_access_links where id = %s", (link_id,)).fetchone()
        return access_link_from_row(row) if row else None

    def get_access_link_for_business_user(self, *, business_id: str, user_id: str) -> BusinessAccessLinkRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                select * from business_access_links
                where business_id = %s and user_id = %s
                order by (role_in_business = 'owner') desc, (status = 'active') desc, updated_at desc, id desc
                limit 1
                """,
                (business_id, user_id),
            ).fetchone()
        return access_link_from_row(row) if row else None

    def get_active_access_link_for_business_user(self, *, business_id: str, user_id: str) -> BusinessAccessLinkRecord | None:
        with self._connect() as conn:  # type: ignore[attr-defined]
            row = conn.execute(
                """
                select * from business_access_links
                where business_id = %s
                  and user_id = %s
                  and role_in_business = 'owner'
                  and status = 'active'
                order by updated_at desc, id desc
                limit 1
                """,
                (business_id, user_id),
            ).fetchone()
        return access_link_from_row(row) if row else None

    def list_access_links_for_business(self, business_id: str) -> list[BusinessAccessLinkRecord]:
        with self._connect() as conn:  # type: ignore[attr-defined]
            rows = conn.execute(
                """
                select * from business_access_links
                where business_id = %s
                order by updated_at desc, id desc
                """,
                (business_id,),
            ).fetchall()
        return [access_link_from_row(row) for row in rows]

    def set_access_link_status(self, *, link: BusinessAccessLinkRecord, status: str, reason: str) -> BusinessAccessLinkRecord:
        if status not in BUSINESS_ACCESS_STATUSES:
            raise ApiError("VALIDATION_ERROR", status_code=422)
        updates = {
            "active": "suspended_at = null, blocked_at = null, revoked_at = null",
            "suspended": "suspended_at = now()",
            "blocked": "blocked_at = now()",
            "revoked": "revoked_at = now()",
        }[status]
        with self._connect() as conn:  # type: ignore[attr-defined]
            target = conn.execute(
                "select * from business_access_links where id = %s",
                (link.id,),
            ).fetchone()
            if target is None:
                raise ApiError("BUSINESS_ACCESS_LINK_REQUIRED", status_code=404)
            rows = conn.execute(
                f"""
                update business_access_links
                set status = %s, reason = %s, {updates}, updated_at = now()
                where business_id = %s and user_id = %s and role_in_business = %s
                returning *
                """,
                (status, reason, target["business_id"], target["user_id"], target["role_in_business"]),
            ).fetchall()
            conn.commit()
        return preferred_access_link([access_link_from_row(row) for row in rows]) or link
