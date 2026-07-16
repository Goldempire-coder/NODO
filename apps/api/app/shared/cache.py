from __future__ import annotations

import json
import time
from contextlib import contextmanager
from threading import RLock
from collections.abc import Iterator
from typing import Any

import redis

from app.core.logging import get_logger
from app.shared.logging_redaction import redact_mapping
from app.shared.profiling import current_profile, profile_mark

logger = get_logger("nodo.cache")


class CacheUnavailableError(RuntimeError):
    pass


def _mark_unavailable(operation: str, namespace: str | None = None) -> None:
    profile_mark(current_profile(), "cache:unavailable", time.perf_counter(), {"operation": operation})
    logger.warning(
        "cache_unavailable",
        extra=redact_mapping(
            {
                "event": "cache_unavailable",
                "operation": operation,
                "cache_namespace": namespace,
            }
        ),
    )


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

    def get_many_text(self, keys: list[str]) -> dict[str, str]:
        return {key: value for key in keys if (value := self.get_text(key)) is not None}

    def set_text(self, key: str, value: str, ttl_seconds: int) -> None:
        with self._lock:
            self._items[key] = (time.time() + ttl_seconds, value)

    def set_text_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        with self._lock:
            if self.get_text(key) is not None:
                return False
            self._items[key] = (time.time() + ttl_seconds, value)
            return True

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

    def set_marker(self, key: str, ttl_seconds: int) -> bool:
        self.set_text(f"marker:{key}", "1", ttl_seconds)
        return True

    def existing_markers(self, keys: list[str]) -> set[str] | None:
        marker_keys = {f"marker:{key}": key for key in keys}
        existing = self.get_many_text(list(marker_keys))
        return {marker_keys[key] for key in existing}

    def clear_prefix_debounced(self, prefix: str, *, debounce_key: str, debounce_seconds: int) -> bool:
        if debounce_seconds <= 0 or self.set_text_if_absent(f"debounce:{debounce_key}", "1", debounce_seconds):
            self.clear_prefix(prefix)
            return True
        return False

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
        try:
            payload = self._client.get(key)
            if payload is None:
                return None
            return json.loads(payload)
        except (json.JSONDecodeError, redis.RedisError) as exc:
            raise CacheUnavailableError("redis_get_json_failed") from exc

    def get_text(self, key: str) -> str | None:
        try:
            return self._client.get(key)
        except redis.RedisError as exc:
            raise CacheUnavailableError("redis_get_text_failed") from exc

    def get_many_text(self, keys: list[str]) -> dict[str, str]:
        if not keys:
            return {}
        try:
            values = self._client.mget(keys)
        except redis.RedisError as exc:
            raise CacheUnavailableError("redis_get_many_text_failed") from exc
        return {key: value for key, value in zip(keys, values) if value is not None}

    def set_text(self, key: str, value: str, ttl_seconds: int) -> None:
        try:
            self._client.setex(key, ttl_seconds, value)
        except redis.RedisError as exc:
            raise CacheUnavailableError("redis_set_text_failed") from exc

    def set_text_if_absent(self, key: str, value: str, ttl_seconds: int) -> bool:
        try:
            return bool(self._client.set(key, value, ex=ttl_seconds, nx=True))
        except redis.RedisError as exc:
            raise CacheUnavailableError("redis_set_text_if_absent_failed") from exc

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        try:
            self._client.setex(key, ttl_seconds, json.dumps(value, separators=(",", ":"), sort_keys=True))
        except redis.RedisError as exc:
            raise CacheUnavailableError("redis_set_json_failed") from exc

    def incr(self, key: str) -> int:
        try:
            return int(self._client.incr(key))
        except redis.RedisError as exc:
            raise CacheUnavailableError("redis_incr_failed") from exc

    def clear_prefix(self, prefix: str) -> None:
        try:
            for key in self._client.scan_iter(match=f"{prefix}*"):
                self._client.delete(key)
        except redis.RedisError as exc:
            raise CacheUnavailableError("redis_clear_prefix_failed") from exc

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
        try:
            versioned_key = self._versioned_key(key)
        except CacheUnavailableError:
            _mark_unavailable("version_lookup", self._namespace)
            return None
        started = time.perf_counter()
        local = self._local_cache.get_json_unprofiled(versioned_key)
        profile_mark(current_profile(), "cache:local_get", started)
        if local is not None:
            profile_mark(current_profile(), "cache:hit", time.perf_counter(), {"hit_type": "local"})
            return local
        started = time.perf_counter()
        try:
            shared = self._shared_cache.get_json(versioned_key)
            profile_mark(current_profile(), "cache:shared_get", started)
        except CacheUnavailableError:
            _mark_unavailable("shared_get", self._namespace)
            profile_mark(current_profile(), "cache:hit", time.perf_counter(), {"hit_type": "miss"})
            return None
        if shared is not None:
            self._local_cache.set_json_unprofiled(versioned_key, shared, self._shared_hit_local_ttl_seconds)
            profile_mark(current_profile(), "cache:hit", time.perf_counter(), {"hit_type": "shared"})
            return shared
        profile_mark(current_profile(), "cache:hit", time.perf_counter(), {"hit_type": "miss"})
        return shared

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        try:
            versioned_key = self._versioned_key(key)
        except CacheUnavailableError:
            _mark_unavailable("version_lookup", self._namespace)
            return
        started = time.perf_counter()
        try:
            self._shared_cache.set_json(versioned_key, value, ttl_seconds)
            profile_mark(current_profile(), "cache:set_shared", started)
        except CacheUnavailableError:
            _mark_unavailable("shared_set", self._namespace)
            return
        started = time.perf_counter()
        self._local_cache.set_json_unprofiled(versioned_key, value, ttl_seconds)
        profile_mark(current_profile(), "cache:set_local", started)

    def set_marker(self, key: str, ttl_seconds: int) -> bool:
        marker_key = f"{self._namespace}:marker:{key}"
        try:
            self._shared_cache.set_text(marker_key, "1", ttl_seconds)
            self._local_cache.set_text(marker_key, "1", ttl_seconds)
            return True
        except CacheUnavailableError:
            _mark_unavailable("marker_set", self._namespace)
            return False

    def existing_markers(self, keys: list[str]) -> set[str] | None:
        if not keys:
            return set()
        marker_keys = {f"{self._namespace}:marker:{key}": key for key in keys}
        started = time.perf_counter()
        try:
            existing = self._shared_cache.get_many_text(list(marker_keys))
            profile_mark(current_profile(), "cache:marker_get", started)
        except CacheUnavailableError:
            _mark_unavailable("marker_get", self._namespace)
            return None
        for marker_key in existing:
            self._local_cache.set_text(marker_key, "1", self._shared_hit_local_ttl_seconds)
        return {marker_keys[key] for key in existing}

    def clear_prefix(self, prefix: str) -> None:
        try:
            new_version = str(self._shared_cache.incr(self._version_key))
            with self._version_lock:
                self._cached_version = new_version
                self._cached_version_expires_at = time.time() + self._version_cache_ttl_seconds
            logger.info(
                "cache_invalidation",
                extra=redact_mapping(
                    {
                        "event": "cache_invalidation",
                        "operation": "version_bump",
                        "cache_namespace": self._namespace,
                    }
                ),
            )
        except CacheUnavailableError:
            _mark_unavailable("version_bump", self._namespace)
        self._local_cache.clear_prefix(self._entry_prefix)

    def clear_prefix_debounced(self, prefix: str, *, debounce_key: str, debounce_seconds: int) -> bool:
        if debounce_seconds <= 0:
            self.clear_prefix(prefix)
            return True
        debounce_marker = f"{self._namespace}:debounce:{debounce_key}"
        try:
            should_bump = self._shared_cache.set_text_if_absent(debounce_marker, "1", debounce_seconds)
        except CacheUnavailableError:
            _mark_unavailable("debounce_set", self._namespace)
            self.clear_prefix(prefix)
            return True
        if should_bump:
            self.clear_prefix(prefix)
            return True
        logger.info(
            "cache_invalidation_debounced",
            extra=redact_mapping(
                {
                    "event": "cache_invalidation_debounced",
                    "operation": "version_bump_skipped",
                    "cache_namespace": self._namespace,
                }
            ),
        )
        return False

    @contextmanager
    def lock(self, key: str) -> Iterator[None]:
        started = time.perf_counter()
        with self._local_cache.lock(f"{self._namespace}:lock:{key}"):
            profile_mark(current_profile(), "cache:lock_wait", started)
            yield
