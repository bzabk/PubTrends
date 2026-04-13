from dataclasses import dataclass

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
class FetchDataframeResult:
    dataframe: pd.DataFrame
    failed_pmids: list[str]
    no_data_pmids: list[str]