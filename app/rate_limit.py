import time
from collections import deque

from fastapi import HTTPException


class SlidingWindowLimiter:
    def __init__(self, max_hits: int, window_sec: float):
        self.max_hits = max_hits
        self.window_sec = window_sec
        self._hits: deque[float] = deque()

    def check(self) -> None:
        now = time.monotonic()
        while self._hits and now - self._hits[0] > self.window_sec:
            self._hits.popleft()
        if len(self._hits) >= self.max_hits:
            raise HTTPException(
                status_code=429,
                detail="Слишком много запросов. Подождите минуту.",
            )
        self._hits.append(now)
