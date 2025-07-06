import asyncio
import json
import os
from dataclasses import dataclass
from http.client import responses
from time import sleep

import asynciolimiter
import pandas as pd
import xmltodict
from dotenv import load_dotenv

import aiohttp

load_dotenv('.env')


class AsyncDataRetriever:
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
        Title: str
        Summary: str
        Organism: str
        Experiment_type: str
        GSE_code: str
        Overall_design: str = None

    def __init__(self):
        self.pmid_list = []
        self.chunked_list = []
        self.df = pd.DataFrame
        self._load_pmids_from_file()
        self.BASE_URL_DB_IDX = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi'
        self.BASE_URL_SUMMARY = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
        self.BASE_URL_OVERALL_DESIGN = 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi'
        self.results = []
        self.API_KEY = os.getenv('API_KEY')

    def divide_into_packages(self, package_size=10):
        for i in range(0, len(self.pmid_list), 10):
            self.chunked_list.append(self.pmid_list[i:i + package_size])
        return self.chunked_list

    def _load_pmids_from_file(self):
        """
        Loads a list of PMIDs from a file named 'PMIDs_list.txt'
        """
        with open('PMIDs_list.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line.isdigit() and int(line) not in self.pmid_list:
                    self.pmid_list.append(int(line))
        return self.pmid_list

    def prepare_tasks_for_db_idx(self, session, pmid_list):
        tasks = []
        limiter = asynciolimiter.Limiter(10 / 1)
        for pmid in pmid_list:
            params = {
                "dbfrom": "pubmed",
                "db": "gds",
                "linkname": "pubmed_gds",
                "id": pmid,
                "retmode": "json",
                "api_key": self.API_KEY
            }
            tasks.append(session.get(self.BASE_URL_DB_IDX.format(pmid), params=params, ssl=False))
        return tasks

    def prepare_tasks_for_summary_info(self, session, db_idx_list):

        tasks = []
        limiter = asynciolimiter.Limiter(10 / 1)
        for idx in db_idx_list:
            params = {
                "db": "gds",
                "id": idx,
                "retmode": "json",
                "api_key": self.API_KEY
            }
            tasks.append(session.get(self.BASE_URL_SUMMARY, params=params, ssl=False))
        return tasks

    async def main_async_call(self, chunks):
        async with aiohttp.ClientSession() as session:
            for chunk in chunks:

                single_chunk_responses = await asyncio.gather(*self.prepare_tasks_for_db_idx(session, chunk))

                db_idx = [await AsyncDataRetriever.base_url_db_idx_json_parser(response) for response in single_chunk_responses]
                print(db_idx)

                for idx in db_idx:
                    print(len(idx))
                    tasks_summary = self.prepare_tasks_for_summary_info(session, idx)

                    summaries_reposponses = await asyncio.gather(*tasks_summary)

                    res = [await AsyncDataRetriever.base_summary_url_json_parser(response, id) for response, id in
                           zip(summaries_reposponses, idx)]

                    # print(res)

                    await asyncio.sleep(1)

                await asyncio.sleep(1)

    @staticmethod
    async def base_summary_url_json_parser(response, idx):
        json_response = await response.json()
        print(json_response)
        return json_response['result'][f'{idx}']

    @staticmethod
    async def base_url_db_idx_json_parser(response):
        json_response = await response.json()
        print(json_response)
        # //todo handle 'error': 'API key status invalid'
        return json_response['linksets'][0]['linksetdbs'][0]['links']


if __name__ == "__main__":
    o = AsyncDataRetriever()
    o.divide_into_packages()
    asyncio.run(o.main_async_call(o.chunked_list))
    # print(o.results)


