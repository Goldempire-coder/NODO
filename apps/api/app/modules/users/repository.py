from __future__ import annotations

from app.modules.users.memory_repository import InMemoryUserRepository
from app.modules.users.postgres_repository import PostgresUserRepository

__all__ = ["InMemoryUserRepository", "PostgresUserRepository"]
