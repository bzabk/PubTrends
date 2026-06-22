import pytest


@pytest.mark.redis
async def test_insert_get_roundtrip(cache_repository, sample_entries):
    await cache_repository.insert(sample_entries)

    cached_records = await cache_repository.get(["11111", "22222"])
    assert len(cached_records) == 3

    by_pmid = {}
    for record in cached_records:
        by_pmid.setdefault(record.pmid, []).append(record)

    assert len(by_pmid["11111"]) == 2
    assert len(by_pmid["22222"]) == 1


@pytest.mark.redis
async def test_exists_after_insert(cache_repository, sample_entries):
    await cache_repository.insert(sample_entries)

    assert await cache_repository.exists("11111") is True
    assert await cache_repository.exists("99999") is False


@pytest.mark.redis
async def test_partial_hit_returns_only_existing(cache_repository, sample_entries):
    await cache_repository.insert(sample_entries)

    cached_records = await cache_repository.get(["22222", "99999"])

    assert len(cached_records) == 1
    assert cached_records[0].pmid == "22222"
    assert cached_records[0].db_idx == "33333"


@pytest.mark.redis
async def test_insert_empty_entries_is_noop(cache_repository):
    await cache_repository.insert([])

    cached_records = await cache_repository.get(["11111"])
    assert cached_records == []


@pytest.mark.redis
async def test_insert_then_get_result_returns_appropriate_records(cache_repository, sample_entries):
    await cache_repository.insert(sample_entries)

    cached_records = await cache_repository.get(["11111", "22222", "33333"])

    assert len(cached_records) == 3
    assert {record.pmid for record in cached_records} == {"11111", "22222"}


@pytest.mark.redis
async def test_get_not_existing_key_returns_empty_list(cache_repository):
    assert await cache_repository.get(["222222"]) == []


@pytest.mark.redis
async def test_get_skips_corrupted_cache_entry_and_returns_empty(cache_repository, redis_client):
    key = cache_repository._make_key("44444")
    await redis_client.set(key, "invalid_data")

    result = await cache_repository.get(["44444"])
    assert result == []
