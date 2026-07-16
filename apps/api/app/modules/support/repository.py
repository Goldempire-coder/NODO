from __future__ import annotations

from app.modules.support.memory_repository import InMemorySupportRepository
from app.modules.support.postgres_repository import PostgresSupportRepository

__all__ = ["InMemorySupportRepository", "PostgresSupportRepository"]
