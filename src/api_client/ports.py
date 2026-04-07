from typing import Protocol, Any


class DatasetCacheRepository(Protocol):

    async def exists(self,pmid: int) ->bool:
        ...

    async def add(self, pmid_data: dict[str, Any]) -> int:
        ...

    async def get(self,pmid: list[int]) -> list[dict[str, Any]]:
        ...
