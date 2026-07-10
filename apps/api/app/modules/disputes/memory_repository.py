from __future__ import annotations

from threading import RLock
from typing import Any

from app.modules.disputes.models import DisputeEventRecord, DisputeRecord, new_id, utc_now


class InMemoryDisputeRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.disputes: dict[str, DisputeRecord] = {}
        self.events: list[DisputeEventRecord] = []

    def get_open_for_order(self, order_id: str) -> DisputeRecord | None:
        for dispute in self.disputes.values():
            if dispute.order_id == order_id and dispute.status in {"open", "in_review"}:
                return dispute
        return None

    def list_open_order_ids(self, order_ids: list[str]) -> set[str]:
        if not order_ids:
            return set()
        wanted = set(order_ids)
        return {
            dispute.order_id
            for dispute in self.disputes.values()
            if dispute.order_id in wanted and dispute.status in {"open", "in_review"}
        }

    def create_dispute(
        self,
        *,
        order_id: str,
        opened_by_user_id: str,
        opened_by_role: str,
        previous_order_status: str,
        reason: str,
        description: str | None,
    ) -> DisputeRecord:
        with self._lock:
            existing = self.get_open_for_order(order_id)
            if existing is not None:
                return existing
            now = utc_now()
            dispute = DisputeRecord(
                id=new_id(),
                order_id=order_id,
                opened_by_user_id=opened_by_user_id,
                opened_by_role=opened_by_role,
                previous_order_status=previous_order_status,
                reason=reason,
                description=description,
                created_at=now,
                updated_at=now,
            )
            self.disputes[dispute.id] = dispute
            return dispute

    def add_event(self, *, dispute_id: str, order_id: str, actor_user_id: str, actor_role: str, event_type: str, old_status: str | None, new_status: str | None, reason: str | None, metadata_json: dict | None) -> DisputeEventRecord:
        event = DisputeEventRecord(
            id=new_id(),
            dispute_id=dispute_id,
            order_id=order_id,
            actor_user_id=actor_user_id,
            actor_role=actor_role,
            event_type=event_type,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            metadata_json=metadata_json,
        )
        with self._lock:
            self.events.append(event)
        return event

    def list_disputes(self, *, status: str | None, cursor: str | None, limit: int) -> tuple[list[DisputeRecord], str | None]:
        items = list(self.disputes.values())
        if status:
            items = [item for item in items if item.status == status]
        if cursor:
            items = [item for item in items if item.created_at.isoformat() < cursor]
        items.sort(key=lambda item: item.created_at, reverse=True)
        page = items[:limit]
        return page, page[-1].created_at.isoformat() if len(page) == limit else None

    def get_dispute(self, dispute_id: str) -> DisputeRecord | None:
        return self.disputes.get(dispute_id)

    def update_dispute(self, dispute: DisputeRecord, **fields: Any) -> DisputeRecord:
        with self._lock:
            for key, value in fields.items():
                setattr(dispute, key, value)
            dispute.updated_at = utc_now()
            return dispute

    def list_events(self, dispute_id: str) -> list[DisputeEventRecord]:
        return sorted([event for event in self.events if event.dispute_id == dispute_id], key=lambda event: event.created_at)
