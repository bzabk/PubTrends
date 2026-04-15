import os

import pytest
import pytest_asyncio
import redis.asyncio as aioredis

from src.api_client.db_cache.redis_dataset_cache_repository import (
    RedisDatasetCacheRepository,
)
from src.api_client.dtos import CachedDatasetRecord, CachedPmidRecords


@pytest_asyncio.fixture
async def redis_client():
    host = os.getenv("TEST_REDIS_HOST", "localhost")
    port = int(os.getenv("TEST_REDIS_PORT", "6379"))
    db = int(os.getenv("TEST_REDIS_DB", "15"))

    client = aioredis.Redis(host=host, port=port, db=db, decode_responses=True)
    yield client

    await client.flushdb()
    await client.aclose()


@pytest.fixture
def cache_repository(redis_client):
    return RedisDatasetCacheRepository(redis_client)


@pytest.fixture
def sample_entries():
    return [
        CachedPmidRecords(
            pmid="11111",
            records=[
                CachedDatasetRecord(
                    pmid="11111",
                    db_idx="22222",
                    title="title_1",
                    summary="summary_1",
                    organism="organism_1",
                    experiment_type="experiment_type_1",
                    gse_code="gse_1",
                    overall_design="design_1",
                ),
                CachedDatasetRecord(
                    pmid="11111",
                    db_idx="33333",
                    title="title_2",
                    summary="summary_2",
                    organism="organism_2",
                    experiment_type="experiment_type_2",
                    gse_code="gse_2",
                    overall_design="design_2",
                ),
            ],
        ),
        CachedPmidRecords(
            pmid="22222",
            records=[
                CachedDatasetRecord(
                    pmid="22222",
                    db_idx="33333",
                    title="title_3",
                    summary="summary_3",
                    organism="organism_3",
                    experiment_type="experiment_type_3",
                    gse_code="gse_3",
                    overall_design="design_3",
                )
            ],
        ),
    ]
