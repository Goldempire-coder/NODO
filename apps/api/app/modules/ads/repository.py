from __future__ import annotations

from app.modules.ads.memory_repository import InMemoryAdRepository
from app.modules.ads.postgres_repository import PostgresAdRepository

__all__ = ["InMemoryAdRepository", "PostgresAdRepository"]
