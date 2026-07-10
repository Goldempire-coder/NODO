from __future__ import annotations

from dataclasses import asdict

from app.core.config import Settings
from app.repositories.database import DatabaseRepository
from app.repositories.redis import RedisRepository


class HealthService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._database = DatabaseRepository(settings.database_url)
        self._redis = RedisRepository(settings.redis_url)

    def health(self) -> dict:
        return {
            "status": "ok",
            "service": self._settings.app_name,
            "version": self._settings.app_version,
            "build_id": self._settings.build_id,
        }

    def version(self) -> dict:
        return {
            "service": self._settings.app_name,
            "version": self._settings.app_version,
            "build_id": self._settings.build_id,
            "environment": self._settings.app_env,
        }

    def readiness(self) -> tuple[bool, dict]:
        database = self._database.check_connectivity()
        redis = self._redis.check_connectivity()
        checks = {
            "database": asdict(database),
            "redis": asdict(redis),
        }
        return database.ok and redis.ok, {"status": "ready" if database.ok and redis.ok else "not_ready", "checks": checks}
