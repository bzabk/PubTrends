import asyncio
from dataclasses import dataclass

import pandas as pd
import xmltodict

from ApiClient.AbstractDfCreator.abstract_df_creator import AbstractApiDataFrameCreator

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

class DatabaseIndexDataFrameCreator(AbstractApiDataFrameCreator):

    def __init__(self,retrieval_times,base_url,api_key,semaphore,data_list):
        self.data_list = data_list
        self.retrieval_times = retrieval_times
        self.base_url = base_url
        self.api_key = api_key
        self.semaphore: asyncio.Semaphore = semaphore
        self.failed_pmid = []
        self.session = None


    def set_session(self,session):
        self.session = session

    async def create_data_frame(self):
        db_rows = []
        chunks = self.divide_into_packages(self.data_list)
        for chunk in chunks:
            tasks_db = [asyncio.create_task(self.send_request(pmid)) for pmid in chunk]
            responses_db = await asyncio.gather(*tasks_db)
            await asyncio.sleep(0.1)
            for pmid, response in zip(chunk, responses_db):
                for atomic_response in response:
                    db_rows.append({"Pmid": pmid, "db_id": atomic_response})

        df_db = pd.DataFrame(db_rows)
        return df_db

    async def send_request(self,pmid):
        params = {
            "dbfrom": "pubmed",
            "db": "gds",
            "linkname": "pubmed_gds",
            "id": pmid,
            "retmode": "json",
            "api_key": self.api_key
        }
        async with self.semaphore:
            if self.semaphore._value == 0:
                pass
            for attempt in range(1, self.retrieval_times + 5):
                try:
                    response = await self.session.get(self.base_url.format(pmid), params=params)
                    data = await self.response_parser(response)
                    return data
                except Exception as e:
                    await asyncio.sleep(0.5 * (attempt ** 2))

        self.failed_pmid.append(pmid)
        return None


    async def response_parser(self,response,idx=None):
        json_response = await response.json()
        return json_response['linksets'][0]['linksetdbs'][0]['links']


class SummaryDataFrameCreator(AbstractApiDataFrameCreator):


    def __init__(self,retrieval_times,base_url,api_key,semaphore):
        self.retrieval_times = retrieval_times
        self.base_url = base_url
        self.api_key = api_key
        self.semaphore: asyncio.Semaphore = semaphore
        self.failed_pmid = []
        self.data_list= None
        self.session = None

    def set_session(self,session):
        self.session = session

    def set_data_list(self,data_list):
        self.data_list = data_list

    async def create_data_frame(self):
        unique_db_idx_set = set()
        info_rows = []
        db_idx_chunks = self.divide_into_packages(self.data_list)
        for db_idx_chunk in db_idx_chunks:

            tasks_info = [asyncio.create_task(self.send_request(db_idx)) for db_idx in db_idx_chunk]
            responses_db_info = await asyncio.gather(*tasks_info)

            for response_db_info, db_idx in zip(responses_db_info, db_idx_chunk):
                if db_idx not in unique_db_idx_set:
                    info_rows.append({"db_id": db_idx,
                                      "Title": response_db_info.Title,
                                      "Summary": response_db_info.Summary,
                                      "Experiment_type": response_db_info.Experiment_type,
                                      "GSE_code": response_db_info.GSE_code,
                                      "Organism": response_db_info.Organism})
                    unique_db_idx_set.add(db_idx)

        df_info = pd.DataFrame(info_rows)
        return df_info

    async def send_request(self, idx):
        params = {
            "db": "gds",
            "id": idx,
            "retmode": "json",
            "api_key": self.api_key
        }

        async with self.semaphore:
            if self.semaphore._value == 0:
                pass
            for attempt in range(1, self.retrieval_times + 1):
                try:
                    try:
                        response = await self.session.get(self.base_url.format(idx), params=params)
                    except Exception as e:
                        print(e)

                    data = await self.response_parser(response, idx)

                    return data
                except Exception as e:
                    await asyncio.sleep(0.5 * (2 ** attempt))

            return None
    async def response_parser(self, response,idx=None):
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


class OverallDesignDataFrameCreator(AbstractApiDataFrameCreator):


    def __init__(self,retrieval_times,base_url,api_key,semaphore):
        self.retrieval_times = retrieval_times
        self.base_url = base_url
        self.api_key = api_key
        self.semaphore: asyncio.Semaphore = semaphore
        self.failed_pmid = []
        self.data_list = None
        self.session = None

    def set_session(self,session):
        self.session = session

    def set_data_list(self,data_list):
        self.data_list = data_list

    async def create_data_frame(self):
        overall_design_rows = []
        gse_tasks = [asyncio.create_task(self.send_request(gse_code)) for gse_code in self.data_list]
        gse_responses = await asyncio.gather(*gse_tasks)
        for gse_response, gse_code in zip(gse_responses, self.data_list):
            overall_design_rows.append({
                "GSE_code": gse_code,
                "Overall_design": gse_response
            })

        df_overall_design = pd.DataFrame(overall_design_rows)
        return df_overall_design

    async def response_parser(self, response,idx=None):
        response_text = await response.text()
        data = xmltodict.parse(response_text)
        return data["MINiML"]["Series"].get("Overall-Design")

    async def send_request(self, idx):
        params = {
            "acc": idx,
            "form": "xml",
            "api_key": self.api_key
        }
        async with self.semaphore:
            if self.semaphore._value == 0:
                pass
            for attempt in range(1, self.retrieval_times + 1):
                try:
                    response = await self.session.get(self.base_url.format(idx), params=params,
                                                 ssl=False)
                    response_data = await self.response_parser(response)
                    return response_data
                except Exception as e:
                    await asyncio.sleep(0.5 * (2 ** attempt))
            return None