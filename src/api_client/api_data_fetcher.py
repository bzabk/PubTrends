import asyncio
import logging

import pandas as pd

from src.api_client.api_dataframe_mapper import ApiDataFrameMapper
from src.api_client.db_cache.ports import DatasetCacheRepository
from src.api_client.dtos import (
    BatchFetchResult,
    CachedDatasetRecord,
    CachedPmidRecords,
    FetchDataframeResult,
    SinglePmidFetchResult,
)
from src.api_client.gateways.eutils_gateway import AsyncEutilsGateway
from src.api_client.gateways.ncbi_gateway import AsyncNcbiGateway
from src.exceptions.api_client_exceptions import (
    CacheSerializationError,
    PermanentException,
    RedisRequestException,
    TransientException,
)

logger = logging.getLogger(__name__)


class FetchDataService:
    def __init__(
        self,
        eutils_gateway: AsyncEutilsGateway,
        ncbi_gateway: AsyncNcbiGateway,
        cache_repository: DatasetCacheRepository,
        concurrency_limit: int = 5,
    ):
        self.eutils_gateway = eutils_gateway
        self.ncbi_gateway = ncbi_gateway
        self.cache_repository = cache_repository
        self.concurrency_limit = concurrency_limit
        self.semaphore = asyncio.Semaphore(concurrency_limit)

    async def fetch_dataframe(self, pmids: list[str]) -> FetchDataframeResult:
        logger.info("Starting fetch for %d PMIDs", len(pmids))
        batch_result = await self.fetch_batch(pmids)

        if batch_result.failed_pmids:
            logger.info("Retrying %d failed PMIDs", len(batch_result.failed_pmids))
            retry_result = await self.fetch_batch(batch_result.failed_pmids)
            all_dataframes = batch_result.partial_dataframes + retry_result.partial_dataframes
            final_failed = retry_result.failed_pmids
            final_no_data = batch_result.no_data_pmids + retry_result.no_data_pmids
        else:
            all_dataframes = batch_result.partial_dataframes
            final_failed = []
            final_no_data = batch_result.no_data_pmids

        result = FetchDataframeResult(
            dataframe=ApiDataFrameMapper.combine_dataframes(all_dataframes),
            failed_pmids=final_failed,
            no_data_pmids=final_no_data,
        )
        logger.info(
            "Fetch complete: %d datasets, %d failed, %d no_data",
            len(result.dataframe) if result.dataframe is not None else 0,
            len(final_failed),
            len(final_no_data),
        )
        if result.dataframe is not None:
            logger.debug("Final combined DataFrame shape: %s", result.dataframe.shape)
        return result

    async def fetch_batch(self, pmids: list[str]) -> BatchFetchResult:
        try:
            cached_records = await self.cache_repository.get(pmids)
        except (RedisRequestException, CacheSerializationError) as e:
            logger.error("Cache unavailable, fetching all PMIDs from API: %s", e)
            cached_records = []

        cache_hits = self._extract_hit_pmids(cached_records)
        missing_pmids = [pmid for pmid in pmids if pmid not in set(cache_hits)]
        logger.info("Cache: %d hits, %d misses", len(cache_hits), len(missing_pmids))
        logger.info("Starting bakup retrieval for %d",len(missing_pmids))
        logger.info("Missed pmids:")
        logger.info(missing_pmids)
        tasks = [self._fetch_single_pmid_semaphore(pmid) for pmid in missing_pmids]
        single_pmid_results = await asyncio.gather(*tasks)

        fresh_records: list[CachedDatasetRecord] = []
        cache_entries: list[CachedPmidRecords] = []
        partial_dataframes: list[pd.DataFrame] = []
        failed_pmids: list[str] = []
        no_data_pmids: list[str] = []

        for result in single_pmid_results:
            if result.status == "success":
                fresh_records.extend(result.records)
                cache_entries.append(CachedPmidRecords(pmid=result.pmid, records=result.records))
                if result.dataframe is not None and not result.dataframe.empty:
                    partial_dataframes.append(result.dataframe)
            elif result.status == "no_data":
                no_data_pmids.append(result.pmid)
            else:
                failed_pmids.append(result.pmid)

        await self.cache_repository.insert(cache_entries)

        cached_dataframe = ApiDataFrameMapper.records_to_dataframe(cached_records)
        if not cached_dataframe.empty:
            partial_dataframes.insert(0, cached_dataframe)

        return BatchFetchResult(
            records=fresh_records,
            partial_dataframes=partial_dataframes,
            failed_pmids=failed_pmids,
            no_data_pmids=no_data_pmids,
            cache_hits=cache_hits,
            cache_misses=missing_pmids,
        )

    async def _fetch_single_pmid_semaphore(self, pmid: str) -> SinglePmidFetchResult:
        async with self.semaphore:
            return await self._fetch_single_pmid(pmid)

    async def _fetch_single_pmid(self, pmid: str) -> SinglePmidFetchResult:
        try:
            dataset_link = await self.eutils_gateway.get_dataset_idx(pmid)
            if not dataset_link.db_ids:
                return SinglePmidFetchResult.no_data(pmid)

            summaries = await asyncio.gather(
                *(self.eutils_gateway.get_dataset_summary(db_id) for db_id in dataset_link.db_ids)
            )
            if not summaries:
                return SinglePmidFetchResult.no_data(pmid)

            overall_designs = await asyncio.gather(
                *(self.ncbi_gateway.get_overall_design(summary.gse_code) for summary in summaries)
            )

            single_pmid_df = ApiDataFrameMapper.create_dataframe_from_single_pmid(
                pmid=pmid,
                summaries=summaries,
                overall_designs=overall_designs,
            )
            if single_pmid_df.empty:
                return SinglePmidFetchResult.no_data(pmid)

            logger.debug("PMID %s: single_pmid_df shape %s", pmid, single_pmid_df.shape)
            records = ApiDataFrameMapper.dataframe_to_records(single_pmid_df)
            return SinglePmidFetchResult.success(pmid, records, single_pmid_df)
        except TransientException as e:
            logger.warning("Transient failure for PMID %s: %s", pmid, e)
            return SinglePmidFetchResult.failed(pmid)
        except PermanentException as e:
            logger.warning("Permanent failure for PMID %s (no retry): %s", pmid, e)
            return SinglePmidFetchResult.no_data(pmid)

    @staticmethod
    def _extract_hit_pmids(records: list[CachedDatasetRecord]) -> list[str]:
        return list(dict.fromkeys(record.pmid for record in records))
