from __future__ import annotations

import hashlib
import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Iterator
from uuid import uuid4

import redis

from app.core.errors import ApiError


def _profile_mark(profile: list[dict[str, Any]] | None, stage: str, started: float) -> None:
    if profile is not None:
        profile.append({"stage": stage, "elapsed_ms": round((time.perf_counter() - started) * 1000, 4)})


@dataclass(frozen=True)
class IdempotencyRecord:
    payload_hash: str
    response: dict[str, Any]
    expires_at: float


@dataclass
class _KeyLock:
    lock: Any = field(default_factory=RLock)
    users: int = 0


def canonical_payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class InMemoryIdempotencyStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._records: dict[str, IdempotencyRecord] = {}
        self._key_locks: dict[str, _KeyLock] = {}

    @contextmanager
    def _lock_key(self, key: str) -> Iterator[None]:
        # Count waiters too: never replace a lock while another caller still owns it.
        with self._lock:
            entry = self._key_locks.setdefault(key, _KeyLock())
            entry.users += 1
        try:
            with entry.lock:
                yield
        finally:
            with self._lock:
                entry.users -= 1
                if entry.users == 0:
                    del self._key_locks[key]

    def get(self, key: str) -> IdempotencyRecord | None:
        now = time.time()
        with self._lock:
            record = self._records.get(key)
            if record is None:
                return None
            if record.expires_at <= now:
                self._records.pop(key, None)
                return None
            return record

    def put(self, key: str, *, payload_hash: str, response: dict[str, Any], ttl_seconds: int = 86_400) -> None:
        with self._lock_key(key), self._lock:
            self._records[key] = IdempotencyRecord(
                payload_hash=payload_hash,
                response=response,
                expires_at=time.time() + ttl_seconds,
            )

    def replay_or_store(self, key: str | None, *, payload: dict[str, Any], compute, profile: list[dict[str, Any]] | None = None) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        if not key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        payload_hash = canonical_payload_hash(payload)
        with self._lock_key(key):
            started = time.perf_counter()
            record = self.get(key)
            _profile_mark(profile, "idempotency:get_existing", started)
            if record is not None:
                if record.payload_hash != payload_hash:
                    raise ApiError("IDEMPOTENCY_PAYLOAD_MISMATCH", status_code=409)
                return record.response
            response = compute()
            started = time.perf_counter()
            self.put(key, payload_hash=payload_hash, response=response)
            _profile_mark(profile, "idempotency:store_response", started)
            return response


class RedisIdempotencyStore:
    def __init__(self, redis_url: str) -> None:
        self._client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> IdempotencyRecord | None:
        raw = self._client.get(f"idempotency:{key}")
        if not raw:
            return None
        data = json.loads(raw)
        return IdempotencyRecord(
            payload_hash=data["payload_hash"],
            response=data["response"],
            expires_at=float(data["expires_at"]),
        )

    def put(self, key: str, *, payload_hash: str, response: dict[str, Any], ttl_seconds: int = 86_400) -> None:
        expires_at = time.time() + ttl_seconds
        self._client.setex(
            f"idempotency:{key}",
            ttl_seconds,
            json.dumps({"payload_hash": payload_hash, "response": response, "expires_at": expires_at}, default=str),
        )

    def _put_and_release_lock(self, key: str, lock_key: str, token: str, *, payload_hash: str, response: dict[str, Any], ttl_seconds: int = 86_400) -> None:
        expires_at = time.time() + ttl_seconds
        encoded = json.dumps({"payload_hash": payload_hash, "response": response, "expires_at": expires_at}, default=str)
        self._client.eval(
            """
            redis.call('setex', KEYS[1], ARGV[1], ARGV[2])
            if redis.call('get', KEYS[2]) == ARGV[3] then
                redis.call('del', KEYS[2])
            end
            return 1
            """,
            2,
            f"idempotency:{key}",
            lock_key,
            ttl_seconds,
            encoded,
            token,
        )

    def _get_or_lock(self, key: str, lock_key: str, token: str) -> tuple[str, str | None]:
        result = self._client.eval(
            """
            local existing = redis.call('get', KEYS[1])
            if existing then
                return {'existing', existing}
            end
            if redis.call('setnx', KEYS[2], ARGV[1]) == 1 then
                redis.call('expire', KEYS[2], ARGV[2])
                return {'locked', false}
            end
            return {'busy', false}
            """,
            2,
            f"idempotency:{key}",
            lock_key,
            token,
            30,
        )
        status = str(result[0])
        raw_record = result[1] if len(result) > 1 and result[1] else None
        return status, raw_record

    def _decode_record(self, raw: str) -> IdempotencyRecord:
        data = json.loads(raw)
        return IdempotencyRecord(
            payload_hash=data["payload_hash"],
            response=data["response"],
            expires_at=float(data["expires_at"]),
        )

    def replay_or_store(self, key: str | None, *, payload: dict[str, Any], compute, profile: list[dict[str, Any]] | None = None) -> dict[str, Any]:  # type: ignore[no-untyped-def]
        if not key:
            raise ApiError("IDEMPOTENCY_KEY_REQUIRED", status_code=400)
        payload_hash = canonical_payload_hash(payload)
        lock_key = f"idempotency_lock:{key}"
        token = str(uuid4())
        started = time.perf_counter()
        status, raw_record = self._get_or_lock(key, lock_key, token)
        _profile_mark(profile, "idempotency:get_or_lock", started)
        if status == "existing" and raw_record:
            started = time.perf_counter()
            record = self._decode_record(raw_record)
            _profile_mark(profile, "idempotency:decode_existing", started)
            if record.payload_hash != payload_hash:
                raise ApiError("IDEMPOTENCY_PAYLOAD_MISMATCH", status_code=409)
            return record.response
        if status == "locked":
            lock_released = False
            try:
                response = compute()
                started = time.perf_counter()
                self._put_and_release_lock(key, lock_key, token, payload_hash=payload_hash, response=response)
                _profile_mark(profile, "idempotency:store_and_release_lock", started)
                lock_released = True
                return response
            finally:
                if not lock_released and self._client.get(lock_key) == token:
                    self._client.delete(lock_key)

        deadline = time.time() + 10
        started = time.perf_counter()
        while time.time() < deadline:
            time.sleep(0.05)
            record = self.get(key)
            if record is None:
                continue
            if record.payload_hash != payload_hash:
                raise ApiError("IDEMPOTENCY_PAYLOAD_MISMATCH", status_code=409)
            _profile_mark(profile, "idempotency:wait_for_existing", started)
            return record.response
        _profile_mark(profile, "idempotency:wait_timeout", started)
        raise ApiError("IDEMPOTENCY_CONFLICT", status_code=409)
