import asyncio
import time
from collections import deque


class AsyncLimiter:
    def __init__(self, max_deque_size: int = 10, release_time: float = 1.0):
        self._lock = asyncio.Lock()
        self._api_calls_timestamps = deque()
        self._max_deque_size = max_deque_size
        self._release_time = release_time
    async def acquire(self):
        while True:
            async with self._lock:
                api_request_timestamp = time.monotonic()
                while self._api_calls_timestamps and api_request_timestamp-self._api_calls_timestamps[0] > self._release_time:
                    self._api_calls_timestamps.popleft()
                if len(self._api_calls_timestamps)<self._max_deque_size:
                    self._api_calls_timestamps.append(api_request_timestamp)
                    return
                time_left = self._release_time - (api_request_timestamp-self._api_calls_timestamps[0])
            if time_left > 0:
                await asyncio.sleep(time_left)



