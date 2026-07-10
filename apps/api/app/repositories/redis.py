from __future__ import annotations

from app.core.network import ConnectivityResult, socket_check


class RedisRepository:
    def __init__(self, redis_url: str) -> None:
        self._redis_url = redis_url

    def check_connectivity(self) -> ConnectivityResult:
        try:
            from redis import Redis

            client = Redis.from_url(self._redis_url, socket_connect_timeout=0.35, socket_timeout=0.35)
            client.ping()
            return ConnectivityResult(True)
        except ImportError:
            return socket_check(self._redis_url, default_port=6379)
        except Exception:
            return ConnectivityResult(False, "UPSTREAM_UNAVAILABLE", "Connection failed.")
