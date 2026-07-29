from __future__ import annotations

from threading import RLock
from typing import Any

from app.shared.db.connection import pooled_connect


AttentionResourceKey = tuple[str, str]


class InMemorySurfaceAttentionReadRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self._records: dict[tuple[str, str, str, str], str] = {}

    def get_acknowledged_signatures(
        self,
        *,
        user_id: str,
        surface: str,
        resources: list[AttentionResourceKey],
    ) -> dict[AttentionResourceKey, str]:
        if not resources:
            return {}
        with self._lock:
            return {
                (kind, resource_id): signature
                for kind, resource_id in resources
                if (signature := self._records.get((user_id, surface, kind, resource_id))) is not None
            }

    def mark_acknowledged(
        self,
        *,
        user_id: str,
        surface: str,
        resource_kind: str,
        resource_id: str,
        signature: str,
    ) -> None:
        with self._lock:
            self._records[(user_id, surface, resource_kind, resource_id)] = signature


class PostgresSurfaceAttentionReadRepository:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url

    def _connect(self):  # type: ignore[no-untyped-def]
        return pooled_connect(self._database_url)

    def get_acknowledged_signatures(
        self,
        *,
        user_id: str,
        surface: str,
        resources: list[AttentionResourceKey],
    ) -> dict[AttentionResourceKey, str]:
        if not resources:
            return {}
        clauses: list[str] = []
        params: list[Any] = [user_id, surface]
        for kind, resource_id in resources:
            clauses.append("(resource_kind = %s and resource_id = %s)")
            params.extend([kind, resource_id])
        sql = f"""
            select resource_kind, resource_id, signature
            from surface_attention_read_state
            where user_id = %s
              and surface = %s
              and ({' or '.join(clauses)})
        """
        with self._connect() as conn:
            rows = conn.execute(sql, params).fetchall()
        return {
            (str(row["resource_kind"]), str(row["resource_id"])): str(row["signature"])
            for row in rows
        }

    def mark_acknowledged(
        self,
        *,
        user_id: str,
        surface: str,
        resource_kind: str,
        resource_id: str,
        signature: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                insert into surface_attention_read_state (
                    user_id, surface, resource_kind, resource_id, signature,
                    acknowledged_at, created_at, updated_at
                )
                values (%s, %s, %s, %s, %s, now(), now(), now())
                on conflict (user_id, surface, resource_kind, resource_id)
                do update set
                    signature = excluded.signature,
                    acknowledged_at = excluded.acknowledged_at,
                    updated_at = excluded.updated_at
                """,
                (user_id, surface, resource_kind, resource_id, signature),
            )
            conn.commit()
