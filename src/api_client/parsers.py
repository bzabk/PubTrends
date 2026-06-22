from typing import Any
from xml.parsers.expat import ExpatError

import xmltodict

from src.api_client.dtos import DatasetLinkDto, DatasetSummaryDto, OverallDesignDto
from src.exceptions.api_client_exceptions import ParserError


def parse_pmid_to_dbidx(response_result: dict[str, Any], pmid: str) -> DatasetLinkDto:
    try:
        db_ids = response_result["linksets"][0]["linksetdbs"][0]["links"]
    except (KeyError, IndexError, TypeError) as e:
        raise ParserError(f"Failed to parse dbidx for {pmid}") from e
    return DatasetLinkDto(pmid=pmid, db_ids=db_ids)


def parse_dataset_summary(response_result: dict[str, Any], db_idx: str) -> DatasetSummaryDto:
    try:
        item = response_result["result"][db_idx]
        return DatasetSummaryDto(
            db_idx=db_idx,
            title=item["title"],
            summary=item["summary"],
            organism=item["taxon"],
            experiment_type=item["gdstype"],
            gse_code=item["accession"],
        )
    except (KeyError, TypeError) as e:
        raise ParserError(f"Failed to parse dataset summary for {db_idx}") from e


def parse_overall_design(xml_text: str, gse_code: str) -> OverallDesignDto:
    try:
        data = xmltodict.parse(xml_text)
        overall_design = data["MINiML"]["Series"].get("Overall-Design")
    except (KeyError, TypeError, AttributeError, ExpatError) as e:
        raise ParserError(f"Failed to parse XML response for {gse_code}") from e
    return OverallDesignDto(
        gse_code=gse_code,
        overall_design=overall_design,
    )
