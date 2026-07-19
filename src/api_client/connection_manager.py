import asyncio
import contextlib
import json
import logging
import re
from typing import Any, Literal

import aiohttp
from yarl import URL

from src.exceptions.api_client_exceptions import (
    ApiUnavailableException,
    HttpStatusException,
    InvalidApiKeyException,
    RequestException,
    SessionNotInitializedError,
)

logger = logging.getLogger(__name__)


class ConnectionManager:
    def __init__(
        self,
        async_limiter,
        timeout_s: float = 15.0,
        connector_limit: int = 20,
        semaphore_size: int = 20,
        retry_attempts: int = 3,
        delay_s: float = 0.05,
    ):
        self._timeout_s = timeout_s
        self._connector_limit = connector_limit
        self.retry_attempts = retry_attempts
        self.delay_s = delay_s
        self._async_limiter = async_limiter
        self._semaphore = asyncio.Semaphore(semaphore_size)
        self._session = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=self._timeout_s)
        connector = aiohttp.TCPConnector(limit=self._connector_limit)
        self._session = aiohttp.ClientSession(timeout=timeout, connector=connector)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def get_json(self, url: str, params) -> dict[str, Any]:
        return await self._send_request("GET", url, params=params, response_type="json")

    async def get_text(self, url: str, params) -> str:
        return await self._send_request("GET", url, params=params, response_type="text")

    async def _send_request(
        self,
        method: str,
        url: str,
        response_type: Literal["json", "text"],
        params,
    ) -> dict[str, Any] | str:
        if self._session is None:
            raise SessionNotInitializedError("Session was not initialized")

        last_error = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                logger.debug("GET %s (attempt %d/%d)", url, attempt, self.retry_attempts)
                if self._async_limiter is not None:
                    await self._async_limiter.acquire()

                async with self._semaphore, self._session.request(method, url, params=params) as response:
                    logger.info("Request sent:")
                    logger.info(self._redact_api_key(str(response.url)))
                    if response.status >= 400:
                        error_text = await response.text()
                        error_data = {}
                        with contextlib.suppress(json.JSONDecodeError):
                            error_data = json.loads(error_text)

                        if error_data.get("error") == "API key invalid":
                            raise InvalidApiKeyException()

                        if error_data.get("ERROR") == "Couldn't resolve #exLinkSrv2, the address table is empty.":
                            raise ApiUnavailableException()

                        raise HttpStatusException()

                    if response_type == "json":
                        return await response.json()
                    return await response.text()

            except (InvalidApiKeyException, ApiUnavailableException):
                raise

            except Exception as exc:
                last_error = exc
                if attempt == self.retry_attempts:
                    break
                delay = self.delay_s * attempt
                safe_url = self._redact_api_key(str(URL(url).with_query(params)))
                logger.warning(
                    f"Request failed (attempt {attempt}/{self.retry_attempts}), "
                    f"retrying in {delay:.1f}s: {safe_url}: {exc}"
                )
                await asyncio.sleep(delay)

        logger.error(f"Request failed after {self.retry_attempts} attempts: {url}")
        raise RequestException("Request failed after retries") from last_error

    @staticmethod
    def _redact_api_key(full_url: str) -> str:
        return re.sub(r"[?&]api_key=[^&]*", "", full_url)
