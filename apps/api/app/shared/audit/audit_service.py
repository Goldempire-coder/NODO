from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from uuid import uuid4

from psycopg.types.json import Jsonb

from app.shared.db.connection import pooled_connect


@dataclass(frozen=True)
class AuditEvent:
    id: str
    event_type: str
    actor_user_id: str | None
    actor_role: str | None
    resource_type: str
    resource_id: str | None
    request_id: str
    metadata_json: dict | None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class InMemoryAuditWriter:
    def __init__(self) -> None:
        self._lock = RLock()
        self.events: list[AuditEvent] = []

    def write(
        self,
        *,
        event_type: str,
        actor_user_id: str | None,
        actor_role: str | None,
        resource_type: str,
        resource_id: str | None,
        request_id: str,
        metadata_json: dict | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            id=str(uuid4()),
            event_type=event_type,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            resource_type=resource_type,
            resource_id=resource_id,
            request_id=request_id,
            metadata_json=metadata_json,
        )
        with self._lock:
            self.events.append(event)
        return event

    def write_many(self, events: list[dict]) -> list[AuditEvent]:
        written = [
            AuditEvent(
                id=str(uuid4()),
                event_type=event["event_type"],
                actor_user_id=event.get("actor_user_id"),
                actor_role=event.get("actor_role"),
                resource_type=event["resource_type"],
                resource_id=event.get("resource_id"),
                request_id=event["request_id"],
                metadata_json=event.get("metadata_json"),
            )
            for event in events
        ]
        with self._lock:
            self.events.extend(written)
        return written


class PostgresAuditWriter:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _jsonb(self, value: dict | None) -> Jsonb | None:
        if value is None:
            return None
        return Jsonb(value, dumps=lambda payload: json.dumps(payload, default=str))

    def write(
        self,
        *,
        event_type: str,
        actor_user_id: str | None,
        actor_role: str | None,
        resource_type: str,
        resource_id: str | None,
        request_id: str,
        metadata_json: dict | None = None,
    ) -> AuditEvent:
        with pooled_connect(self._database_url) as conn:
            row = conn.execute(
                """
                insert into audit_logs (
                    actor_user_id, actor_role, event_type, resource_type, resource_id,
                    request_id, metadata_json, created_at
                )
                values (%s, %s, %s, %s, %s, %s, %s, now())
                returning id, event_type, actor_user_id, actor_role, resource_type,
                          resource_id, request_id, metadata_json, created_at
                """,
                (actor_user_id, actor_role, event_type, resource_type, resource_id, request_id, self._jsonb(metadata_json)),
            ).fetchone()
            conn.commit()
        return AuditEvent(
            id=str(row["id"]),
            event_type=row["event_type"],
            actor_user_id=str(row["actor_user_id"]) if row["actor_user_id"] else None,
            actor_role=row["actor_role"],
            resource_type=row["resource_type"],
            resource_id=str(row["resource_id"]) if row["resource_id"] else None,
            request_id=row["request_id"],
            metadata_json=row["metadata_json"],
            created_at=row["created_at"],
        )

    def write_many(self, events: list[dict]) -> list[AuditEvent]:
        if not events:
            return []
        values_sql = ", ".join(["(%s, %s, %s, %s, %s, %s, %s, now())"] * len(events))
        params: list[object] = []
        for event in events:
            params.extend(
                [
                    event.get("actor_user_id"),
                    event.get("actor_role"),
                    event["event_type"],
                    event["resource_type"],
                    event.get("resource_id"),
                    event["request_id"],
                    self._jsonb(event.get("metadata_json")),
                ]
            )
        with pooled_connect(self._database_url) as conn:
            rows = conn.execute(
                f"""
                insert into audit_logs (
                    actor_user_id, actor_role, event_type, resource_type, resource_id,
                    request_id, metadata_json, created_at
                )
                values {values_sql}
                returning id, event_type, actor_user_id, actor_role, resource_type,
                          resource_id, request_id, metadata_json, created_at
                """,
                params,
            ).fetchall()
            conn.commit()
        return [
            AuditEvent(
                id=str(row["id"]),
                event_type=row["event_type"],
                actor_user_id=str(row["actor_user_id"]) if row["actor_user_id"] else None,
                actor_role=row["actor_role"],
                resource_type=row["resource_type"],
                resource_id=str(row["resource_id"]) if row["resource_id"] else None,
                request_id=row["request_id"],
                metadata_json=row["metadata_json"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
