from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import RLock


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = RLock()
        self._attempts: dict[str, deque[float]] = defaultdict(deque)
        self._expires_at: dict[str, float] = {}
        self._next_cleanup = 0.0

    def allow(self, key: str, *, max_attempts: int, window_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            if now >= self._next_cleanup:
                expired = [
                    key for key, deadline in self._expires_at.items() if deadline <= now
                ]
                for expired_key in expired:
                    self._attempts.pop(expired_key, None)
                    self._expires_at.pop(expired_key, None)
                self._next_cleanup = now + 60
            attempts = self._attempts[key]
            while attempts and attempts[0] <= now - window_seconds:
                attempts.popleft()
            if len(attempts) >= max_attempts:
                return False
            attempts.append(now)
            self._expires_at[key] = now + window_seconds
            return True
