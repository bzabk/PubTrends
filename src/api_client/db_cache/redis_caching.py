import json
from typing import Any

import redis.asyncio as aioredis
import os

from src.api_client.ports import DatasetCacheRepository


class RedisCaching(DatasetCacheRepository):

    def __init__(self, host: str | None = None, port: int | None = None, db: int | None = None):
        resolved_host = host if host is not None else os.getenv("REDIS_HOST", "localhost")
        resolved_port = port if port is not None else int(os.getenv("REDIS_PORT", "6379"))
        resolved_db = db if db is not None else int(os.getenv("REDIS_DB", "0"))
        self.host = resolved_host
        self.port = resolved_port
        self.db = resolved_db
        self.client = aioredis.Redis(host=resolved_host, port=resolved_port, db=resolved_db, decode_responses=True)

    async def exists(self, key):
        return bool(await self.client.exists(key))

    async def add(self, key: str, value: str) -> int:
        return await self.client.sadd(key, value)

    async def get(self, indices: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index in indices:
            raws = await self.client.smembers(index)
            for raw in raws:
                data = json.loads(raw)
                data['Pmid'] = index
                rows.append(data)
        return rows
