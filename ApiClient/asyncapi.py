import asyncio
import os
from time import time
import aiohttp
from dotenv import load_dotenv

from ApiClient.DfCreatorImplementations.df_creator_implementations import SummaryDataFrameCreator, \
    OverallDesignDataFrameCreator
from DfCreatorImplementations.df_creator_implementations import DatabaseIndexDataFrameCreator


class AsyncDataRetriever:

    RETRIVAL_TIMES = 3
    SEMAPHORE_SIZE = 10

    def __init__(self):
        #load_dotenv('./ApiClient/.env')
        load_dotenv(".env")
        self.pmid_list = AsyncDataRetriever._load_pmids_from_file()
        self.BASE_URL_DB_IDX = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/elink.fcgi'
        self.BASE_URL_SUMMARY = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi'
        self.BASE_URL_OVERALL_DESIGN = 'https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi'

        self.API_KEY = os.getenv('API_KEY')
        self.sem = asyncio.Semaphore(AsyncDataRetriever.SEMAPHORE_SIZE)

        self.db_idx_df = DatabaseIndexDataFrameCreator(retrieval_times=AsyncDataRetriever.RETRIVAL_TIMES,
                                                  base_url=self.BASE_URL_DB_IDX,
                                                  api_key=self.API_KEY, semaphore=self.sem, data_list=self.pmid_list)

        self.summary_df = SummaryDataFrameCreator(retrieval_times=AsyncDataRetriever.RETRIVAL_TIMES,
                                             base_url=self.BASE_URL_SUMMARY,
                                             api_key=self.API_KEY, semaphore=self.sem)

        self.overall_design = OverallDesignDataFrameCreator(retrieval_times=AsyncDataRetriever.RETRIVAL_TIMES,
                                                       base_url=self.BASE_URL_OVERALL_DESIGN,
                                                       api_key=self.API_KEY, semaphore=self.sem)

    async def main_async_call(self):

        async with aiohttp.ClientSession() as session:

            self.db_idx_df.set_session(session)
            df_db = await self.db_idx_df.create_data_frame()
            await asyncio.sleep(1)

            self.summary_df.set_session(session)
            self.summary_df.set_data_list(df_db['db_id'].unique().tolist())
            su_df = await self.summary_df.create_data_frame()
            await asyncio.sleep(1)


            self.overall_design.set_session(session)
            self.overall_design.set_data_list(set(su_df['GSE_code'].tolist()))
            overall_design_df  =await self.overall_design.create_data_frame()


            final_df = self._combined_all_df(df_db, su_df, overall_design_df)


        print(final_df)
        final_df.to_csv("save.csv",index=False)
        return final_df

    @staticmethod
    def _combined_all_df(df_db, df_info, df_overall_design):
        combined_1 = df_db.merge(df_info, on='db_id', how='left')
        combined_2 = combined_1.merge(df_overall_design, on='GSE_code', how='left')
        return combined_2

    @staticmethod
    def _load_pmids_from_file():
        pmid_list = set()
        with open('PMIDs_list.txt', 'r') as f:
            for line in f:
                line = line.strip()
                if line.isdigit() and int(line) not in pmid_list:
                    pmid_list.add(int(line))
        return list(pmid_list)

if __name__ == "__main__":
    o = AsyncDataRetriever()
    start = time()
    asyncio.run(o.main_async_call())
    print(time()-start)