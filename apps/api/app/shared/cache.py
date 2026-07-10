from __future__ import annotations

import json
import time
from contextlib import contextmanager
from threading import RLock
from collections.abc import Iterator
from typing import Any

import redis

from app.shared.profiling import current_profile, profile_mark


class InMemoryTTLCache:
    def __init__(self) -> None:
        self._items: dict[str, tuple[float, str]] = {}
        self._key_locks: dict[str, RLock] = {}
        self._lock = RLock()

    def get_json(self, key: str) -> dict[str, Any] | None:
        return self._get_json(key, profile_enabled=True)

    def get_json_unprofiled(self, key: str) -> dict[str, Any] | None:
        return self._get_json(key, profile_enabled=False)

    def _get_json(self, key: str, *, profile_enabled: bool) -> dict[str, Any] | None:
        started = time.perf_counter()
        with self._lock:
            item = self._items.get(key)
            if item is None:
                if profile_enabled:
                    profile_mark(current_profile(), "cache:local_get", started)
                    profile_mark(current_profile(), "cache:hit", time.perf_counter(), {"hit_type": "miss"})
                return None
            expires_at, payload = item
            if expires_at <= time.time():
                self._items.pop(key, None)
                if profile_enabled:
                    profile_mark(current_profile(), "cache:local_get", started)
                    profile_mark(current_profile(), "cache:hit", time.perf_counter(), {"hit_type": "miss"})
                return None
            if profile_enabled:
                profile_mark(current_profile(), "cache:local_get", started)
                profile_mark(current_profile(), "cache:hit", time.perf_counter(), {"hit_type": "local"})
            return json.loads(payload)

    def get_text(self, key: str) -> str | None:
        with self._lock:
            item = self._items.get(key)
            if item is None:
                return None
            expires_at, payload = item
            if expires_at <= time.time():
                self._items.pop(key, None)
                return None
            return payload

    def set_text(self, key: str, value: str, ttl_seconds: int) -> None:
        with self._lock:
            self._items[key] = (time.time() + ttl_seconds, value)

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self._set_json(key, value, ttl_seconds, profile_enabled=True)

    def set_json_unprofiled(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self._set_json(key, value, ttl_seconds, profile_enabled=False)

    def _set_json(self, key: str, value: dict[str, Any], ttl_seconds: int, *, profile_enabled: bool) -> None:
        started = time.perf_counter()
        with self._lock:
            self._items[key] = (time.time() + ttl_seconds, json.dumps(value, separators=(",", ":"), sort_keys=True))
        if profile_enabled:
            profile_mark(current_profile(), "cache:set_local", started)

    def incr(self, key: str) -> int:
        with self._lock:
            current = self.get_text(key)
            value = int(current or "0") + 1
            self._items[key] = (time.time() + 86_400, str(value))
            return value

    def clear_prefix(self, prefix: str) -> None:
        with self._lock:
            for key in list(self._items):
                if key.startswith(prefix):
                    self._items.pop(key, None)

    @contextmanager
    def lock(self, key: str) -> Iterator[None]:
        started = time.perf_counter()
        with self._lock:
            key_lock = self._key_locks.setdefault(key, RLock())
        with key_lock:
            profile_mark(current_profile(), "cache:lock_wait", started)
            yield


class RedisTTLCache:
    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)
        self._key_locks: dict[str, RLock] = {}
        self._lock = RLock()

    def get_json(self, key: str) -> dict[str, Any] | None:
        payload = self._client.get(key)
        if payload is None:
            return None
        return json.loads(payload)

    def get_text(self, key: str) -> str | None:
        return self._client.get(key)

    def set_text(self, key: str, value: str, ttl_seconds: int) -> None:
        self._client.setex(key, ttl_seconds, value)

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        self._client.setex(key, ttl_seconds, json.dumps(value, separators=(",", ":"), sort_keys=True))

    def incr(self, key: str) -> int:
        return int(self._client.incr(key))

    def clear_prefix(self, prefix: str) -> None:
        for key in self._client.scan_iter(match=f"{prefix}*"):
            self._client.delete(key)

    @contextmanager
    def lock(self, key: str) -> Iterator[None]:
        with self._lock:
            key_lock = self._key_locks.setdefault(key, RLock())
        with key_lock:
            yield


class VersionedLayeredTTLCache:
    def __init__(
        self,
        *,
        local_cache: InMemoryTTLCache,
        shared_cache: RedisTTLCache,
        namespace: str,
        version_cache_ttl_seconds: float = 0,
        shared_hit_local_ttl_seconds: int = 1,
    ) -> None:
        self._local_cache = local_cache
        self._shared_cache = shared_cache
        self._namespace = namespace
        self._version_key = f"{namespace}:version"
        self._entry_prefix = f"{namespace}:entry:"
        self._version_cache_ttl_seconds = max(0.0, version_cache_ttl_seconds)
        self._shared_hit_local_ttl_seconds = max(1, shared_hit_local_ttl_seconds)
        self._version_lock = RLock()
        self._cached_version: str | None = None
        self._cached_version_expires_at = 0.0

    def _version(self) -> str:
        now = time.time()
        with self._version_lock:
            if self._cached_version is not None and self._cached_version_expires_at > now:
                profile_mark(current_profile(), "cache:version_cached", time.perf_counter())
                return self._cached_version
        started = time.perf_counter()
        version = self._shared_cache.get_text(self._version_key) or "0"
        profile_mark(current_profile(), "cache:version_lookup", started)
        if self._version_cache_ttl_seconds > 0:
            with self._version_lock:
                self._cached_version = version
                self._cached_version_expires_at = now + self._version_cache_ttl_seconds
        return version

    def _versioned_key(self, key: str) -> str:
        return f"{self._entry_prefix}v{self._version()}:{key}"

    def get_json(self, key: str) -> dict[str, Any] | None:
        versioned_key = self._versioned_key(key)
        started = time.perf_counter()
        local = self._local_cache.get_json_unprofiled(versioned_key)
        profile_mark(current_profile(), "cache:local_get", started)
        if local is not None:
            profile_mark(current_profile(), "cache:hit", time.perf_counter(), {"hit_type": "local"})
            return local
        started = time.perf_counter()
        shared = self._shared_cache.get_json(versioned_key)
        profile_mark(current_profile(), "cache:shared_get", started)
        if shared is not None:
            self._local_cache.set_json_unprofiled(versioned_key, shared, self._shared_hit_local_ttl_seconds)
            profile_mark(current_profile(), "cache:hit", time.perf_counter(), {"hit_type": "shared"})
            return shared
        profile_mark(current_profile(), "cache:hit", time.perf_counter(), {"hit_type": "miss"})
        return shared

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        versioned_key = self._versioned_key(key)
        started = time.perf_counter()
        self._local_cache.set_json_unprofiled(versioned_key, value, ttl_seconds)
        profile_mark(current_profile(), "cache:set_local", started)
        started = time.perf_counter()
        self._shared_cache.set_json(versioned_key, value, ttl_seconds)
        profile_mark(current_profile(), "cache:set_shared", started)

    def clear_prefix(self, prefix: str) -> None:
        new_version = str(self._shared_cache.incr(self._version_key))
        with self._version_lock:
            self._cached_version = new_version
            self._cached_version_expires_at = time.time() + self._version_cache_ttl_seconds
        self._local_cache.clear_prefix(self._entry_prefix)

    @contextmanager
    def lock(self, key: str) -> Iterator[None]:
        started = time.perf_counter()
        with self._local_cache.lock(f"{self._namespace}:lock:{key}"):
            profile_mark(current_profile(), "cache:lock_wait", started)
            yield
