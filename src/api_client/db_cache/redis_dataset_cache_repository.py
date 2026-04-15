import json
from collections.abc import Sequence
from dataclasses import asdict

import redis.asyncio as aioredis
from redis import RedisError

from src.api_client.dtos import CachedDatasetRecord, CachedPmidRecords
from src.api_client.ports import DatasetCacheRepository
from src.exceptions.api_client_exceptions import (
    CacheSerializationError,
    RedisRequestException,
)


class RedisDatasetCacheRepository(DatasetCacheRepository):
    def __init__(self, redis_client: aioredis.Redis):
        self._client = redis_client
        self._key_prefix = "pmid"
        self._key_suffix = "dataset_details"

    async def exists(self, key: str) -> bool:
        try:
            return bool(await self._client.exists(self._make_key(key)))
        except RedisError as e:
            raise RedisRequestException(
                f"Redis exists operation failed for key: {key}"
            ) from e

    async def insert(self, entries: Sequence[CachedPmidRecords]) -> None:
        if not entries:
            return
        try:
            key_value_pairs = {
                self._make_key(entry.pmid): self._serialize(entry.records)
                for entry in entries
                if entry.records
            }
        except CacheSerializationError as e:
            raise CacheSerializationError(
                "Failed to serialize cache records before Redis insert"
            ) from e
        if not key_value_pairs:
            return
        try:
            await self._client.mset(key_value_pairs)
        except RedisError as e:
            raise RedisRequestException("Redis insert operation failed") from e

    async def get(self, pmids: Sequence[str]) -> list[CachedDatasetRecord]:
        if not pmids:
            return []
        keys = [self._make_key(pmid) for pmid in pmids]
        try:
            raw_values = await self._client.mget(keys)
        except RedisError as e:
            raise RedisRequestException("Redis get operation failed") from e

        results = []
        for key, raw_value in zip(keys, raw_values, strict=False):
            if raw_value is not None:
                try:
                    results.extend(self._deserialize(raw_value))
                except CacheSerializationError as e:
                    raise CacheSerializationError(
                        f"Failed to deserialize cached value for key: {key}"
                    ) from e
        return results

    def _make_key(self, pmid: str) -> str:
        return f"{self._key_prefix}:{pmid}:{self._key_suffix}"

    def _serialize(self, records: Sequence[CachedDatasetRecord]) -> str:
        try:
            return json.dumps([asdict(record) for record in records])
        except TypeError as e:
            raise CacheSerializationError(
                "Failed to serialize cached dataset records"
            ) from e

    def _deserialize(self, raw_value: str) -> list[CachedDatasetRecord]:
        try:
            decoded = json.loads(raw_value)
            return [CachedDatasetRecord(**item) for item in decoded]
        except (json.JSONDecodeError, TypeError) as e:
            raise CacheSerializationError(
                "Failed to deserialize cached dataset records"
            ) from e
