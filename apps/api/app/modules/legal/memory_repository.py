from __future__ import annotations

from threading import RLock

from app.modules.legal.models import (
    BusinessLegalAcceptanceRecord,
    new_id,
    utc_now,
)


class InMemoryBusinessLegalAcceptanceRepository:
    def __init__(self) -> None:
        self._lock = RLock()
        self.acceptances: dict[tuple[str, str, str, str], BusinessLegalAcceptanceRecord] = {}

    def list_for_business_user(self, *, business_id: str, user_id: str) -> list[BusinessLegalAcceptanceRecord]:
        with self._lock:
            items = [
                acceptance
                for key, acceptance in self.acceptances.items()
                if key[0] == business_id and key[1] == user_id
            ]
        return sorted(items, key=lambda item: item.accepted_at, reverse=True)

    def get_for_document(
        self,
        *,
        business_id: str,
        user_id: str,
        document_set: str,
        document_version: str,
    ) -> BusinessLegalAcceptanceRecord | None:
        return self.acceptances.get((business_id, user_id, document_set, document_version))

    def record_acceptance(
        self,
        *,
        business_id: str,
        user_id: str,
        document_set: str,
        document_version: str,
        confirmation: str,
        surface: str,
        locale: str,
        request_id: str,
    ) -> BusinessLegalAcceptanceRecord:
        key = (business_id, user_id, document_set, document_version)
        with self._lock:
            existing = self.acceptances.get(key)
            if existing is not None:
                return existing
            now = utc_now()
            acceptance = BusinessLegalAcceptanceRecord(
                id=new_id(),
                business_id=business_id,
                user_id=user_id,
                document_set=document_set,
                document_version=document_version,
                confirmation=confirmation,
                surface=surface,
                locale=locale,
                request_id=request_id,
                accepted_at=now,
                created_at=now,
            )
            self.acceptances[key] = acceptance
            return acceptance
