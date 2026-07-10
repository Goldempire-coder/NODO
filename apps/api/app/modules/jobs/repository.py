from __future__ import annotations

from app.modules.jobs.memory_repository import InMemoryJobRepository
from app.modules.jobs.postgres_repository import PostgresJobRepository

__all__ = ["InMemoryJobRepository", "PostgresJobRepository"]
