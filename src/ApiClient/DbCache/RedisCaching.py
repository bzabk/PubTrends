import json
from typing import Any

import redis.asyncio as aioredis
import os


class RedisCaching:

    def __init__(self):
        host = os.getenv("REDIS_HOST", "localhost")
        self.client = aioredis.Redis(host=host, port=6379, db=0, decode_responses=True)

    async def check_if_exists(self, key):
        return bool(await self.client.exists(key))

    async def sadd(self, key: str, value: str) -> int:
        return await self.client.sadd(key, value)

    async def get_dataframe_from_redis(self, indices: list[str]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index in indices:
            raws = await self.client.smembers(index)
            for raw in raws:
                data = json.loads(raw)
                data['Pmid'] = index
                rows.append(data)
        return rows
