from dataclasses import dataclass

import pandas as pd


@dataclass
class CachedDatasetRecord:
    pmid: int
    db_idx: int
    title: str
    summary: str
    organism: str
    experiment_type: str
    gse_code: str
    overall_design: str | None



@dataclass
class DatasetLinkDto:
    pmid: int
    db_ids: list[int]

@dataclass
class DatasetSummaryDto:
    db_idx: int
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
class FetchDataframeResult:
    dataframe: pd.DataFrame
    failed_pmids: list[int]
    no_data_pmids: list[int]