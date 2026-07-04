import asyncio
import logging

from src.api_client.dtos import DatasetSummaryDto, MissingFetchResult
from src.api_client.parsers import parse_dataset_summaries, parse_pmids_to_dbidx
from src.exceptions.api_client_exceptions import GatewayException, MissingAPIKeyError

logger = logging.getLogger(__name__)


class AsyncEutilsGateway:
    _ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    _ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    _ESUMMARY_BATCH_SIZE = 2

    def __init__(self, connector, api_key: str | None = None):
        self._connector = connector
        self._api_key = api_key

    async def get_dataset_idxs(self, pmids: list[str]) -> MissingFetchResult:
        if not self._api_key:
            raise MissingAPIKeyError()
        params = [
            ("dbfrom", "pubmed"),
            ("db", "gds"),
            ("linkname", "pubmed_gds"),
            ("retmode", "json"),
            ("api_key", self._api_key),
        ]
        params += [("id", pmid) for pmid in pmids]

        try:
            result = await self._connector.get_json(self._ELINK_URL, params=params)
        except Exception:
            logger.warning(f"Failed to fetch from {self._ELINK_URL} for {pmids}")
            return MissingFetchResult(dataset_links=[], failed_pmids=pmids, no_data_pmids=[])

        links = parse_pmids_to_dbidx(result, pmids)
        if links is None:
            logger.warning(f"Failed to parse response for pmids: {pmids}")
            return MissingFetchResult(dataset_links=[], failed_pmids=pmids, no_data_pmids=[])

        dataset_links = [link for link in links if link.db_idx]
        no_data = [link.pmid for link in links if not link.db_idx]
        return MissingFetchResult(dataset_links=dataset_links, failed_pmids=[], no_data_pmids=no_data)

    async def get_dataset_summaries(self, db_ids: list[str]) -> list[DatasetSummaryDto]:
        if not db_ids:
            return []
        chunks = [db_ids[i : i + self._ESUMMARY_BATCH_SIZE] for i in range(0, len(db_ids), self._ESUMMARY_BATCH_SIZE)]
        chunk_results = await asyncio.gather(*(self._fetch_summary_chunk(chunk) for chunk in chunks))

        return [summary for chunk_result in chunk_results for summary in chunk_result]

    async def _fetch_summary_chunk(self, db_ids: list[str]) -> list[DatasetSummaryDto]:
        if not self._api_key:
            raise MissingAPIKeyError()
        params = [("db", "gds"), ("id", ",".join(db_ids)), ("retmode", "json"), ("api_key", self._api_key)]
        try:
            result = await self._connector.get_json(self._ESUMMARY_URL, params=params)
        except Exception as e:
            raise GatewayException(f"Failed to fetch dataset summaries for {len(db_ids)} ids") from e
        return parse_dataset_summaries(result, db_ids)
