import asyncio
import time
from collections import deque


class AsyncLimiter:
    def __init__(self, max_deque_size: int = 10, release_time: float = 1.0):
        self._lock = asyncio.Lock()
        self._api_calls_timestamps = deque()
        self._max_deque_size = max_deque_size
        self._release_time = release_time
        self._delay_between_requests = 0.125
        self._last_request = None
        self._next_allowed_at = 0

    async def acquire(self):

        async with self._lock:
            now = time.monotonic()
            scheduled_at = max(now, self._next_allowed_at)
            self._next_allowed_at = scheduled_at + self._delay_between_requests
        delay = scheduled_at - now
        if delay > 0:
            await asyncio.sleep(delay)
