from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import RLock
from typing import Any

from app.core.errors import ApiError
from app.shared.db.connection import pooled_connect


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@dataclass
class EmergencyModeRecord:
    enabled: bool = False
    reason: str | None = None
    message: str | None = None
    activated_by_user_id: str | None = None
    activated_at: datetime | None = None
    deactivated_by_user_id: str | None = None
    deactivated_at: datetime | None = None
    updated_at: datetime | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "enabled": self.enabled,
            "reason": self.reason,
            "message": self.message,
            "activated_by_user_id": self.activated_by_user_id,
            "activated_at": _iso(self.activated_at),
            "deactivated_by_user_id": self.deactivated_by_user_id,
            "deactivated_at": _iso(self.deactivated_at),
            "updated_at": _iso(self.updated_at),
        }


class InMemoryEmergencyModeRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._record = EmergencyModeRecord(updated_at=_now())

    def get(self) -> EmergencyModeRecord:
        with self._lock:
            return EmergencyModeRecord(**self._record.__dict__)

    def set_enabled(self, *, enabled: bool, reason: str, message: str | None, actor_user_id: str) -> EmergencyModeRecord:
        with self._lock:
            now = _now()
            if enabled:
                self._record = EmergencyModeRecord(
                    enabled=True,
                    reason=reason,
                    message=message,
                    activated_by_user_id=actor_user_id,
                    activated_at=now,
                    deactivated_by_user_id=None,
                    deactivated_at=None,
                    updated_at=now,
                )
            else:
                self._record = EmergencyModeRecord(
                    enabled=False,
                    reason=reason,
                    message=None,
                    activated_by_user_id=self._record.activated_by_user_id,
                    activated_at=self._record.activated_at,
                    deactivated_by_user_id=actor_user_id,
                    deactivated_at=now,
                    updated_at=now,
                )
            return self.get()


class PostgresEmergencyModeRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def _ensure_row(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into platform_emergency_mode (id, enabled, created_at, updated_at)
                values ('platform', false, now(), now())
                on conflict (id) do nothing
                """
            )

    def get(self) -> EmergencyModeRecord:
        self._ensure_row()
        with self._connect() as conn:
            row = conn.execute("select * from platform_emergency_mode where id = 'platform'").fetchone()
        return _record_from_row(row)

    def set_enabled(self, *, enabled: bool, reason: str, message: str | None, actor_user_id: str) -> EmergencyModeRecord:
        self._ensure_row()
        if enabled:
            sql = """
                update platform_emergency_mode
                   set enabled = true,
                       reason = %s,
                       message = %s,
                       activated_by_user_id = %s,
                       activated_at = now(),
                       deactivated_by_user_id = null,
                       deactivated_at = null,
                       updated_at = now()
                 where id = 'platform'
             returning *
            """
            params = (reason, message, actor_user_id)
        else:
            sql = """
                update platform_emergency_mode
                   set enabled = false,
                       reason = %s,
                       message = null,
                       deactivated_by_user_id = %s,
                       deactivated_at = now(),
                       updated_at = now()
                 where id = 'platform'
             returning *
            """
            params = (reason, actor_user_id)
        with self._connect() as conn:
            row = conn.execute(sql, params).fetchone()
        return _record_from_row(row)


def _record_from_row(row) -> EmergencyModeRecord:  # type: ignore[no-untyped-def]
    if row is None:
        return EmergencyModeRecord(updated_at=_now())
    return EmergencyModeRecord(
        enabled=bool(row["enabled"]),
        reason=row["reason"],
        message=row["message"],
        activated_by_user_id=str(row["activated_by_user_id"]) if row["activated_by_user_id"] else None,
        activated_at=row["activated_at"],
        deactivated_by_user_id=str(row["deactivated_by_user_id"]) if row["deactivated_by_user_id"] else None,
        deactivated_at=row["deactivated_at"],
        updated_at=row["updated_at"],
    )


def require_platform_operational(repository, *, operation: str) -> None:  # type: ignore[no-untyped-def]
    record = repository.get()
    if not record.enabled:
        return
    message = record.message or "NODO esta en modo emergencia. Intenta nuevamente cuando el servicio se estabilice."
    raise ApiError("PLATFORM_EMERGENCY_MODE_ACTIVE", message, status_code=503)
