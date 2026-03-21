import asyncio

from src.App.dataset_loading_service import DatasetLoadingService
from src.App.front_model_utils import (
    reset_select_boxes,
    read_initial_pmids_from_the_file,
    validate_chosen_file,
    load_css_styles,
    load_3d_plot,
    validate_user_preprocessing_parameters,
    preprocess_raw_text,
)
import numpy as np
import streamlit as st
from src.ApiClient.DbCache.RedisCaching import RedisCaching
from src.ApiClient.apiclient import ApiClient
from src.App.statemanager import SessionStateManager
from src.Exceptions.api_client_exceptions import ResponseStatusException
from src.Exceptions.front_model_exceptions import EmptyDataFrameException, NotEnoughPmidsInTxtFileException, \
    FileValidationError
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
        with st.container():
            st.title("PubTrends: Data Insights for Enhanced Paper Relevance")
        self.error_placeholder = st.empty()
        self.progress_bar_placeholder = st.empty()

    def prepare_side_bar(self) -> None:
        """
        Creates the sidebar layout, which includes:
        - A file uploader for the user’s file
        - A button for loading the toy dataset
        - A App number_input for setting the TF-IDF feature count
        - A App number_input for setting n_clusters (used by the KMeans algorithm)
        - A App selection box for choosing from the last three loaded user DataFrames
        """

        with st.sidebar:
            st.sidebar.title("Provide API key")
            api_key = st.text_input("Enter your ", type="password", value=self.session_manager.get("api_key") or "")
            if st.button("Save api key"):
                try:
                    self.session_manager.set("api_key", api_key)
                    self.apiclient.api_key = api_key
                    asyncio.run(self.apiclient.check_api_availability(with_api_key=True))
                    self.update_on_success(message="API key is valid and saved successfully")
                except ResponseStatusException as e:
                    self.update_on_error(message=e.message)

            st.sidebar.title("Enter txt file with list of PMIDs", anchor="center")
            self.session_manager.set("uploaded_file", st.file_uploader(
                "Choose a file",
                type=["txt"],
                accept_multiple_files=False,
                label_visibility="collapsed",
            ))
            if self.session_manager.get("uploaded_file") is not None:
                if st.button("Load PMIDs file", use_container_width=True):
                    try:
                        self.handle_user_dataset()
                    except NotEnoughPmidsInTxtFileException as e:
                        self.update_on_error(message=e.message)
            st.text("or choose a toy dataset")
            if st.button("Load toy dataset", use_container_width=True):
                self.load_data_from_redis()
            st.text("Set parameters for TF-IDF")
            self.session_manager.set("max_features", st.number_input(
                "Enter a number of features",
                min_value=3,
                max_value=200,
                value=10,
                step=1,
            ))
            self.session_manager.set("num_clusters", st.number_input(
                "Enter a number of clusters", min_value=1, max_value=30, value=8, step=1
            ))

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
        tab_visualization, tab_info = st.tabs(["Visualization", "Info"])
        with tab_visualization:
            if self.session_manager.get("success_flag"):
                plot_placeholder = st.empty()
                plot_placeholder.empty()

                plot_placeholder.plotly_chart(
                    load_3d_plot(MainApp.PLOT_WIDTH, MainApp.PLOT_HEIGHT),
                    key="3d_plot_selected",
                )

                col1, col2, col3, col4 = st.columns(4)
                # filters
                with col1:
                    _ = st.selectbox(
                        "Pmid",
                        ["<select>"] + sorted(self.session_manager.get("pmid_df")["Pmid"].unique().tolist()),
                        key="Pmid",
                    )
                with col2:
                    _ = st.selectbox(
                        "Organism",
                        ["<select>"] + self.session_manager.get("pmid_df")["Organism"].unique().tolist(),
                        key="Organism",
                    )
                with col3:
                    _ = st.selectbox(
                        "Experiment type",
                        ["<select>"] + self.session_manager.get("pmid_df")["Experiment_type"].unique().tolist(),
                        key="Experiment_type",
                    )
                with col4:
                    if st.button("Filter"):
                        selected_pmid = self.session_manager.get("Pmid")
                        selected_organism = self.session_manager.get("Organism")
                        selected_experiment_type = self.session_manager.get("Experiment_type")

                        conditions = []
                        pmid_df = self.session_manager.get("pmid_df")
                        if selected_pmid != "<select>":
                            conditions.append(pmid_df["Pmid"] == selected_pmid)
                        if selected_organism != "<select>":
                            conditions.append(pmid_df["Organism"] == selected_organism)
                        if selected_experiment_type != "<select>":
                            conditions.append(pmid_df["Experiment_type"] == selected_experiment_type)
                        if conditions:
                            pmid_df["is_selected"] = np.logical_and.reduce(conditions).astype(int)
                        else:
                            pmid_df["is_selected"] = 1
                        self.session_manager.set("pmid_df", pmid_df)

                        plot_placeholder.empty()
                        plot_placeholder.plotly_chart(
                            load_3d_plot(MainApp.PLOT_WIDTH, MainApp.PLOT_HEIGHT),
                            key="3d_plot_filtered",
                        )
                st.dataframe(
                    self.session_manager.get("pmid_df")[
                        [
                            "GSE_code",
                            "Title",
                            "Summary",
                            "Organism",
                            "Experiment_type",
                            "Overall_design",
                        ]
                    ][self.session_manager.get("pmid_df")["is_selected"] == 1]
                )

        with tab_info:
            with open("src/App/info.md", "r") as f:
                st.markdown(f.read())

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
        validate_user_preprocessing_parameters(MainApp.PERPLEXITY_MIN)
        reset_select_boxes()
        preprocess_raw_text()
        self.session_manager.set("success_flag", True)

    # ----------------------------------- User data handling -----------------------------------
    def handle_user_dataset(self) -> None:
        self.session_manager.set(
            "pmid_df",
            self.dataset_loading_service.load_user_dataset(
                uploaded_file=self.session_manager.get("uploaded_file"),
                min_len_pmid_list=MainApp.MIN_LEN_PMID_LIST,
            ),
        )

        self.session_manager.set("current_num_clusters", self.session_manager.get("num_clusters"))
        validate_user_preprocessing_parameters(MainApp.PERPLEXITY_MIN)
        reset_select_boxes()
        preprocess_raw_text()
        self.session_manager.set("success_flag", True)
