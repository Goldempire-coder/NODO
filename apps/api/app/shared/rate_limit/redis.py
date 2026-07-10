from __future__ import annotations

import redis
from redis.exceptions import NoScriptError


class RedisRateLimiter:
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

    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._allow_script_sha: str | None = None

    def allow(self, key: str, *, max_attempts: int, window_seconds: int) -> bool:
        redis_key = f"rate_limit:{key}"
        if self._allow_script_sha is None:
            self._allow_script_sha = self._client.script_load(self._ALLOW_SCRIPT)
        try:
            allowed = self._client.evalsha(self._allow_script_sha, 1, redis_key, max_attempts, window_seconds)
        except NoScriptError:
            self._allow_script_sha = self._client.script_load(self._ALLOW_SCRIPT)
            allowed = self._client.evalsha(self._allow_script_sha, 1, redis_key, max_attempts, window_seconds)
        return bool(int(allowed))
