import asyncio


class ApiAvailabilityService:
    _ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?"
    _ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    _GEO_URL = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi"

    def __init__(self, connector):
        self._connector = connector

    async def check(self, key: str) -> list[Exception]:
        results = await asyncio.gather(
            self._check_elink(key),
            self._check_esummary(key),
            self._check_geo(),
            return_exceptions=True,
        )
        errors = [result for result in results if isinstance(result, Exception)]
        return errors

    async def _check_elink(self, api_key: str) -> None:
        return await self._connector.get_json(
            self._ELINK_URL,
            params={
                "dbfrom": "pubmed",
                "db": "gds",
                "linkname": "pubmed_gds",
                "id": 19211887,
                "retmode": "json",
                "api_key": api_key,
            },
        )

    async def _check_esummary(self, api_key: str) -> None:
        return await self._connector.get_json(
            self._ESUMMARY_URL,
            params={"db": "gds", "id": 200157027, "retmode": "json", "api_key": api_key},
        )

    async def _check_geo(self) -> None:
        return await self._connector.get_text(
            self._GEO_URL,
            params={"acc": "GSE157027", "form": "xml"},
        )
