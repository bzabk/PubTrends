import asyncio

import streamlit as st

from src.api_client.apiclient import ApiClient
from src.api_client.db_cache.redis_dataset_cache_repository import RedisCaching
from src.app.dataset_loading_service import DatasetLoadingService
from src.app.front_model_utils import (
    read_initial_pmids_from_the_file,
)
from src.app.message_service import MessageService
from src.app.preprocessing_service import PreprocessingService
from src.app.statemanager import SessionStateManager
from src.app.ui_service import UIService
from src.exceptions.api_client_exceptions import ResponseStatusException
from src.exceptions.front_model_exceptions import NotEnoughPmidsInTxtFileException


class MainApp:
    def __init__(self):
        self.progress_bar_placeholder = None
        self.error_placeholder = None
        self.message_service: None | MessageService = None
        self.session_manager = SessionStateManager(st.session_state)
        self.redis_client = RedisCaching()

        self.apiclient = ApiClient(
            redis_client=self.redis_client, api_key=self.session_manager.get("api_key")
        )

        self.dataset_loading_service = DatasetLoadingService(
            apiclient=self.apiclient, redis_client=self.redis_client
        )
        self.preprocessing_service = PreprocessingService(
            session_manager=self.session_manager
        )
        self.ui_service = UIService()

    # ----------------------------------- Layout app -----------------------------------
    def run(self):
        self.prepare_main_window()
        self.prepare_side_bar()
        self.prepare_tabs()

    def prepare_main_window(self) -> None:
        self.error_placeholder, self.progress_bar_placeholder = (
            self.ui_service.render_main_window()
        )
        self.message_service = MessageService(
            error_placeholder=self.error_placeholder,
            progress_bar_placeholder=self.progress_bar_placeholder,
        )

    def prepare_side_bar(self) -> None:

        sidebar_state = self.ui_service.render_sidebar(
            self.session_manager.get("api_key")
        )

        self.session_manager.set("uploaded_file", sidebar_state["uploaded_file"])
        self.session_manager.set("max_features", sidebar_state["max_features"])
        self.session_manager.set("num_clusters", sidebar_state["num_clusters"])

        if sidebar_state["save_api_key_clicked"]:
            try:
                self.session_manager.set("api_key", sidebar_state["api_key"])
                self.apiclient.api_key = sidebar_state["api_key"]
                asyncio.run(self.apiclient.check_api_availability(with_api_key=True))
                self.message_service.success(
                    message="API key is valid and saved successfully"
                )
            except ResponseStatusException as e:
                self.message_service.error(e.message)

        if sidebar_state["load_pmids_clicked"]:
            try:
                self.handle_user_dataset()
            except NotEnoughPmidsInTxtFileException as e:
                self.message_service.error(e.message)

        if sidebar_state["load_toy_clicked"]:
            self.load_data_from_redis()

    def prepare_tabs(self) -> None:
        self.ui_service.render_tabs(session_manager=self.session_manager)

    def load_data_from_redis(self) -> None:
        """
        Handles the loading and preprocessing of a dataset.

        """
        initial_pmids = read_initial_pmids_from_the_file()
        self.session_manager.set(
            "pmid_df",
            self.dataset_loading_service.load_initial_dataset_from_redis(initial_pmids),
        )
        self.preprocessing_service.process_loaded_toy_dataset()

    # ----------------------------------- User data handling -----------------------------------
    def handle_user_dataset(self) -> None:
        self.session_manager.set(
            "pmid_df",
            self.dataset_loading_service.load_user_dataset(
                uploaded_file=self.session_manager.get("uploaded_file")
            ),
        )
        self.preprocessing_service.process_loaded_user_dataset()
