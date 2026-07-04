import asyncio
import itertools
import logging
from dataclasses import asdict

import pandas as pd

from src.api_client.api_dataframe_mapper import ApiDataFrameMapper
from src.api_client.db_cache.ports import DatasetCacheRepository
from src.api_client.dtos import (
    CachedDatasetRecord,
    CachedPmidRecords,
    DatasetLinkDto,
    FetchDataframeResult,
)
from src.api_client.gateways.eutils_gateway import AsyncEutilsGateway
from src.api_client.gateways.ncbi_gateway import AsyncNcbiGateway
from src.exceptions.api_client_exceptions import (
    CacheSerializationError,
    RedisRequestException,
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
        first_result = await self.fetch_batch(pmids)

        if not first_result.failed_pmids:
            return first_result

        logger.info(f"Retrying {len(first_result.failed_pmids)} failed pmids")
        retry_result = await self.fetch_batch(first_result.failed_pmids)

        combined_df = pd.concat([first_result.dataframe, retry_result.dataframe], ignore_index=True)
        return FetchDataframeResult(
            dataframe=combined_df,
            failed_pmids=retry_result.failed_pmids,
            no_data_pmids=first_result.no_data_pmids + retry_result.no_data_pmids,
        )

    async def fetch_batch(self, pmids: list[str]) -> FetchDataframeResult:
        try:
            cached_records = await self.cache_repository.get(pmids)
        except (RedisRequestException, CacheSerializationError):
            logger.error("Failed to get cached data from repository, fetching all data from API")
            cached_records = []

        cache_hits = self._extract_hit_pmids(cached_records) if cached_records else []
        missing_pmids = [pmid for pmid in pmids if pmid not in set(cache_hits)]

        logger.info(f"Cache: {len(cache_hits)} hits, {len(missing_pmids)} missed")
        logger.info("Started retrieval for missed pmids")

        missing_result = await self._fetch_missing(missing_pmids)
        await self._save_to_cache(missing_result.dataframe)

        cached_df = ApiDataFrameMapper.records_to_dataframe(cached_records)
        combined_df = ApiDataFrameMapper.combine_dataframes([cached_df, missing_result.dataframe])
        return FetchDataframeResult(
            dataframe=combined_df,
            failed_pmids=missing_result.failed_pmids,
            no_data_pmids=missing_result.no_data_pmids,
        )


    async def _fetch_missing(self, missing_pmids: list[str]) -> FetchDataframeResult:
        if not missing_pmids:
            return FetchDataframeResult(dataframe=pd.DataFrame(), failed_pmids=[], no_data_pmids=[])
        batches = [missing_pmids[i:i + self.bulk_size] for i in range(0, len(missing_pmids), self.bulk_size)]

        results = await asyncio.gather(
            *(self.eutils_gateway.get_dataset_idxs(batch) for batch in batches)
        )

        dataset_links = list(itertools.chain.from_iterable(r.dataset_links for r in results))
        failed_pmids = list(itertools.chain.from_iterable(r.failed_pmids for r in results))
        no_data_pmids = list(itertools.chain.from_iterable(r.no_data_pmids for r in results))

        logger.info(f"Found {len(no_data_pmids)} pmids with no datalinks: {no_data_pmids}")
        logger.warning(f"Failed to fetch {len(failed_pmids)} pmids: {failed_pmids}")

        unique_indices = list({idx for link in dataset_links for idx in link.db_idx})

        dataset_summeries = await self.eutils_gateway.get_dataset_summaries(unique_indices)
        gse_code_list_unique = list({s.gse_code for s in dataset_summeries})
        overall_data = await asyncio.gather(
            *(self.ncbi_gateway.get_overall_design(gse_code) for gse_code in gse_code_list_unique)
        )

        df_links = self._dataset_links2dataframe(dataset_links)
        df_summaries = self._dataclass2dataframe(dataset_summeries)
        df_overall_design = self._dataclass2dataframe(overall_data)

        df_combined = df_links.merge(df_summaries, on="db_idx", how="left")

        dropped_esummary = df_combined[df_combined["title"].isna()]["pmid"].unique().tolist()
        if dropped_esummary:
            logger.warning(f"Dropping {len(dropped_esummary)} pmids due to failed esummary: {dropped_esummary}")
        df_combined = df_combined.dropna(subset=["title"])

        df_combined = df_combined.merge(df_overall_design, on="gse_code", how="left")

        dropped_overall_design = df_combined[df_combined["overall_design"].isna()]["pmid"].unique().tolist()
        if dropped_overall_design:
            logger.warning(f"Dropping {len(dropped_overall_design)} pmids due to failed overall_design: {dropped_overall_design}")
        df_combined = df_combined.dropna(subset=["overall_design"])

        df_combined = df_combined.rename(columns={
            "pmid": "Pmid",
            "title": "Title",
            "summary": "Summary",
            "organism": "Organism",
            "experiment_type": "Experiment_type",
            "gse_code": "GSE_code",
            "overall_design": "Overall_design",
        })

        logger.info(f"DataFrame shape: {df_combined.shape}")
        return FetchDataframeResult(dataframe=df_combined, failed_pmids=failed_pmids, no_data_pmids=no_data_pmids)


    async def _save_to_cache(self, dataframe: pd.DataFrame) -> None:
        if dataframe.empty:
            return
        records = ApiDataFrameMapper.dataframe_to_records(dataframe)
        records_by_pmid: dict[str, list[CachedDatasetRecord]] = {}
        for record in records:
            records_by_pmid.setdefault(record.pmid, []).append(record)
        entries = [CachedPmidRecords(pmid=pmid, records=recs) for pmid, recs in records_by_pmid.items()]
        try:
            await self.cache_repository.insert(entries)
            logger.info(f"Cached {len(entries)} pmids to Redis")
        except Exception as e:
            logger.error(f"Failed to save data to cache: {e}")

    def _dataset_links2dataframe(self, dataset_links: list[DatasetLinkDto]) -> pd.DataFrame:
        if not dataset_links:
            return pd.DataFrame(columns=["pmid", "db_idx"])
        df = pd.DataFrame([asdict(link) for link in dataset_links])
        df = df.explode("db_idx").reset_index(drop=True)
        return df

    def _dataclass2dataframe(self,dataset_summeries) -> pd.DataFrame:
        return pd.DataFrame([asdict(summary) for summary in dataset_summeries])

    @staticmethod
    def _extract_hit_pmids(records: list[CachedDatasetRecord]) -> list[str]:
        return list(dict.fromkeys(record.pmid for record in records))
