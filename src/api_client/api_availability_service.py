import asyncio


class ApiAvailabilityService:
    _ELINK_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    _ESUMMARY_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    _GEO_URL = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi"

    def __init__(self, connector):
        self._connector = connector

    async def check(self) -> bool:
        results = await asyncio.gather(
            self._check_elink(),
            self._check_esummary(),
            self._check_geo(),
            return_exceptions=True,
        )
        errors = [result for result in results if isinstance(result, Exception)]
        return not errors

    async def _check_elink(self) -> None:
        return await self._connector.get_json(
            self._ELINK_URL,
            params={
                "dbfrom": "pubmed",
                "db": "gds",
                "linkname": "pubmed_gds",
                "id": 19211887,
                "retmode": "json",
            },
        )

    async def _check_esummary(self) -> None:
        return await self._connector.get_json(
            self._ESUMMARY_URL,
            params={"db": "gds", "id": 200157027, "retmode": "json"},
        )

    async def _check_geo(self) -> None:
        return await self._connector.get_text(
            self._GEO_URL,
            params={"acc": "GSE157027", "form": "xml"},
        )
