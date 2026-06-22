import os

import pandas as pd
import streamlit as st

from src.api_client.api_client_facade import ApiClientFacade
from src.app.message_service import MessageService
from src.app.preprocessing_service import PreprocessingService
from src.app.ui_service import UIService
from src.exceptions.api_client_exceptions import (
    ApiUnavailableException,
    InvalidApiKeyException,
    MissingAPIKeyError,
)
from src.exceptions.front_model_exceptions import (
    EmptyDataFrameException,
    NotEnoughPmidsInTxtFileException,
    PmidTxtFileIsNoneException,
)


class MainApp:
    SESSION_DEFAULTS = {
        "pmid_df": None,
        "success_flag": False,
        "uploaded_file": None,
        "current_labels": None,
        "current_X": None,
        "kmeans_processor": None,
        "tfidf_processor": None,
        "tsne_processor": None,
        "api_key": None,
        "max_features": 12,
        "num_clusters": 8,
        "current_num_clusters": None,
        "remove_punctuation": None,
        "pmid_list": None,
    }
    REDIS_URL_TEMPLATE = "redis://{host}:{port}"

    def __init__(self):
        self._initialize_session_state()
        self.apiclient = ApiClientFacade(redis_url=self._build_redis_url())
        self._restore_api_client_state()

        self.preprocessing_service = PreprocessingService()
        self.ui_service = UIService()
        self.message_service = None

    def _initialize_session_state(self) -> None:
        for key, value in self.SESSION_DEFAULTS.items():
            st.session_state.setdefault(key, value)

    def _restore_api_client_state(self) -> None:
        api_key = st.session_state.get("api_key")
        if api_key:
            self.apiclient.set_api_key(api_key)

    def _build_redis_url(self) -> str:
        redis_host = os.getenv("REDIS_HOST", "localhost")
        redis_port = os.getenv("REDIS_PORT", "6379")
        return self.REDIS_URL_TEMPLATE.format(host=redis_host, port=redis_port)

    def run(self):
        error_placeholder, progress_bar_placeholder = self.ui_service.render_main_window()
        self.message_service = MessageService(error_placeholder, progress_bar_placeholder)

        sidebar_state = self.ui_service.render_sidebar()
        self._sync_sidebar_state(sidebar_state)
        self._handle_sidebar_actions(sidebar_state)
        self.ui_service.render_tabs()

    def _sync_sidebar_state(self, sidebar_state) -> None:
        st.session_state["max_features"] = sidebar_state.max_features
        st.session_state["num_clusters"] = sidebar_state.num_clusters

    def _handle_sidebar_actions(self, sidebar_state) -> None:
        try:
            if sidebar_state.save_api_key_clicked:
                self._save_api_key(sidebar_state.api_key)
            if sidebar_state.load_pmids_clicked:
                self.preprocessing_service.validate_chosen_file(sidebar_state.uploaded_file)
                self._load_dataset(load_default_dataset=False)
            if sidebar_state.load_toy_clicked:
                self._load_dataset(load_default_dataset=True)
        except (PmidTxtFileIsNoneException, NotEnoughPmidsInTxtFileException) as exc:
            self.message_service.error(str(exc))
        except (MissingAPIKeyError, EmptyDataFrameException) as exc:
            self.message_service.error(str(exc))
        except Exception as exc:
            self.message_service.error(f"Unexpected error: {exc}")

    def _save_api_key(self, api_key: str) -> None:
        errors = self.apiclient.check_api_availability(api_key)
        if any(isinstance(error, InvalidApiKeyException) for error in errors):
            self.message_service.error("Invalid API key")
            return
        if any(isinstance(error, ApiUnavailableException) for error in errors):
            self.message_service.error("API is unavailable")
            return
        if errors:
            self.message_service.error(f"Unexpected error: {errors}")
            return
        self.apiclient.set_api_key(api_key)
        st.session_state["api_key"] = api_key
        self.message_service.success("API key saved.")

    def _load_dataset(self, load_default_dataset: bool) -> None:
        if load_default_dataset:
            st.session_state["pmid_df"] = pd.read_csv("src/api_client/redis_data/toy_dataset.csv")
            self.preprocessing_service.process_dataframe_from_session_cache()
        else:
            result = self.apiclient.fetch_dataframe(st.session_state["pmid_list"])
            if result.dataframe is None or result.dataframe.empty:
                raise EmptyDataFrameException(
                    "No GEO datasets found for the provided PMIDs. "
                    f"Failed: {len(result.failed_pmids)}, no data: {len(result.no_data_pmids)}."
                )
            st.session_state["pmid_df"] = result.dataframe
            self.preprocessing_service.process_dataframe_from_session_cache()
