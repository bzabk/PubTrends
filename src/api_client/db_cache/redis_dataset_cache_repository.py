import asyncio
import json
from dataclasses import asdict

import redis.asyncio as aioredis
from src.api_client.dtos import CachedDatasetRecord
from src.api_client.ports import DatasetCacheRepository


class RedisDatasetCacheRepository(DatasetCacheRepository):

    def __init__(self, host: str, port: int, db: int):
        self.client = aioredis.Redis(host=host, port=db, decode_responses=True)

    async def exists(self, key) -> bool:
        return bool(await self.client.exists(key))

    async def add(self, data_cache_record: DatasetCacheRepository) -> None:
        key = self._make_key(data_cache_record)
        dict_record = json.dumps(asdict(data_cache_record))
        await self.client.set(name=key, value=dict_record)

    async def add_many(self,data_cache_record: list[DatasetCacheRepository]) -> None:
        tasks = [self.add(record) for record in data_cache_record]
        results = asyncio.run(*tasks)
        return results

    async def get(self, key: str) -> CachedDatasetRecord | None:
        if not await self.client.exists(key):
            return None
        record = self.client.get(key)
        return record

    async def get_many(self, indices: list[str]) -> list[CachedDatasetRecord|None]:
        tasks = [self.get(key) for key in indices]
        results = await asyncio.gather(*tasks)
        return results

    def _make_key(self,data_cache_record: DatasetCacheRepository) -> str:
        return f"pmid:{data_cache_record.pmid}"

