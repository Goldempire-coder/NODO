from __future__ import annotations

from app.modules.credits.memory_repository import InMemoryCreditRepository
from app.modules.credits.postgres_repository import PostgresCreditRepository


__all__ = ["InMemoryCreditRepository", "PostgresCreditRepository"]
