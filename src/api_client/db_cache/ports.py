from collections.abc import Sequence
from typing import Protocol

from src.api_client.dtos import CachedDatasetRecord, CachedPmidRecords


class DatasetCacheRepository(Protocol):
    async def get(self, pmids: Sequence[str]) -> list[CachedDatasetRecord]: ...

    async def insert(self, entries: Sequence[CachedPmidRecords]) -> None: ...

    async def exists(self, key: str) -> bool: ...
