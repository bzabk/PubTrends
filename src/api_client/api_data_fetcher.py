import asyncio

import pandas as pd

from src.api_client.dtos import (
    BatchFetchResult,
    CachedDatasetRecord,
    CachedPmidRecords,
    DatasetSummaryDto,
    FetchDataframeResult,
    OverallDesignDto,
    SinglePmidFetchResult,
)
from src.api_client.gateways.eutils_gateway import AsyncEutilsGateway
from src.api_client.gateways.ncbi_gateway import AsyncNcbiGateway
from src.api_client.db_cache.ports import DatasetCacheRepository

from src.exceptions.api_client_exceptions import GatewayException, CacheSerializationError, ParserError, \
    RedisRequestException


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
        batch_result = await self.fetch_batch(pmids)
        combined_dataframe = self._combine_dataframes(batch_result.partial_dataframes)
        return FetchDataframeResult(
            dataframe=combined_dataframe,
            failed_pmids=batch_result.failed_pmids,
            no_data_pmids=batch_result.no_data_pmids,
        )

    async def fetch_batch(self, pmids: list[str]) -> BatchFetchResult:
        cached_records = await self.cache_repository.get(pmids)
        cache_hits = self._extract_hit_pmids(cached_records)
        missing_pmids = [pmid for pmid in pmids if pmid not in set(cache_hits)]

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
                cache_entries.append(
                    CachedPmidRecords(pmid=result.pmid, records=result.records)
                )
                if result.dataframe is not None and not result.dataframe.empty:
                    partial_dataframes.append(result.dataframe)
            elif result.status == "no_data":
                no_data_pmids.append(result.pmid)
            else:
                failed_pmids.append(result.pmid)

        await self.cache_repository.insert(cache_entries)

        cached_dataframe = self._records_to_dataframe(cached_records)
        if not cached_dataframe.empty:
            partial_dataframes.insert(0, cached_dataframe)

        return BatchFetchResult(
            records=fresh_records,
            partial_dataframes=partial_dataframes,
            failed_pmids=failed_pmids,
            no_data_pmids=no_data_pmids,
            cache_hits=[],
            cache_misses=[],
        )

    async def _fetch_single_pmid_semaphore(self, pmid: str) -> SinglePmidFetchResult:
        async with self.semaphore:
            return await self._fetch_single_pmid(pmid)

    def _create_dataframe_from_single_pmid(
        self,
        pmid: str,
        summaries: list[DatasetSummaryDto],
        overall_designs: list[OverallDesignDto],
    ) -> pd.DataFrame:
        if not summaries or not overall_designs or not pmid:
            return pd.DataFrame(columns=self._dataframe_columns())

        summary_rows = [
            {
                "db_idx": summary.db_idx,
                "Title": summary.title,
                "Summary": summary.summary,
                "Organism": summary.organism,
                "Experiment_type": summary.experiment_type,
                "GSE_code": summary.gse_code,
            }
            for summary in summaries
        ]
        overall_design_rows = [
            {
                "GSE_code": overall_design.gse_code,
                "Overall_design": overall_design.overall_design,
            }
            for overall_design in overall_designs
        ]
        pmid_rows = [
            {
                "Pmid": int(pmid),
                "db_idx": int(summary.db_idx),
            }
            for summary in summaries
        ]

        summary_df = pd.DataFrame(summary_rows).drop_duplicates(subset=["db_idx"])
        overall_design_df = pd.DataFrame(overall_design_rows).drop_duplicates(
            subset=["GSE_code"]
        )
        pmid_df = pd.DataFrame(pmid_rows)

        return pmid_df.merge(summary_df, on="db_idx", how="left").merge(
            overall_design_df, on="GSE_code", how="left"
        )

    async def _fetch_single_pmid(self, pmid: str) -> SinglePmidFetchResult:
        try:
            dataset_link = await self.eutils_gateway.get_dataset_idx(pmid)
            if not dataset_link.db_ids:
                return SinglePmidFetchResult.no_data(pmid)

            summaries = await asyncio.gather(
                *(
                    self.eutils_gateway.get_dataset_summary(db_id)
                    for db_id in dataset_link.db_ids
                )
            )
            if not summaries:
                return SinglePmidFetchResult.no_data(pmid)

            overall_designs = await asyncio.gather(
                *(
                    self.ncbi_gateway.get_overall_design(summary.gse_code)
                    for summary in summaries
                )
            )

            single_pmid_df = self._create_dataframe_from_single_pmid(
                pmid=pmid,
                summaries=summaries,
                overall_designs=overall_designs,
            )
            if single_pmid_df.empty:
                return SinglePmidFetchResult.no_data(pmid)

            records = self._dataframe_to_records(single_pmid_df)
            return SinglePmidFetchResult.success(pmid, records, single_pmid_df)
        except (
            CacheSerializationError,
            GatewayException,
            ParserError,
            RedisRequestException,
        ):
            return SinglePmidFetchResult.failed(pmid)

    def _combine_dataframes(self, dataframes: list[pd.DataFrame]) -> pd.DataFrame:
        filtered_dataframes = [
            dataframe
            for dataframe in dataframes
            if dataframe is not None and not dataframe.empty
        ]
        if not filtered_dataframes:
            return pd.DataFrame(columns=self._dataframe_columns())
        return pd.concat(filtered_dataframes, axis=0, ignore_index=True)

    def _records_to_dataframe(self, records: list[CachedDatasetRecord]) -> pd.DataFrame:
        if not records:
            return pd.DataFrame(columns=self._dataframe_columns())

        rows = [
            {
                "Pmid": record.pmid,
                "db_idx": record.db_idx,
                "Title": record.title,
                "Summary": record.summary,
                "Organism": record.organism,
                "Experiment_type": record.experiment_type,
                "GSE_code": record.gse_code,
                "Overall_design": record.overall_design,
            }
            for record in records
        ]
        return pd.DataFrame(rows, columns=self._dataframe_columns())

    def _dataframe_to_records(
        self, dataframe: pd.DataFrame
    ) -> list[CachedDatasetRecord]:
        return [
            CachedDatasetRecord(
                pmid=row.Pmid,
                db_idx=row.db_idx,
                title=row.Title,
                summary=row.Summary,
                organism=row.Organism,
                experiment_type=row.Experiment_type,
                gse_code=row.GSE_code,
                overall_design=row.Overall_design,
            )
            for row in dataframe.itertuples(index=False)
        ]

    def _extract_hit_pmids(self, records: list[CachedDatasetRecord]) -> list[str]:
        return list(dict.fromkeys(record.pmid for record in records))

    def _dataframe_columns(self) -> list[str]:
        return [
            "Pmid",
            "db_idx",
            "Title",
            "Summary",
            "Organism",
            "Experiment_type",
            "GSE_code",
            "Overall_design",
        ]
