import asyncio

from src.App.dataset_loading_service import DatasetLoadingService
from src.App.preprocessing_service import PreprocessingService
from src.App.ui_service import UIService
from src.App.front_model_utils import (
    read_initial_pmids_from_the_file,
    load_css_styles,
)
import streamlit as st
from src.ApiClient.DbCache.RedisCaching import RedisCaching
from src.ApiClient.apiclient import ApiClient
from src.App.statemanager import SessionStateManager
from src.Exceptions.api_client_exceptions import ResponseStatusException
from src.Exceptions.front_model_exceptions import NotEnoughPmidsInTxtFileException
from src.Preprocessing.text_preprocessing import *


class MainApp:
    """
    Main application class for the PubTrends app.
    This class handles the initialization of the App session state,
    layout preparation, data loading, preprocessing, and visualization.

    Attributes:
    error_placeholder (st.empty): Placeholder for displaying error messages.
    progress_bar_placeholder (st.empty): Placeholder for displaying the progress bar.
    pubmed_api (ApiClient): Instance of the ApiClient class for fetching data from PubMed.
    """

    PERPLEXITY_MIN = 30
    PLOT_WIDTH = 900
    PLOT_HEIGHT = 600
    MIN_LEN_PMID_LIST = 10

    def __init__(self):
        """
        Some of the variables we want to save between streamlit sessions
        """
        self.progress_bar_placeholder = None
        self.error_placeholder = None
        load_css_styles()
        self.session_manager = SessionStateManager(st.session_state)
        self.redis_client = RedisCaching()

        self.apiclient = ApiClient(redis_client=self.redis_client,
                                   api_key=self.session_manager.get("api_key"))

        self.dataset_loading_service = DatasetLoadingService(apiclient=self.apiclient,
                                                             redis_client=self.redis_client)
        self.preprocessing_service = PreprocessingService(
            session_manager=self.session_manager,
            perplexity_min=MainApp.PERPLEXITY_MIN,
        )
        self.ui_service = UIService()
        """
        Remove_Punctuation only provides text processing without any saving any parameters so it does not need
        to be remembered between streamlit sessions
        """
        self.session_manager.set("remove_punctuation", ProcessorFactory.get_processor("remove_punctuation"))

    # ----------------------------------- Layout App -----------------------------------
    def run(self):
        self.prepare_main_window()
        self.prepare_side_bar()
        self.prepare_tabs()

    def prepare_main_window(self) -> None:
        """
        Reserving space for the app title,error messages and the progress bar.
        """
        self.error_placeholder, self.progress_bar_placeholder = self.ui_service.render_main_window()

    def prepare_side_bar(self) -> None:
        """
        Creates the sidebar layout, which includes:
        - A file uploader for the user’s file
        - A button for loading the toy dataset
        - A App number_input for setting the TF-IDF feature count
        - A App number_input for setting n_clusters (used by the KMeans algorithm)
        - A App selection box for choosing from the last three loaded user DataFrames
        """

        sidebar_state = self.ui_service.render_sidebar(self.session_manager.get("api_key"))

        self.session_manager.set("uploaded_file", sidebar_state["uploaded_file"])
        self.session_manager.set("max_features", sidebar_state["max_features"])
        self.session_manager.set("num_clusters", sidebar_state["num_clusters"])

        if sidebar_state["save_api_key_clicked"]:
            try:
                self.session_manager.set("api_key", sidebar_state["api_key"])
                self.apiclient.api_key = sidebar_state["api_key"]
                asyncio.run(self.apiclient.check_api_availability(with_api_key=True))
                self.update_on_success(message="API key is valid and saved successfully")
            except ResponseStatusException as e:
                self.update_on_error(message=e.message)

        if sidebar_state["load_pmids_clicked"]:
            try:
                self.handle_user_dataset()
            except NotEnoughPmidsInTxtFileException as e:
                self.update_on_error(message=e.message)

        if sidebar_state["load_toy_clicked"]:
            self.load_data_from_redis()

    def prepare_tabs(self) -> None:
        """
        Creates two tabs:
        1) A Visualization tab
        2) An Information tab providing general details about the application

        Visualization features:
        - A 3D visualization
        - A select box for choosing PMIDs, experiment types, and organisms
        - A preview of the associated DataFrame
        """
        self.ui_service.render_tabs(
            session_manager=self.session_manager,
            plot_width=MainApp.PLOT_WIDTH,
            plot_height=MainApp.PLOT_HEIGHT,
            info_file_path="src/App/info.md",
        )

    # ----------------------------------- Displaying Errors -----------------------------------
    def update_on_error(self, *args, **kwargs):
        self.error_placeholder.error(kwargs.get("message"))

    def update_progress(self, *args, **kwargs):
        self.progress_bar_placeholder.progress(kwargs.get("measure"))

    def update_on_success(self, *args, **kwargs):
        self.error_placeholder.empty()
        self.error_placeholder.success(kwargs.get("message"))

    # ----------------------------------- Handling initial dataset  -----------------------------------

    def create_initial_redis_database_dump(self) -> None:
        """
        Creates dump.rdb file with initial dataframe that's being loaded while 'Load Toy Dataset'
        is clicked.
        """
        initial_pmids = read_initial_pmids_from_the_file()
        asyncio.run(self.apiclient.main_async_call(initial_pmids))

    def load_data_from_redis(self) -> None:
        """
        Handles the loading and preprocessing of a dataset.

        """
        initial_pmids = read_initial_pmids_from_the_file()
        self.session_manager.set("pmid_df", self.dataset_loading_service.load_initial_dataset_from_redis(initial_pmids))
        self.preprocessing_service.process_loaded_toy_dataset()

    # ----------------------------------- User data handling -----------------------------------
    def handle_user_dataset(self) -> None:
        self.session_manager.set(
            "pmid_df",
            self.dataset_loading_service.load_user_dataset(
                uploaded_file=self.session_manager.get("uploaded_file"),
                min_len_pmid_list=MainApp.MIN_LEN_PMID_LIST,
            ),
        )
        self.preprocessing_service.process_loaded_user_dataset()
