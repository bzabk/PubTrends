import asyncio
import json
import os
from asyncio import Semaphore
from apiclient_utils import *
from time import time
from typing import List, AnyStr, Any
from dotenv import load_dotenv
import aiohttp
import pandas as pd
from ApiClient.DbCache.RedisCaching import RedisCaching

class PubMedDataRetriever:
    load_dotenv('.env')

    RETRIEVAL_TIMES = 3
    SEMAPHORE_SIZE = 10

    BASE_URL_OVERALL_DESIGN = 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi'
    BASE_URL_DB_IDX = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi'
    BASE_URL_SUMMARY = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'

    def __init__(self):
        self.api_key = os.getenv('API_KEY')
        self.semaphore = Semaphore(PubMedDataRetriever.SEMAPHORE_SIZE)
        self.failed_pmid_list = []
        self.counter=0
        self.session=None
        self.redis_client = RedisCaching()

    async def main_async_call(self, pmidlist: list[int]) -> pd.DataFrame:
        async with aiohttp.ClientSession() as session:
            self.session = session
            tasks = [asyncio.create_task(self.async_call_for_single_pmid(pmid_idx)) for pmid_idx in pmidlist]
            partial_df_list = await asyncio.gather(*tasks)
            df = stack_data_frames(partial_df_list)
            return df

    async def async_call_for_single_pmid(self,pmid_idx: int) -> pd.DataFrame | None:
        try:
            db_idx_list = await self.pmid_to_db_idx_layer(pmid_idx)
    
            df1 = create_pmid_to_db_idx_df(pmid_idx,db_idx_list)
    
            tasks_layer2 = [asyncio.create_task(self.db_idx_to_info_layer(db_idx=db_idx)) for db_idx in db_idx_list]
            pmdata_list = await asyncio.gather(*tasks_layer2)
    
            df2 = create_db_idx_to_info_df(db_idx_list,pmdata_list)
    
    
            gse_list = df2['GSE_code'].unique()
            tasks_layer3 = [asyncio.create_task(self.gse_code_to_overall_design(gse_code=gse_code)) for gse_code in gse_list]

            overall_design = await asyncio.gather(*tasks_layer3)

    
            df3 = create_gse_to_overall_design_df(gse_list,overall_design)
            partial_df = combine_all_data_frames(df1,df2,df3)
            await self.save_to_redis_db(partial_df)
            return partial_df
        except Exception as e:
            self.failed_pmid_list.append(pmid_idx)
            return None


    async def save_single_data_point_to_redis(self, single_row):
        value = json.dumps({k: v for k, v in single_row[1].items() if k != "pmid_idx"})
        await self.redis_client.set_key(key=single_row[1]["pmid_idx"], value=value)

    async def save_to_redis_db(self,df: pd.DataFrame):
        save_to_redis_tasks = [asyncio.create_task(self.save_single_data_point_to_redis(row)) for row in df.iterrows()]
        await asyncio.gather(*save_to_redis_tasks)

    async def get_data_from_url(self,url ,params: dict[str:Any],parser,sentinel: PmData|None,**kwargs):
        for attempt in range(1, PubMedDataRetriever.RETRIEVAL_TIMES + 5):
            try:
                response = await self.session.get(url, params=params)
                return await parser(response,**kwargs)
            except Exception as e:
                await asyncio.sleep(1)
        return sentinel






    async def pmid_to_db_idx_layer(self,id: int) -> List[int] | None:
        params = {
            "dbfrom": "pubmed", "db": "gds", "linkname": "pubmed_gds",
            "id": id, "retmode": "json", "api_key": self.api_key
        }
        async with self.semaphore:
            self.counter += 1
            return await self.get_data_from_url(url=PubMedDataRetriever.BASE_URL_DB_IDX,params=params,
                                                parser=pmid_to_db_idx_parser,sentinel=None)

            # for attempt1 in range(1, PubMedDataRetriever.RETRIEVAL_TIMES+ 5):
            #     try:
            #         response = await self.session.get(
            #             PubMedDataRetriever.BASE_URL_DB_IDX, params=params)
            #         data = await pmid_to_db_idx_parser(response)
            #         return data
            #     except Exception as e:
            #         await asyncio.sleep(0.5 * (attempt1 ** 2))
            # if attempt1 == PubMedDataRetriever.RETRIEVAL_TIMES + 4:
            #     self.failed_pmid_list.append(id)

    async def db_idx_to_info_layer(self,db_idx: int) -> PmData:
        params = {
            "db": "gds", "id": db_idx,
            "retmode": "json", "api_key": self.api_key
        }
        empty_pmdata = PmData()
        async with self.semaphore:
            self.counter += 1
            return await self.get_data_from_url(url=PubMedDataRetriever.BASE_URL_SUMMARY,params=params,
                                                parser=info_from_db_idx_parser,idx=db_idx,sentinel=empty_pmdata)
            # for attempt2 in range(1, PubMedDataRetriever.RETRIEVAL_TIMES + 5):
            #     try:
            #         response = await self.session.get(PubMedDataRetriever.BASE_URL_SUMMARY, params=params)
            #         pm_data = await info_from_db_idx_parser(response, idx=db_idx)
            #         return pm_data
            #     except Exception as e:
            #         await asyncio.sleep(0.5 * (attempt2 ** 1.5))
            # if attempt2 == PubMedDataRetriever.RETRIEVAL_TIMES + 4:
            #     self.failed_pmid_list.append(attempt2)

    async def gse_code_to_overall_design(self,gse_code):
        params = {"acc": gse_code,"form": "xml","api_key": self.api_key}
        async with self.semaphore:
            self.counter += 1
            return await self.get_data_from_url(url=PubMedDataRetriever.BASE_URL_OVERALL_DESIGN,params=params,
                                                 parser=overall_design_parser,sentinel=None)
            # for attempt1 in range(1, PubMedDataRetriever.RETRIEVAL_TIMES + 1):
            #     try:
            #         response = await self.session.get(
            #                 PubMedDataRetriever.BASE_URL_OVERALL_DESIGN.format(gse_code),
            #                 params=params,ssl=False)
            #
            #         return await overall_design_parser(response)
            #     except Exception as e:
            #         await asyncio.sleep(1)
            # if attempt1 == PubMedDataRetriever.RETRIEVAL_TIMES + 4:
            #     self.failed_pmid_list.append(gse_code)

    

if __name__ == "__main__":
    pmid_list = load_pmids_from_file()
    o = PubMedDataRetriever()
    start = time()
    df = asyncio.run(o.main_async_call(pmid_list))
    end = time()
    print(df)
    print(end-start)
    print(o.failed_pmid_list)
    print(o.counter)