from __future__ import annotations

from datetime import datetime
from typing import Any

from app.modules.staff.models import StaffInviteRecord, StaffPermissionRecord, StaffProfileRecord
from app.shared.db.connection import pooled_connect


class PostgresStaffRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def _profile(self, row: dict[str, Any]) -> StaffProfileRecord:
        return StaffProfileRecord(**row)

    def _permission(self, row: dict[str, Any]) -> StaffPermissionRecord:
        return StaffPermissionRecord(**row)

    def _invite(self, row: dict[str, Any]) -> StaffInviteRecord:
        return StaffInviteRecord(**row)

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select id::text, telegram_id, username, first_name, last_name, role, status, created_at, updated_at
                from users where id = %s
                """,
                (user_id,),
            ).fetchone()
        return dict(row) if row else None

    def count_active_super_admin_profiles(self) -> int:
        with self._connect() as conn:
            row = conn.execute("select count(*) as count from staff_profiles where status = 'active' and staff_role = 'super_admin'").fetchone()
        return int(row["count"])

    def list_profiles(self, *, status: str | None, staff_role: str | None, q: str | None, cursor: str | None, limit: int) -> tuple[list[StaffProfileRecord], str | None]:
        clauses = ["1=1"]
        params: list[object] = []
        if status:
            clauses.append("sp.status = %s")
            params.append(status)
        if staff_role:
            clauses.append("sp.staff_role = %s")
            params.append(staff_role)
        if q:
            clauses.append("(sp.display_name ilike %s or u.username ilike %s or u.first_name ilike %s)")
            needle = f"%{q}%"
            params.extend([needle, needle, needle])
        if cursor:
            clauses.append("sp.created_at < %s")
            params.append(cursor)
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select sp.id::text, sp.user_id::text, sp.staff_role, sp.status, sp.display_name,
                       sp.created_by_super_admin_id::text, sp.activated_by_super_admin_id::text,
                       sp.suspended_by_super_admin_id::text, sp.revoked_by_super_admin_id::text,
                       sp.activated_at, sp.suspended_at, sp.revoked_at, sp.reason,
                       sp.created_at, sp.updated_at
                from staff_profiles sp
                join users u on u.id = sp.user_id
                where {' and '.join(clauses)}
                order by sp.created_at desc
                limit %s
                """,
                params,
            ).fetchall()
        items = [self._profile(dict(row)) for row in rows]
        return items, items[-1].created_at.isoformat() if len(items) == limit else None

    def get_profile(self, profile_id: str) -> StaffProfileRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select id::text, user_id::text, staff_role, status, display_name,
                       created_by_super_admin_id::text, activated_by_super_admin_id::text,
                       suspended_by_super_admin_id::text, revoked_by_super_admin_id::text,
                       activated_at, suspended_at, revoked_at, reason, created_at, updated_at
                from staff_profiles where id = %s
                """,
                (profile_id,),
            ).fetchone()
        return self._profile(dict(row)) if row else None

    def get_active_profile_for_user(self, user_id: str) -> StaffProfileRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                select id::text, user_id::text, staff_role, status, display_name,
                       created_by_super_admin_id::text, activated_by_super_admin_id::text,
                       suspended_by_super_admin_id::text, revoked_by_super_admin_id::text,
                       activated_at, suspended_at, revoked_at, reason, created_at, updated_at
                from staff_profiles
                where user_id = %s and status = 'active'
                order by created_at desc
                limit 1
                """,
                (user_id,),
            ).fetchone()
        return self._profile(dict(row)) if row else None

    def create_invite(self, *, target_user_id: str | None, target_telegram_id: int | None, target_username: str | None, staff_role: str, expires_at: datetime, created_by_super_admin_id: str, reason: str) -> StaffInviteRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into staff_invites (
                    target_user_id, target_telegram_id, target_username, invite_code_hash,
                    staff_role, status, expires_at, created_by_super_admin_id, reason,
                    created_at, updated_at
                )
                values (%s, %s, %s, null, %s, 'pending', %s, %s, %s, now(), now())
                returning id::text, target_user_id::text, target_telegram_id, target_username, invite_code_hash,
                          staff_role, status, expires_at, created_by_super_admin_id::text,
                          accepted_by_user_id::text, accepted_at, revoked_at, expired_at,
                          reason, created_at, updated_at
                """,
                (target_user_id, target_telegram_id, target_username, staff_role, expires_at, created_by_super_admin_id, reason),
            ).fetchone()
            conn.commit()
        return self._invite(dict(row))

    def create_or_activate_profile(self, *, user_id: str, staff_role: str, display_name: str | None, actor_id: str, reason: str) -> StaffProfileRecord:
        with self._connect() as conn:
            row = conn.execute(
                """
                insert into staff_profiles (
                    user_id, staff_role, status, display_name, created_by_super_admin_id,
                    activated_by_super_admin_id, activated_at, reason, created_at, updated_at
                )
                values (%s, %s, 'active', %s, %s, %s, now(), %s, now(), now())
                on conflict (user_id) where status = 'active'
                do update set staff_role = excluded.staff_role,
                              display_name = coalesce(excluded.display_name, staff_profiles.display_name),
                              reason = excluded.reason,
                              updated_at = now()
                returning id::text, user_id::text, staff_role, status, display_name,
                          created_by_super_admin_id::text, activated_by_super_admin_id::text,
                          suspended_by_super_admin_id::text, revoked_by_super_admin_id::text,
                          activated_at, suspended_at, revoked_at, reason, created_at, updated_at
                """,
                (user_id, staff_role, display_name, actor_id, actor_id, reason),
            ).fetchone()
            conn.commit()
        return self._profile(dict(row))

    def set_profile_status(self, *, profile_id: str, status: str, actor_id: str, reason: str) -> StaffProfileRecord | None:
        actor_field = {"active": "activated_by_super_admin_id", "suspended": "suspended_by_super_admin_id", "revoked": "revoked_by_super_admin_id"}[status]
        time_field = {"active": "activated_at", "suspended": "suspended_at", "revoked": "revoked_at"}[status]
        with self._connect() as conn:
            row = conn.execute(
                f"""
                update staff_profiles
                set status = %s, {actor_field} = %s, {time_field} = now(), reason = %s, updated_at = now()
                where id = %s
                returning id::text, user_id::text, staff_role, status, display_name,
                          created_by_super_admin_id::text, activated_by_super_admin_id::text,
                          suspended_by_super_admin_id::text, revoked_by_super_admin_id::text,
                          activated_at, suspended_at, revoked_at, reason, created_at, updated_at
                """,
                (status, actor_id, reason, profile_id),
            ).fetchone()
            if status == "revoked":
                conn.execute(
                    """
                    update staff_permissions
                    set status = 'revoked', revoked_by_super_admin_id = %s, revoked_at = now(), updated_at = now()
                    where staff_profile_id = %s and status = 'active'
                    """,
                    (actor_id, profile_id),
                )
            conn.commit()
        return self._profile(dict(row)) if row else None

    def replace_permissions(self, *, profile_id: str, permissions: list[dict[str, str | None]], actor_id: str, reason: str) -> list[StaffPermissionRecord]:
        with self._connect() as conn:
            conn.execute(
                """
                update staff_permissions
                set status = 'revoked', revoked_by_super_admin_id = %s, revoked_at = now(), updated_at = now()
                where staff_profile_id = %s and status = 'active'
                """,
                (actor_id, profile_id),
            )
            rows = []
            for item in permissions:
                rows.append(
                    conn.execute(
                        """
                        insert into staff_permissions (
                            staff_profile_id, permission, scope, scope_value, status,
                            granted_by_super_admin_id, reason, created_at, updated_at
                        )
                        values (%s, %s, %s, %s, 'active', %s, %s, now(), now())
                        returning id::text, staff_profile_id::text, permission, scope, scope_value, status,
                                  granted_by_super_admin_id::text, revoked_by_super_admin_id::text,
                                  revoked_at, reason, created_at, updated_at
                        """,
                        (profile_id, item["permission"], item["scope"], item.get("scope_value"), actor_id, reason),
                    ).fetchone()
                )
            conn.commit()
        return [self._permission(dict(row)) for row in rows]

    def list_permissions(self, profile_id: str) -> list[StaffPermissionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select id::text, staff_profile_id::text, permission, scope, scope_value, status,
                       granted_by_super_admin_id::text, revoked_by_super_admin_id::text,
                       revoked_at, reason, created_at, updated_at
                from staff_permissions
                where staff_profile_id = %s
                order by created_at desc
                """,
                (profile_id,),
            ).fetchall()
        return [self._permission(dict(row)) for row in rows]

    def list_active_permissions_for_user(self, user_id: str) -> list[StaffPermissionRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                select p.id::text, p.staff_profile_id::text, p.permission, p.scope, p.scope_value, p.status,
                       p.granted_by_super_admin_id::text, p.revoked_by_super_admin_id::text,
                       p.revoked_at, p.reason, p.created_at, p.updated_at
                from staff_permissions p
                join staff_profiles sp on sp.id = p.staff_profile_id
                where sp.user_id = %s and sp.status = 'active' and p.status = 'active'
                """,
                (user_id,),
            ).fetchall()
        return [self._permission(dict(row)) for row in rows]

    def list_activity(self, *, profile_id: str, event_type: str | None, cursor: str | None, limit: int) -> tuple[list[dict[str, Any]], str | None]:
        profile = self.get_profile(profile_id)
        if profile is None:
            return [], None
        clauses = ["(actor_user_id = %s or resource_id = %s)"]
        params: list[object] = [profile.user_id, profile.id]
        if event_type:
            clauses.append("event_type = %s")
            params.append(event_type)
        if cursor:
            clauses.append("created_at < %s")
            params.append(cursor)
        params.append(limit)
        with self._connect() as conn:
            rows = conn.execute(
                f"""
                select event_type, actor_user_id::text, actor_role, resource_type, resource_id::text,
                       metadata_json, created_at
                from audit_logs
                where {' and '.join(clauses)}
                order by created_at desc
                limit %s
                """,
                params,
            ).fetchall()
        items = [dict(row) for row in rows]
        for item in items:
            if item.get("created_at"):
                item["created_at"] = item["created_at"].isoformat()
        return items, items[-1]["created_at"] if len(items) == limit else None
