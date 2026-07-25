from __future__ import annotations

from redis.exceptions import NoScriptError, ResponseError

from app.shared.rate_limit.in_memory import InMemoryRateLimiter
from app.shared.rate_limit.redis import RedisRateLimiter


def _limiter_with_client(client: object) -> RedisRateLimiter:
    limiter = RedisRateLimiter.__new__(RedisRateLimiter)
    limiter._client = client
    limiter._allow_script_sha = None
    limiter._fallback = InMemoryRateLimiter()
    limiter._redis_unavailable_until = 0.0
    return limiter


class ScriptLoadFailingRedis:
    def __init__(self) -> None:
        self.script_load_calls = 0

    def script_load(self, _script: str) -> str:
        self.script_load_calls += 1
        raise ResponseError("max requests limit exceeded")


class EvalFailingRedis:
    def __init__(self) -> None:
        self.evalsha_calls = 0

    def script_load(self, _script: str) -> str:
        return "sha"

    def evalsha(self, *_args: object) -> int:
        self.evalsha_calls += 1
        raise ResponseError("max requests limit exceeded")


class NoScriptThenAllowedRedis:
    def __init__(self) -> None:
        self.evalsha_calls = 0
        self.script_load_calls = 0

    def script_load(self, _script: str) -> str:
        self.script_load_calls += 1
        return f"sha-{self.script_load_calls}"

    def evalsha(self, *_args: object) -> int:
        self.evalsha_calls += 1
        if self.evalsha_calls == 1:
            raise NoScriptError("NOSCRIPT")
        return 1


def test_redis_rate_limiter_falls_back_when_script_load_hits_provider_limit() -> None:
    client = ScriptLoadFailingRedis()
    limiter = _limiter_with_client(client)

    assert limiter.allow("admin:dashboard:user", max_attempts=1, window_seconds=60) is True
    assert limiter.allow("admin:dashboard:user", max_attempts=1, window_seconds=60) is False
    assert client.script_load_calls == 1


def test_redis_rate_limiter_falls_back_when_eval_hits_provider_limit() -> None:
    client = EvalFailingRedis()
    limiter = _limiter_with_client(client)

    assert limiter.allow("admin:login:user", max_attempts=2, window_seconds=60) is True
    assert limiter.allow("admin:login:user", max_attempts=2, window_seconds=60) is True
    assert limiter.allow("admin:login:user", max_attempts=2, window_seconds=60) is False
    assert client.evalsha_calls == 1


def test_redis_rate_limiter_keeps_noscript_retry_behavior() -> None:
    client = NoScriptThenAllowedRedis()
    limiter = _limiter_with_client(client)

    assert limiter.allow("admin:login:user", max_attempts=1, window_seconds=60) is True
    assert client.script_load_calls == 2
    assert client.evalsha_calls == 2
