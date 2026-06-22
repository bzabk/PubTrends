import asyncio
import time
from abc import ABC, abstractmethod
from collections import deque


class RateLimiterStrategy(ABC):
    @abstractmethod
    async def acquire(self) -> None: ...


class FixedDelayStrategy(RateLimiterStrategy):
    def __init__(self, delay: float = 0.125):
        self._lock = asyncio.Lock()
        self._delay_between_requests = delay
        self._next_allowed_at = 0

    async def acquire(self):

        async with self._lock:
            now = time.monotonic()
            scheduled_at = max(now, self._next_allowed_at)
            self._next_allowed_at = scheduled_at + self._delay_between_requests
        delay = scheduled_at - now
        if delay > 0:
            await asyncio.sleep(delay)


class SlidingWindowStrategy(RateLimiterStrategy):
    def __init__(self, max_requests: int = 10, window: float = 1.0):
        self._lock = asyncio.Lock()
        self._api_calls_timestamps = deque()
        self._max_deque_size = max_requests
        self._release_time = window

    async def acquire(self):
        while True:
            async with self._lock:
                api_request_timestamp = time.monotonic()
                while (
                    self._api_calls_timestamps
                    and api_request_timestamp - self._api_calls_timestamps[0] > self._release_time
                ):
                    self._api_calls_timestamps.popleft()
                if len(self._api_calls_timestamps) < self._max_deque_size:
                    self._api_calls_timestamps.append(api_request_timestamp)
                    return
                time_left = self._release_time - (api_request_timestamp - self._api_calls_timestamps[0])
            if time_left > 0:
                await asyncio.sleep(time_left)
