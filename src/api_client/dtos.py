from dataclasses import dataclass
from typing import Literal

import pandas as pd


@dataclass
class CachedDatasetRecord:
    pmid: str
    db_idx: str
    title: str
    summary: str
    organism: str
    experiment_type: str
    gse_code: str
    overall_design: str | None


@dataclass
class CachedPmidRecords:
    pmid: str
    records: list[CachedDatasetRecord]


@dataclass
class DatasetLinkDto:
    pmid: str
    db_ids: list[str]


@dataclass
class DatasetSummaryDto:
    db_idx: str
    title: str
    summary: str
    organism: str
    experiment_type: str
    gse_code: str


@dataclass
class OverallDesignDto:
    gse_code: str
    overall_design: str | None


@dataclass
class CachedPmidRecords:
    pmid: str
    records: list[CachedDatasetRecord]


@dataclass
class SinglePmidFetchResult:
    pmid: str
    status: Literal["success", "no_data", "failed"]
    records: list[CachedDatasetRecord]
    dataframe: pd.DataFrame | None = None

    @classmethod
    def success(
        cls,
        pmid: str,
        records: list[CachedDatasetRecord],
        dataframe: pd.DataFrame,
    ) -> SinglePmidFetchResult:
        return cls(pmid=pmid, status="success", records=records, dataframe=dataframe)

    @classmethod
    def no_data(cls, pmid: str) -> SinglePmidFetchResult:
        return cls(pmid=pmid, status="no_data", records=[], dataframe=None)

    @classmethod
    def failed(cls, pmid: str) -> SinglePmidFetchResult:
        return cls(pmid=pmid, status="failed", records=[], dataframe=None)


@dataclass
class BatchFetchResult:
    records: list[CachedDatasetRecord]
    partial_dataframes: list[pd.DataFrame]
    failed_pmids: list[str]
    no_data_pmids: list[str]
    cache_hits: list[str]
    cache_misses: list[str]


@dataclass
class FetchDataframeResult:
    dataframe: pd.DataFrame
    failed_pmids: list[str]
    no_data_pmids: list[str]
