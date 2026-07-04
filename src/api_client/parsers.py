import logging
from typing import Any

import xmltodict

from src.api_client.dtos import DatasetLinkDto, DatasetSummaryDto, OverallDesignDto
from src.exceptions.api_client_exceptions import ParserError

logger = logging.getLogger(__name__)


def parse_pmids_to_dbidx(response_result: dict[str, Any], pmids: list[str]) -> list[DatasetLinkDto] | None:
    try:
        linksets = response_result["linksets"]
    except Exception:
        logger.warning(f"Failed to parse response for pmids: {pmids}")
        return None

    db_ids_by_pmid: dict[str, list[str]] = {}
    for linkset in linksets:
        ids = linkset.get("ids") or []
        if not ids:
            continue
        source_pmid = ids[0]
        links: list[str] = []
        for linksetdb in linkset.get("linksetdbs", []):
            if linksetdb.get("linkname") == "pubmed_gds":
                links = linksetdb.get("links", [])
                break
        db_ids_by_pmid[source_pmid] = links

    return [DatasetLinkDto(pmid=pmid, db_idx=db_ids_by_pmid.get(pmid, [])) for pmid in pmids]


def parse_dataset_summaries(response_result: dict[str, Any], db_ids: list[str]) -> list[DatasetSummaryDto]:
    try:
        result = response_result["result"]
    except Exception as e:
        raise ParserError("Failed to parse esummary batch response") from e

    summaries: list[DatasetSummaryDto] = []
    for db_idx in db_ids:
        item = result.get(db_idx)
        if not isinstance(item, dict):
            continue
        try:
            summaries.append(
                DatasetSummaryDto(
                    db_idx=db_idx,
                    title=item["title"],
                    summary=item["summary"],
                    organism=item["taxon"],
                    experiment_type=item["gdstype"],
                    gse_code=item["accession"],
                )
            )
        except KeyError:
            continue
    return summaries


def parse_overall_design(xml_text: str, gse_code: str) -> OverallDesignDto:
    try:
        data = xmltodict.parse(xml_text)
        overall_design = data.get("MINiML", {}).get("Series", {}).get("Overall-Design", "")
    except Exception as e:
        logger.warning(f"XML Parsing failed for {gse_code}: {e}")
        overall_design = None

    return OverallDesignDto(
        gse_code=gse_code,
        overall_design=overall_design,
    )
