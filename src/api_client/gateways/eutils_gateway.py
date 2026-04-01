from src.api_client.dtos import DatasetSummaryDto, DatasetLinkDto
from src.api_client.parsers import parse_dataset_summary, parse_pmid_to_dbidx


class AsyncEutilsGateway:
    _ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    _ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def __init__(self, connector, api_key: str | None = None):
        self._connector = connector
        self._api_key = api_key

    async def get_dataset_idx(self, pmid: int) -> DatasetLinkDto:
        result = await self._connector.get_json(
            self._ELINK_URL,
            params={
                "dbfrom": "pubmed",
                "db": "gds",
                "linkname": "pubmed_gds",
                "id": pmid,
                "retmode": "json",
                "api_key": self._api_key,
            },
        )
        return parse_pmid_to_dbidx(result, pmid=pmid)

    async def get_dataset_summary(self, db_idx: int) -> DatasetSummaryDto:
        result = await self._connector.get_json(
            self._ESUMMARY_URL,
            params={
                "db": "gds",
                "id": db_idx,
                "retmode": "json",
                "api_key": self._api_key,
            },
        )
        return parse_dataset_summary(result, db_idx=db_idx)
