import asyncio
from asyncio import Semaphore
from dataclasses import dataclass
from time import time
from typing import List

import aiohttp
import numpy as np
import pandas as pd
import xmltodict

@dataclass
class PmData:
    """
    Holds metadata for a specific dataset, identified by a GSE code.
    Includes:
    - Title
    - Summary
    - Organism
    - Experiment Type
    - GSE Code
    - Overall Design
    """
    Title: str = None
    Summary: str = None
    Organism: str = None
    Experiment_type: str = None
    GSE_code: str = None
    Overall_design: str = None

class PubMedDataRetriever:

    RETRIEVAL_TIMES = 3
    SEMAPHORE_SIZE = 10

    BASE_URL_OVERALL_DESIGN = 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi'
    BASE_URL_DB_IDX = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi'
    BASE_URL_SUMMARY = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
    def __init__(self):
        self.semaphore = Semaphore(PubMedDataRetriever.SEMAPHORE_SIZE)
        self.retrieval_times = PubMedDataRetriever.RETRIEVAL_TIMES
        self.failed_pmid = []
        self.counter=0
        self.session=None

    async def main_async_call(self, pmidlist):
        async with aiohttp.ClientSession() as session:
            self.session = session
            tasks = [asyncio.create_task(self.chain_layer(pmid_idx)) for pmid_idx in pmidlist]
            df_list = await asyncio.gather(*tasks)
            return df_list

    async def chain_layer(self,pmid_idx):

        db_idx_list = await self.pmid_to_db_idx_layer(pmid_idx)

        df1 = PubMedDataRetriever.create_df1(pmid_idx,db_idx_list)

        tasks_layer2 = [asyncio.create_task(self.db_idx_to_info_layer(db_idx=db_idx)) for db_idx in np.unique(db_idx_list)]
        pmdata_list = await asyncio.gather(*tasks_layer2)
        df2 = PubMedDataRetriever.create_df2(db_idx_list,pmdata_list)


        gse_list = df2['GSE_code'].unique()
        tasks_layer3 = [asyncio.create_task(self.gse_code_to_overall_design(gse_code=gse_code)) for gse_code in gse_list]
        overall_design = await asyncio.gather(*tasks_layer3)

        df3 = PubMedDataRetriever.create_df3(gse_list,overall_design)
        partial_df = self._combine_all_data_frames(df1,df2,df3)
        return partial_df




    async def pmid_to_db_idx_layer(self,id: int) -> List[int] | None:
        params = {
            "dbfrom": "pubmed", "db": "gds", "linkname": "pubmed_gds",
            "id": id, "retmode": "json", "api_key": self.api_key
        }
        async with self.semaphore:

            for attempt1 in range(1, self.retrieval_times + 5):
                try:
                    response = await self.session.get(
                        PubMedDataRetriever.BASE_URL_DB_IDX, params=params)
                    data = await self.pmid_to_db_idx_parser(response)
                    return data
                except Exception as e:
                    await asyncio.sleep(0.5 * (attempt1 ** 2))
            if attempt1 == self.retrieval_times + 4:
                self.failed_pmid.append(id)

    async def db_idx_to_info_layer(self,db_idx: int) -> PmData:
        params = {
            "db": "gds", "id": db_idx,
            "retmode": "json", "api_key": self.api_key
        }
        async with self.semaphore:

            self.counter += 1
            for attempt2 in range(1, self.retrieval_times + 5):
                try:
                    response = await self.session.get(PubMedDataRetriever.BASE_URL_SUMMARY, params=params)
                    pm_data = await self.info_from_db_idx_parser(response, db_idx)
                    return pm_data
                except Exception as e:
                    await asyncio.sleep(0.5 * (attempt2 ** 1.5))
            if attempt2 == self.retrieval_times + 4:
                self.failed_pmid.append(attempt2)

    async def gse_code_to_overall_design(self,gse_code):
        params = {"acc": gse_code,"form": "xml","api_key": self.api_key}
        async with self.semaphore:

            self.counter += 1
            for attempt1 in range(1, self.retrieval_times + 1):
                try:
                    response = await self.session.get(
                            PubMedDataRetriever.BASE_URL_OVERALL_DESIGN.format(gse_code),
                            params=params,ssl=False)
                    response_data = await self.overall_design_parser(response)

                    return response_data
                except Exception as e:
                    await asyncio.sleep(1)
            if attempt1 == self.retrieval_times + 4:
                self.failed_pmid.append(gse_code)

    @staticmethod
    async def overall_design_parser(response):
        response_text = await response.text()
        data = xmltodict.parse(response_text)
        return data["MINiML"]["Series"].get("Overall-Design")

    @staticmethod
    async def pmid_to_db_idx_parser(response):
        json_response = await response.json()
        return json_response['linksets'][0]['linksetdbs'][0]['links']

    @staticmethod
    async def info_from_db_idx_parser(response, idx):
        json_response = await response.json()
        data_response = json_response['result'][f'{idx}']
        pmid_data = PmData(
            Title=data_response['title'],
            Summary=data_response['summary'],
            Organism=data_response['taxon'],
            Experiment_type=data_response['gdstype'],
            GSE_code=data_response['accession']
        )
        return pmid_data

    @staticmethod
    def _load_pmids_from_file():
        pmid_list = set()
        with open('PMIDs_list.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line.isdigit() and int(line) not in pmid_list:
                    pmid_list.add(int(line))
        return list(pmid_list)

    @staticmethod
    def _combine_all_data_frames(df_db, df_info, df_overall_design):
        combined_1 = df_db.merge(df_info, on='db_idx', how='left')
        combined_2 = combined_1.merge(df_overall_design, on='GSE_code', how='left')
        return combined_2

    @staticmethod
    def create_df1(pmid_idx: int, db_idx_list: List[int]) -> pd.DataFrame:
        df = pd.DataFrame({"pmid_idx": [pmid_idx] * len(db_idx_list), "db_idx": db_idx_list})
        return df.explode("db_idx").reset_index(drop=True)

    @staticmethod
    def create_df2(db_idx_list: List[int], pmdata_list: List[PmData]) -> pd.DataFrame:
        return pd.DataFrame({"db_idx": db_idx_list,
                             "Title": [pmdata.Title for pmdata in pmdata_list],
                             "Summary": [pmdata.Summary for pmdata in pmdata_list],
                             "Organism": [pmdata.Organism for pmdata in pmdata_list],
                             "Experiment_type": [pmdata.Experiment_type for pmdata in pmdata_list],
                             "GSE_code": [pmdata.GSE_code for pmdata in pmdata_list]})

    @staticmethod
    def create_df3(gse_list, overall_design_list):
        return pd.DataFrame({"GSE_code": [gse for gse in gse_list],
                             "overall_design": [overall_design for overall_design in overall_design_list]})

    @staticmethod
    def _stack_data_frames():
        pass

if __name__ == "__main__":
    pmid_list = PubMedDataRetriever._load_pmids_from_file()
    o = PubMedDataRetriever()
    start = time()
    df = asyncio.run(o.main_async_call(pmid_list))
    end = time()
    print(end-start)
    print(o.failed_pmid)
    print(o.counter)