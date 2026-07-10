from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import RLock


class InMemoryRateLimiter:
    def __init__(self) -> None:
        self._lock = RLock()
        self._attempts: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str, *, max_attempts: int, window_seconds: int) -> bool:
        now = time.time()
        with self._lock:
            attempts = self._attempts[key]
            while attempts and attempts[0] <= now - window_seconds:
                attempts.popleft()
            if len(attempts) >= max_attempts:
                return False
            attempts.append(now)
            return True
