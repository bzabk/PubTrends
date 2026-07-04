import asyncio
import logging
from collections.abc import Awaitable, Callable
from concurrent.futures import ThreadPoolExecutor

import redis.asyncio as aioredis

from api_client.rate_limit_strategies import SlidingWindowStrategy
from src.api_client.api_availability_service import ApiAvailabilityService
from src.api_client.api_data_fetcher import FetchDataService
from src.api_client.async_limiter import AsyncLimiter
from src.api_client.connection_manager import ConnectionManager
from src.api_client.db_cache.redis_dataset_cache_repository import (
    RedisDatasetCacheRepository,
)
from src.api_client.dtos import FetchDataframeResult
from src.api_client.gateways.eutils_gateway import AsyncEutilsGateway
from src.api_client.gateways.ncbi_gateway import AsyncNcbiGateway
from src.exceptions.api_client_exceptions import MissingAPIKeyError

logger = logging.getLogger(__name__)


class ApiClientFacade:
    _executor = ThreadPoolExecutor()

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self._redis_url = redis_url
        self._api_key = None

    def set_api_key(self, api_key: str | None) -> None:
        self._api_key = api_key

    def fetch_dataframe(self, pmids: list[str]) -> FetchDataframeResult:
        if self._api_key is None:
            raise MissingAPIKeyError()
        return self._run_async(lambda: self._fetch_dataframe_async(pmids))

    def check_api_availability(self, api_key: str) -> list[Exception]:
        return self._run_async(lambda: self._check_api_availability_async(api_key))

    def _run_async(self, coroutine_factory: Callable[[], Awaitable]):
        return self._executor.submit(lambda: asyncio.run(coroutine_factory())).result()

    async def _fetch_dataframe_async(self, pmids: list[str]) -> FetchDataframeResult:
        redis_client = aioredis.from_url(self._redis_url)
        cache_repo = RedisDatasetCacheRepository(redis_client=redis_client)
        try:
            await cache_repo.log_cache_status()
            async with ConnectionManager(async_limiter=AsyncLimiter()) as conn:
                eutils_gateway = AsyncEutilsGateway(connector=conn, api_key=self._api_key)
                ncbi_gateway = AsyncNcbiGateway(connector=conn, api_key=self._api_key)
                fetch_data_service = FetchDataService(
                    eutils_gateway=eutils_gateway,
                    ncbi_gateway=ncbi_gateway,
                    cache_repository=cache_repo,
                )
                return await fetch_data_service.fetch_dataframe(pmids)
        finally:
            await redis_client.aclose()

    async def _check_api_availability_async(self, api_key: str) -> list[Exception]:
        async with ConnectionManager(
            async_limiter=AsyncLimiter(strategy=SlidingWindowStrategy())
        ) as connection_manager:
            return await ApiAvailabilityService(connector=connection_manager).check(api_key)
