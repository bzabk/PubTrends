import asyncio
import os
from dataclasses import dataclass
from time import time
import aiohttp
import pandas as pd
from dotenv import load_dotenv

class AsyncDataRetriever:

    RETRIVAL_TIMES = 5
    SEMAPHORE_SIZE = 10


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

    def __init__(self):
        load_dotenv('.env')
        self.pmid_list = []
        self._load_pmids_from_file()
        self.BASE_URL_DB_IDX = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi'
        self.BASE_URL_SUMMARY = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
        self.BASE_URL_OVERALL_DESIGN = 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi'


        self.API_KEY = os.getenv('API_KEY')
        self.sem = asyncio.Semaphore(AsyncDataRetriever.SEMAPHORE_SIZE)

        self.failed_pmid = []
        self.failed_db_idx = []

    def _load_pmids_from_file(self):
        """
        Loads a list of PMIDs from a file named 'PMIDs_list.txt'
        """
        with open('PMIDs_list.txt', 'r') as f:
            for line in f:
                line = line.strip()
                #if line.isdigit() and int(line) not in self.pmid_list:
                self.pmid_list.append(int(line))
        return self.pmid_list

    async def _send_request_db_id(self,session,pmid):
        params = {
            "dbfrom": "pubmed",
            "db": "gds",
            "linkname": "pubmed_gds",
            "id": pmid,
            "retmode": "json",
            "api_key": self.API_KEY
        }
        async with self.sem:
            if self.sem._value==0:
                pass
            for attempt in range(1,AsyncDataRetriever.RETRIVAL_TIMES+1):
                try:
                    response = await session.get(self.BASE_URL_DB_IDX.format(pmid), params=params)
                    data = await AsyncDataRetriever.db_idx_json_parser(response)
                    return data
                except Exception as e:
                    await asyncio.sleep(0.5*(attempt**2))

        self.failed_pmid.append(pmid)
        return []


    async def _send_request_info(self,session,id):
        params = {
            "db": "gds",
            "id": id,
            "retmode": "json",
            "api_key": self.API_KEY
        }

        async with self.sem:
            if self.sem._value==0:
                pass
            for attempt in range(1,AsyncDataRetriever.RETRIVAL_TIMES+1):
                try:
                    response = await session.get(self.BASE_URL_SUMMARY.format(id),params=params)
                    data = await AsyncDataRetriever.summary_json_parser(response,id)
                    return data
                except Exception as e:
                    await asyncio.sleep(0.5*(2**attempt))
            self.failed_db_idx.append(id)
            return None


    async def _send_request_overall_design(self,session,gse_code):
        params = {
            "acc": gse_code,
            "form": "xml",
            "api_key":self.API_KEY
        }
        async with self.sem:
            if self.sem._value==0:
                pass
            for _ in range(AsyncDataRetriever.RETRIVAL_TIMES):
                try:
                    response = await session.get(self.BASE_URL_OVERALL_DESIGN.format(gse_code),params=params,ssl=False)
                    response_data = AsyncDataRetriever.overall_design_xml_parser(response)
                    return response_data
                except Exception:
                    await asyncio.sleep(1)
            return None


    async def _create_df_from_db_idx_api(self,session,pmid_list):
        db_rows = []
        chunks = AsyncDataRetriever.divide_into_packages(pmid_list)
        for chunk in chunks:
            tasks_db = [asyncio.create_task(self._send_request_db_id(session, pmid)) for pmid in chunk]
            responses_db = await asyncio.gather(*tasks_db)
            await asyncio.sleep(0.1)
            for pmid, response in zip(pmid_list, responses_db):
                for atomic_response in response:
                    db_rows.append({"pmid": pmid, "db_id": atomic_response})

        df_db = pd.DataFrame(db_rows)
        return df_db

    async def _create_df_from_info_api(self,session,db_list):
        unique_db_idx_set = set()
        info_rows = []
        db_idx_chunks = AsyncDataRetriever.divide_into_packages(db_list)
        for db_idx_chunk in db_idx_chunks:

            tasks_info = [asyncio.create_task(self._send_request_info(session, db_idx)) for db_idx in db_idx_chunk]
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

    async def _create_df_from_overall_design_api(self,session,gse_set):
        overall_design_rows = []
        gse_tasks = [asyncio.create_task(self._send_request_overall_design(session, gse_code)) for gse_code in gse_set]
        gse_responses = await asyncio.gather(*gse_tasks)

        for gse_response, gse_code in zip(gse_responses, gse_set):
            overall_design_rows.append({
                "GSE_code": gse_code,
                "Overall_design": gse_response
            })

        df_overall_design = pd.DataFrame(overall_design_rows)
        return df_overall_design


    async def main_async_call(self, pmid_list):


        start = time()
        async with aiohttp.ClientSession() as session:

            df_db = await self._create_df_from_db_idx_api(session,pmid_list)

            db_list = df_db['db_id'].unique().tolist()

            df_info = await self._create_df_from_info_api(session,db_list)

            gse_set = df_info['GSE_code']

            df_overall_design = await self._create_df_from_overall_design_api(session,gse_set)

            final_df = self._combined_all_df(df_db,df_info,df_overall_design)


            print(len(self.failed_pmid))
            print(len(self.failed_db_idx))
        end=time()
        print(end-start)

    @staticmethod
    def _combined_all_df(df_db, df_info, df_overall_design):

        combined_1 = df_db.merge(df_info, on='db_id', how='left')
        combined_2 = combined_1.merge(df_overall_design, on='GSE_code', how='left')
        return combined_2

    @staticmethod
    async def overall_design_xml_parser(response):
        response_text = await response.text()
        return response_text["MINiML"]["Series"].get("Overall-Design")

    @staticmethod
    async def summary_json_parser(response, idx):
        json_response = await response.json()
        data_response = json_response['result'][f'{idx}']
        pmid_data = AsyncDataRetriever.PmData(
            Title=data_response['title'],
            Summary=data_response['summary'],
            Organism=data_response['taxon'],
            Experiment_type=data_response['gdstype'],
            GSE_code=data_response['accession']
        )
        return pmid_data

    @staticmethod
    async def db_idx_json_parser(response):
        json_response = await response.json()
        return json_response['linksets'][0]['linksetdbs'][0]['links']

    @staticmethod
    def divide_into_packages(list_to_chunks, package_size=10):
        chunks = []
        for i in range(0, len(list_to_chunks), 10):
            chunks.append(list_to_chunks[i:i + package_size])
        return chunks


if __name__ == "__main__":
    o = AsyncDataRetriever()
    start = time()
    asyncio.run(o.main_async_call(o.pmid_list))
    end = time()
    print(end-start)


