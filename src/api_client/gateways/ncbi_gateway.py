from src.api_client.dtos import OverallDesignDto
from src.api_client.parsers import parse_overall_design


class AsyncNcbiGateway:
    _NCBI_URL = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi"

    def __init__(self, connector, api_key: str | None = None):
        self._connector = connector
        self._api_key = api_key

    async def get_overall_design(self, gse_code: str) -> OverallDesignDto:
        result = await self._connector.get_text(
            self._NCBI_URL,
            params={
                "acc": gse_code,
                "form": "xml",
                "api_key": self._api_key,
            },
        )
        return parse_overall_design(result, gse_code=gse_code)