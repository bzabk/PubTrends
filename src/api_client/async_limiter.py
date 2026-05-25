from api_client.rate_limit_strategies import FixedDelayStrategy, RateLimiterStrategy


class AsyncLimiter:
    def __init__(self, strategy: RateLimiterStrategy | None = None):
        self._strategy = strategy or FixedDelayStrategy()

    async def acquire(self):
        await self._strategy.acquire()