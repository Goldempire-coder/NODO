from app.modules.legal.memory_repository import (
    InMemoryBusinessLegalAcceptanceRepository,
)
from app.modules.legal.postgres_repository import (
    PostgresBusinessLegalAcceptanceRepository,
)

__all__ = ["InMemoryBusinessLegalAcceptanceRepository", "PostgresBusinessLegalAcceptanceRepository"]
