from src.api_client.dtos import DatasetSummaryDto, DatasetLinkDto
from src.api_client.parsers import parse_dataset_summary, parse_pmid_to_dbidx
from src.exceptions.api_client_exceptions import GatewayException


class AsyncEutilsGateway:
    _ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    _ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def __init__(self, connector, api_key: str | None = None):
        self._connector = connector
        self._api_key = api_key

    async def get_dataset_idx(self, pmid: str) -> DatasetLinkDto:
        try:
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
        except Exception as e:
            raise GatewayException(f"Failed to fetch dataset idx for pmid {pmid}") from e
        return parse_pmid_to_dbidx(result, pmid)

    async def get_dataset_summary(self, db_idx: str) -> DatasetSummaryDto:
        try:
            result = await self._connector.get_json(
                self._ESUMMARY_URL,
                params={
                    "db": "gds",
                    "id": db_idx,
                    "retmode": "json",
                    "api_key": self._api_key,
                },
            )
        except Exception as e:
            raise GatewayException(f"Failed to fetch dataset summary for db_idx {db_idx}") from e
        return parse_dataset_summary(result, db_idx)

