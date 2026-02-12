import asyncio
import json
from asyncio import Semaphore
import numpy as np
from src.ApiClient.DbCache.RedisCaching import RedisCaching
from src.Exceptions.api_client_exceptions import (
    InfoSummaryException,
    OverallDesignException,
    PmidException,
    ResponseStatusException,
    SingleAsyncCallException,
)
from src.ApiClient.apiclient_utils import *
from time import time
from typing import List, Any, Callable
import aiohttp
import pandas as pd


class ApiClient:

    _RETRIEVAL_TIMES = 3
    _SEMAPHORE_SIZE = 10

    _BASE_URL_OVERALL_DESIGN = "https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi"
    _BASE_URL_DB_IDX = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi"
    _BASE_URL_SUMMARY = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"

    def __init__(self, redis_client: RedisCaching, api_key: str | None = None):
        self.session = None
        self.api_key = api_key
        self.semaphore = Semaphore(ApiClient._SEMAPHORE_SIZE)
        self.failed_pmid_list = []
        self.redis_client = redis_client

    async def check_api_availability(self, with_api_key=False) -> None:

        async with aiohttp.ClientSession() as session:
            urls = [
                'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi?dbfrom=pubmed&db=gds&linkname=pubmed_gds&id=19211887&retmode=json',
                'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=gds&id=200157027&retmode=json',
                'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE157027&form=xml'
            ]
            if with_api_key:
                urls = [f"{url}&api_key={self.api_key}" for url in urls]
            try:
                responses = await asyncio.gather(*(session.get(url) for url in urls))
                if any(resp.status != 200 for resp in responses):
                    raise ResponseStatusException(
                        "One or more API endpoints returned non-200 status codes, "
                        "check your internet connection and your API key"
                    )
            except aiohttp.ClientError as e:
                raise ResponseStatusException(f"API connection error: {str(e)}") from e

    async def main_async_call(self, pmidlist: list[int]) -> pd.DataFrame:
        async with aiohttp.ClientSession() as session:
            self.session = session
            try:
                await self.check_api_availability()
                tasks = [asyncio.create_task(self.async_call_for_single_pmid(pmid_idx)) for pmid_idx in pmidlist]
                partial_df_list = await asyncio.gather(*tasks)
                df = stack_data_frames(partial_df_list)
                return df
            except ResponseStatusException:
                pass

    async def async_call_for_single_pmid(self, pmid_idx: int) -> pd.DataFrame | None:
        try:
            db_idx_list = await self.pmid_to_db_idx_layer(pmid_idx)
            df1 = create_pmid_to_db_idx_df(pmid_idx, db_idx_list)
            tasks_layer2 = [asyncio.create_task(self.db_idx_to_info_layer(db_idx=db_idx)) for db_idx in db_idx_list]
            pmdata_list = await asyncio.gather(*tasks_layer2)

            df2 = create_db_idx_to_info_df(db_idx_list, pmdata_list)
            gse_list = df2["GSE_code"].unique()
            tasks_layer3 = [asyncio.create_task(self.gse_code_to_overall_design(gse_code=gse_code)) for gse_code in gse_list]

            overall_design = await asyncio.gather(*tasks_layer3)
            df3 = create_gse_to_overall_design_df(gse_list, overall_design)
            partial_df = combine_all_data_frames(df1, df2, df3)

            await self.sadd_for_pmid(partial_df)

            return partial_df
        except SingleAsyncCallException:
            return 12

    async def is_data_in_cache(self, pmid: int) -> int | None:
        if await self.redis_client.check_if_exists(pmid):
            return None
        return pmid

    async def reduce_user_pmid_list_with_cached_data(self, pmid_list: List[int]):

        tasks = [asyncio.create_task(self.is_data_in_cache(pmid)) for pmid in pmid_list]
        results = await asyncio.gather(*tasks)

        results = [result for result in results if result is not None]
        return results

    async def sadd_for_pmid(self, df: pd.DataFrame):
        pmid = str(df["Pmid"].iloc[0])
        tasks = [
            asyncio.create_task(
                self.redis_client.sadd(
                    pmid,
                    json.dumps(
                        {k: int(v) if isinstance(v, np.integer) else v for k, v in row._asdict().items() if k != "Pmid"}
                    ),
                )
            )
            for row in df.itertuples(index=False, name="SingleRow")
        ]
        await asyncio.gather(*tasks)

    async def get_data_from_url(
        self,
        url,
        params: dict[str:Any],
        parser: Callable[[aiohttp.ClientSession], Any],
        expection_to_raise,
        **kwargs,
    ):

        for attempt in range(1, ApiClient._RETRIEVAL_TIMES + 5):
            try:
                response = await self.session.get(url, params=params)
                x = await parser(response, **kwargs)
                return x
            except Exception:
                await asyncio.sleep(1)
        raise expection_to_raise

    async def pmid_to_db_idx_layer(self, id: int) -> List[int] | None:
        params = {
            "dbfrom": "pubmed",
            "db": "gds",
            "linkname": "pubmed_gds",
            "id": id,
            "retmode": "json",
            "api_key": self.api_key,
        }
        async with self.semaphore:
            return await self.get_data_from_url(
                url=ApiClient._BASE_URL_DB_IDX,
                params=params,
                parser=pmid_to_db_idx_parser,
                expection_to_raise=PmidException,
            )

    async def db_idx_to_info_layer(self, db_idx: int) -> PmData:
        params = {"db": "gds", "id": db_idx, "retmode": "json", "api_key": self.api_key}
        async with self.semaphore:
            return await self.get_data_from_url(
                url=ApiClient._BASE_URL_SUMMARY,
                params=params,
                parser=info_from_db_idx_parser,
                idx=db_idx,
                expection_to_raise=InfoSummaryException,
            )

    async def gse_code_to_overall_design(self, gse_code: str):
        params = {"acc": gse_code, "form": "xml", "api_key": self.api_key}
        async with self.semaphore:
            return await self.get_data_from_url(
                url=ApiClient._BASE_URL_OVERALL_DESIGN,
                params=params,
                parser=overall_design_parser,
                expection_to_raise=OverallDesignException,
            )


