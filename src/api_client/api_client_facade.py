import asyncio
from src.api_client.api_availability_service import ApiAvailabilityService
from src.api_client.async_limiter import AsyncLimiter
from src.api_client.api_data_fetcher import FetchDataService
from src.api_client.dtos import FetchDataframeResult
from src.api_client.connection_manager import ConnectionManager
from src.api_client.gateways.eutils_gateway import AsyncEutilsGateway
from src.api_client.gateways.ncbi_gateway import AsyncNcbiGateway
from src.exceptions.api_client_exceptions import MissingAPIKeyError


class ApiClientFacade:
    def __init__(self, redis_client, api_key: str | None = None):
        self._redis_client = redis_client
        self._api_key = api_key

    def set_api_key(self, api_key: str | None) -> None:
        self._api_key = api_key

    def fetch_dataframe(self, pmids: list[str]) -> FetchDataframeResult:
        if self._api_key is None:
            raise MissingAPIKeyError()
        try:
            return asyncio.run(self._fetch_dataframe_async(pmids))
        except Exception as e:
            pass

    def check_api_availability(self) -> None:
        asyncio.run(self._check_api_availability_async())

    async def _fetch_dataframe_async(self, pmids: list[str]) -> FetchDataframeResult:
        async with ConnectionManager(async_limiter=AsyncLimiter()) as conn:
            eutils_gateway = AsyncEutilsGateway(connector=conn,
                                                api_key=self._api_key)
            ncbi_gateway = AsyncNcbiGateway(connector=conn,
                                            api_key=self._api_key)

            fetch_data_service = FetchDataService(
                eutils_gateway=eutils_gateway,
                ncbi_gateway=ncbi_gateway,
                cache_repository=self._redis_client,
            )
            return await fetch_data_service.fetch_dataframe(pmids)

    async def _check_api_availability_async(self) -> None:
        async with ConnectionManager(async_limiter=AsyncLimiter()) as connection_manager:
            await ApiAvailabilityService(connector=connection_manager).check()