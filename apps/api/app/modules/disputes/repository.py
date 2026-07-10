from __future__ import annotations

from app.modules.disputes.memory_repository import InMemoryDisputeRepository
from app.modules.disputes.postgres_repository import PostgresDisputeRepository

__all__ = ["InMemoryDisputeRepository", "PostgresDisputeRepository"]
