from __future__ import annotations

import os
import time
from queue import Empty, Queue
from threading import Lock
from threading import local

import psycopg

from app.shared.profiling import current_profile, profile_mark


_thread_state = local()
_pools: dict[str, "BoundedConnectionPool"] = {}
_pools_lock = Lock()


class PoolSaturatedError(RuntimeError):
    pass


def connect(database_url: str, **kwargs):  # type: ignore[no-untyped-def]
    kwargs.setdefault("prepare_threshold", None)
    return psycopg.connect(database_url, **kwargs)


class BoundedConnectionPool:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._max_size = max(1, int(os.environ.get("NODO_DB_POOL_MAX_SIZE", "20")))
        self._timeout_seconds = max(1.0, float(os.environ.get("NODO_DB_POOL_TIMEOUT_SECONDS", "10")))
        self._idle: Queue = Queue(maxsize=self._max_size)
        self._lock = Lock()
        self._created = 0

    def acquire(self):  # type: ignore[no-untyped-def]
        try:
            conn = self._idle.get_nowait()
        except Empty:
            conn = self._create_or_wait()
        if conn.closed:
            self._discard_closed()
            return self.acquire()
        return conn

    def release(self, conn) -> None:  # type: ignore[no-untyped-def]
        if conn.closed:
            self._discard_closed()
            return
        try:
            self._idle.put_nowait(conn)
        except Exception:
            conn.close()
            self._discard_closed()

    def _create_or_wait(self):  # type: ignore[no-untyped-def]
        with self._lock:
            if self._created < self._max_size:
                self._created += 1
                should_create = True
            else:
                should_create = False
        if should_create:
            try:
                return connect(self._database_url, row_factory=psycopg.rows.dict_row)
            except Exception:
                with self._lock:
                    self._created = max(0, self._created - 1)
                raise
        try:
            return self._idle.get(timeout=self._timeout_seconds)
        except Empty as exc:
            raise PoolSaturatedError("DB_POOL_SATURATED") from exc

    def _discard_closed(self) -> None:
        with self._lock:
            self._created = max(0, self._created - 1)

    def snapshot(self) -> dict[str, int | float]:
        return {
            "max_size": self._max_size,
            "timeout_seconds": self._timeout_seconds,
            "created": self._created,
            "idle": self._idle.qsize(),
        }


def _pool_for(database_url: str) -> BoundedConnectionPool:
    with _pools_lock:
        pool = _pools.get(database_url)
        if pool is None:
            pool = BoundedConnectionPool(database_url)
            _pools[database_url] = pool
        return pool


class PooledConnectionContext:
    def __init__(self, database_url: str) -> None:
        self._database_url = database_url
        self._conn = None
        self._owns_connection = False

    def __enter__(self):  # type: ignore[no-untyped-def]
        active = getattr(_thread_state, "active_connections", None)
        if active is None:
            active = {}
            _thread_state.active_connections = active
        entry = active.get(self._database_url)
        if entry is not None and not entry["conn"].closed:
            entry["depth"] += 1
            self._conn = entry["conn"]
            self._owns_connection = False
            return self._conn
        started = time.perf_counter()
        conn = _pool_for(self._database_url).acquire()
        profile_mark(current_profile(), "db:acquire", started)
        active[self._database_url] = {"conn": conn, "depth": 1}
        self._conn = conn
        self._owns_connection = True
        return conn

    def __exit__(self, exc_type, exc, tb) -> bool:  # type: ignore[no-untyped-def]
        if self._conn is None:
            return False
        active = getattr(_thread_state, "active_connections", {})
        entry = active.get(self._database_url)
        if entry is not None:
            entry["depth"] -= 1
            if entry["depth"] > 0:
                return False
            active.pop(self._database_url, None)
        if self._conn.closed:
            return False
        try:
            if exc_type is not None:
                self._conn.rollback()
            else:
                self._conn.commit()
        except Exception:
            self._conn.close()
            raise
        finally:
            if self._owns_connection:
                _pool_for(self._database_url).release(self._conn)
        return False


def pooled_connect(database_url: str) -> PooledConnectionContext:
    return PooledConnectionContext(database_url)


def warm_pool(database_url: str, *, size: int) -> None:
    if size <= 0:
        return
    pool = _pool_for(database_url)
    connections = []
    try:
        for _ in range(size):
            connections.append(pool.acquire())
    finally:
        for conn in connections:
            pool.release(conn)


def pool_snapshot(database_url: str) -> dict[str, int | float]:
    return _pool_for(database_url).snapshot()
