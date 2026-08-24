from __future__ import annotations

import time
from typing import Literal

import redis
from redis.exceptions import NoScriptError, RedisError

from app.core.logging import get_logger
from app.shared.logging_redaction import redact_mapping
from app.shared.rate_limit.in_memory import InMemoryRateLimiter

logger = get_logger("nodo.rate_limit")


class RateLimitUnavailableError(RuntimeError):
    pass


class RedisRateLimiter:
    _REDIS_ERROR_BACKOFF_SECONDS = 30.0
    _ALLOW_SCRIPT = """
    local count = redis.call('INCR', KEYS[1])
    local ttl = redis.call('TTL', KEYS[1])
    if ttl == -1 then
      redis.call('EXPIRE', KEYS[1], tonumber(ARGV[2]))
    end
    if count <= tonumber(ARGV[1]) then
      return 1
    end
    return 0
    """

    def __init__(self, redis_url: str, *, failure_mode: Literal["local", "deny"] = "local") -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._allow_script_sha: str | None = None
        self._fallback = InMemoryRateLimiter()
        self._redis_unavailable_until = 0.0
        self._failure_mode = failure_mode

    def _redis_unavailable_result(self, key: str, *, max_attempts: int, window_seconds: int) -> bool:
        if self._failure_mode == "deny":
            return False
        return self._fallback.allow(key, max_attempts=max_attempts, window_seconds=window_seconds)

    def _allow_redis(self, key: str, *, max_attempts: int, window_seconds: int) -> bool:
        redis_key = f"rate_limit:{key}"
        try:
            if self._allow_script_sha is None:
                self._allow_script_sha = self._client.script_load(self._ALLOW_SCRIPT)
            allowed = self._client.evalsha(self._allow_script_sha, 1, redis_key, max_attempts, window_seconds)
        except NoScriptError:
            self._allow_script_sha = self._client.script_load(self._ALLOW_SCRIPT)
            allowed = self._client.evalsha(self._allow_script_sha, 1, redis_key, max_attempts, window_seconds)
        return bool(int(allowed))

    def _mark_redis_unavailable(self, exc: RedisError) -> None:
        self._redis_unavailable_until = time.time() + self._REDIS_ERROR_BACKOFF_SECONDS
        logger.warning(
            "rate_limiter_redis_unavailable",
            extra=redact_mapping(
                {
                    "event": "rate_limiter_redis_unavailable",
                    "exception_class": exc.__class__.__name__,
                }
            ),
        )

    def allow_shared(self, key: str, *, max_attempts: int, window_seconds: int) -> bool:
        if time.time() < self._redis_unavailable_until:
            raise RateLimitUnavailableError("shared rate limiter unavailable")
        try:
            return self._allow_redis(key, max_attempts=max_attempts, window_seconds=window_seconds)
        except RedisError as exc:
            self._mark_redis_unavailable(exc)
            raise RateLimitUnavailableError("shared rate limiter unavailable") from exc

    def allow(self, key: str, *, max_attempts: int, window_seconds: int) -> bool:
        try:
            return self.allow_shared(key, max_attempts=max_attempts, window_seconds=window_seconds)
        except RateLimitUnavailableError:
            return self._redis_unavailable_result(key, max_attempts=max_attempts, window_seconds=window_seconds)
