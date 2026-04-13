import asyncio
import aiohttp
from typing import Any, Literal
from src.exceptions.api_client_exceptions import RequestException, HttpStatusException, SessionNotInitializedError


class ConnectionManager:
    def __init__(
        self,
        async_limiter,
        timeout_s: float = 15.0,
        connector_limit: int = 20,
        retry_attempts: int = 3,
        delay_s: float = 1.0,
    ):
        self._timeout_s = timeout_s
        self._connector_limit = connector_limit
        self.retry_attempts = retry_attempts
        self.delay_s = delay_s
        self._async_limiter = async_limiter
        self._session = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=15)
        connector = aiohttp.TCPConnector(limit=10, limit_per_host=5)
        self._session = aiohttp.ClientSession(
            timeout=timeout,
            connector=connector
        )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def get_json(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self._send_request("GET", url, params=params, response_type="json")

    async def get_text(self, url: str, params: dict[str, Any] | None = None) -> str:
        return await self._send_request("GET", url, params=params, response_type="text")

    async def _send_request(self, method: str, url: str,
                       response_type: Literal["json", "text"],
                       params: dict[str, Any] | None = None) -> dict[str, Any] | str:
        if self._session is None:
            raise SessionNotInitializedError("Session was not Initialized")

        last_error = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                if self._async_limiter is not None:
                    await self._async_limiter.acquire()
                async with self._session.request(method, url, params=params) as response:

                    if response.status >= 400:
                        body = await response.text()
                        raise HttpStatusException(response.status, str(response.url), body)

                    if response_type == "json":
                        return await response.json()
                    else:
                        return await response.text()
            except (aiohttp.ClientError, asyncio.TimeoutError,HttpStatusException) as e:
                last_error = e
                if isinstance(e, HttpStatusException) and 400 <= e.status < 500 and e.status not in (429, 408):
                    raise RequestException(str(e)) from e

                if attempt == self.retry_attempts:
                    break
                await asyncio.sleep(self.delay_s * attempt)

        raise RequestException(str(last_error)) from last_error