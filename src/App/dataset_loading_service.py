import asyncio
import pandas as pd

from src.App.front_model_utils import validate_chosen_file
from src.Exceptions.front_model_exceptions import EmptyDataFrameException


class DatasetLoadingService:
    MIN_LEN_PMID_LIST = 10

    def __init__(self, apiclient, redis_client):
        self.apiclient = apiclient
        self.redis_client = redis_client

    def load_initial_dataset_from_redis(self, initial_pmids) -> pd.DataFrame:
        initial_raw_data = asyncio.run(self.redis_client.get_dataframe_from_redis(initial_pmids))
        return pd.DataFrame(initial_raw_data)

    def load_user_dataset(self, uploaded_file) -> pd.DataFrame:
        pmid_list_from_file = validate_chosen_file(uploaded_file, DatasetLoadingService.MIN_LEN_PMID_LIST)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            pmids_not_present_in_redis = loop.run_until_complete(
                self.apiclient.reduce_user_pmid_list_with_cached_data(pmid_list_from_file)
            )
            pmids_present_in_redis = list(set(pmid_list_from_file).difference(pmids_not_present_in_redis))

            dataframe_present_in_redis = self._analyse_dataframe_present_in_redis(pmids_present_in_redis, loop)
            dataframe_not_present_in_redis = self._analyse_dataframe_not_present_in_redis(pmids_not_present_in_redis, loop)
        finally:
            loop.close()

        if dataframe_present_in_redis.empty and dataframe_not_present_in_redis.empty:
            raise EmptyDataFrameException

        dataframes = [df for df in (dataframe_present_in_redis, dataframe_not_present_in_redis) if not df.empty]
        return pd.concat(dataframes, ignore_index=True) if dataframes else pd.DataFrame()

    def _analyse_dataframe_not_present_in_redis(self, pmid_list, loop) -> pd.DataFrame:
        if pmid_list:
            data = loop.run_until_complete(self.apiclient.main_async_call(pmid_list))
            return pd.DataFrame(data)
        return pd.DataFrame()

    def _analyse_dataframe_present_in_redis(self, pmid_list, loop) -> pd.DataFrame:
        if pmid_list:
            data = loop.run_until_complete(self.redis_client.get_dataframe_from_redis(pmid_list))
            return pd.DataFrame(data)
        return pd.DataFrame()
