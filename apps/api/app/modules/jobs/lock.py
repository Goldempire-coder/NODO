from __future__ import annotations

from datetime import timedelta
from threading import RLock

import redis

from app.modules.jobs.models import utc_now


class InMemoryJobLockManager:
    def __init__(self) -> None:
        self._lock = RLock()
        self._locks: dict[str, tuple[str, object]] = {}

    def acquire(self, key: str, owner: str, ttl_seconds: int) -> bool:
        now = utc_now()
        with self._lock:
            existing = self._locks.get(key)
            if existing is not None:
                _, expires_at = existing
                if expires_at > now:
                    return False
            self._locks[key] = (owner, now + timedelta(seconds=ttl_seconds))
            return True

    def release(self, key: str, owner: str) -> None:
        with self._lock:
            existing = self._locks.get(key)
            if existing and existing[0] == owner:
                self._locks.pop(key, None)


class RedisJobLockManager:
    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def acquire(self, key: str, owner: str, ttl_seconds: int) -> bool:
        return bool(self._client.set(key, owner, nx=True, ex=ttl_seconds))

    def release(self, key: str, owner: str) -> None:
        self._client.eval(
            """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            end
            return 0
            """,
            1,
            key,
            owner,
        )
