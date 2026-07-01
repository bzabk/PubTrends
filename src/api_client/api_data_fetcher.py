import asyncio
import itertools
import logging
from dataclasses import asdict

import pandas as pd

from src.api_client.api_dataframe_mapper import ApiDataFrameMapper
from src.api_client.db_cache.ports import DatasetCacheRepository
from src.api_client.dtos import (
    BatchFetchResult,
    CachedDatasetRecord,
    CachedPmidRecords,
    DatasetLinkDto,
    DatasetSummaryDto,
    FetchDataframeResult,
    OverallDesignDto,
    SinglePmidFetchResult,
)
from src.api_client.gateways.eutils_gateway import AsyncEutilsGateway
from src.api_client.gateways.ncbi_gateway import AsyncNcbiGateway
from src.exceptions.api_client_exceptions import (
    GatewayException,
    ParserError,
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
        bulk_size: int = 2
    ):
        self.eutils_gateway = eutils_gateway
        self.ncbi_gateway = ncbi_gateway
        self.cache_repository = cache_repository
        self.concurrency_limit = concurrency_limit
        self.bulk_size = bulk_size
        self.semaphore = asyncio.Semaphore(concurrency_limit)

    async def fetch_dataframe(self, pmids: list[str]) -> FetchDataframeResult:
        logger.info(f"Started fetching data for {len(pmids)} pmids")
        batch_result = await self.fetch_batch(pmids)

        # if batch_result.failed_pmids:
        #     logger.info("")
        #     retry_result = await self.fetch_batch(batch_result.failed_pmids)
        #     all_dataframes = batch_result.partial_dataframes + retry_result.partial_dataframes
        #     final_failed = retry_result.failed_pmids
        #     final_no_data = batch_result.no_data_pmids + retry_result.no_data_pmids
        # else:
        #     all_dataframes = batch_result.partial_dataframes
        #     final_failed = []
        #     final_no_data = batch_result.no_data_pmids
        #
        # result = FetchDataframeResult(
        #     dataframe=ApiDataFrameMapper.combine_dataframes(all_dataframes),
        #     failed_pmids=final_failed,
        #     no_data_pmids=final_no_data,
        # )
        # logger.info(f"")
        # if result.dataframe is not None:
        #     logger.debug("Final combined DataFrame shape: %s", result.dataframe.shape)
        # return result

    async def fetch_batch(self, pmids: list[str]) -> BatchFetchResult:
        try:
            cached_records = await self.cache_repository.get(pmids)
        except (RedisRequestException, CacheSerializationError) as e:
            logger.error("Failed to get cached data from repository, fetching all data from API")
            cached_records = []

        cache_hits = self._extract_hit_pmids(cached_records)
        missing_pmids = [pmid for pmid in pmids if pmid not in set(cache_hits)]

        logger.info(f"Cache: {len(cache_hits)} hits, {len(missing_pmids)} missed")
        logger.info(f"Started retrieval for missed pmids")

        x = await self._fetch_missing(missing_pmids)
        print(x)


    async def _fetch_missing(self,missing_pmids: list[str]) -> None:

        batches  = [missing_pmids[i:i + self.bulk_size] for i in range(0, len(missing_pmids), self.bulk_size)]

        tasks = [self.eutils_gateway.get_dataset_idxs(batch) for batch in batches]
        dataset_links_batches = await asyncio.gather(*tasks)
        dataset_links_flatten = list(itertools.chain.from_iterable( dataset_links_batches))
        unique_indices = {
            idx
            for batch in dataset_links_batches
            for dto in batch
            for idx in dto.db_idx
        }
        db_idx_combined_unique = list(unique_indices)
        #dataset_links = await self.eutils_gateway.get_dataset_idxs(missing_pmids)
        #logger.info("Fetched dataset_links:\n")
        #logger.info(dataset_links)

        dataset_summeries = await self.eutils_gateway.get_dataset_summaries(db_idx_combined_unique)
        gse_code_list = [dataset_summary.gse_code for dataset_summary in dataset_summeries]
        gse_code_list_unique = list(set(gse_code_list))
        overall_data = await asyncio.gather(*(self.ncbi_gateway.get_overall_design(gse_code) for gse_code in gse_code_list_unique))
        df_links = self._dataset_links2dataframe(dataset_links_flatten)
        df_summaries = self._dataclass2dataframe(dataset_summeries)
        df_overall_design = self._dataclass2dataframe(overall_data)
        print(df_summaries)
        df_combined = df_links.merge(df_summaries, on="db_idx", how="left")
        df_combined = df_combined.merge(df_overall_design, left_on="gse_code", right_on="gse_code", how="left")
        logger.info("Combined DataFrame shape: %s", df_combined.shape)
        return df_combined


    def _dataset_links2dataframe(self,dataset_links: list[DatasetLinkDto]) -> pd.DataFrame:
        df = pd.DataFrame([asdict(link) for link in dataset_links])
        df = df.explode("db_idx").reset_index(drop=True)
        return df

    def _dataclass2dataframe(self,dataset_summeries) -> pd.DataFrame:
        return pd.DataFrame([asdict(summary) for summary in dataset_summeries])

    @staticmethod
    def _extract_hit_pmids(records: list[CachedDatasetRecord]) -> list[str]:
        return list(dict.fromkeys(record.pmid for record in records))
