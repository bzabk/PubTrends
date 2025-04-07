from collections import deque
import numpy as np
import streamlit as st
import pandas as pd
import sys
import os
import datetime
import plotly.express as px
import plotly.graph_objects as go
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Preprocessing.text_preprocessing import *
from PubMedAPI.pubmed_api import PubMedAPI
import matplotlib.colors as mcolors
from PubMedAPI.observer import Observer

class MainApp(Observer):
    """
    Main application class for the PubTrends app.
    This class handles the initialization of the App session state,
    layout preparation, data loading, preprocessing, and visualization.

    Attributes:
    error_placeholder (st.empty): Placeholder for displaying error messages.
    progress_bar_placeholder (st.empty): Placeholder for displaying the progress bar.
    pubmed_api (PubMedAPI): Instance of the PubMedAPI class for fetching data from PubMed.
    """
    DEQUE_MAX_LENGTH = 3
    PERPLEXITY_MIN = 30
    PLOT_WIDTH = 900
    PLOT_HEIGHT = 600
    MIN_LEN_PMID_LIST = 10
    def __init__(self):
        """
        Some of the variables we want to save between streamlit sessions
        """
        if "pmid_df" not in st.session_state:
            st.session_state.pmid_df = None
        if "success_flag" not in st.session_state:
            st.session_state.success_flag = False
        if "uploaded_file" not in st.session_state:
            st.session_state.uploaded_file = None
        if "current_labels" not in st.session_state:
            st.session_state.current_labels = None
        if "current_X" not in st.session_state:
            st.session_state.current_X = None
        if "saved_locally_dataset" not in st.session_state:
            st.session_state.saved_locally_dataset = []
        if "name_deque" not in st.session_state:
            st.session_state.name_deque = deque(maxlen=MainApp.DEQUE_MAX_LENGTH)
        if "local_df_deque" not in st.session_state:
            st.session_state.local_df_deque = deque(maxlen=MainApp.DEQUE_MAX_LENGTH)
        if "kmeans_processor" not in st.session_state:
            st.session_state.kmeans_processor = None
        if "tfidf_processor" not in st.session_state:
            st.session_state.tfidf_processor = None
        if "tsne_processor" not in st.session_state:
            st.session_state.tsne_processor = None


        self.progress_bar_placeholder = None
        self.error_placeholder = None
        self.pubmed_api = PubMedAPI()
        #adding observer to pubmed_api instance
        self.pubmed_api.attach(self)
        """
        Remove_Punctuation only provides text processing without any saving any parameters so it does not need 
        to be remembered between streamlit sessions
        """
        st.session_state.remove_punctuation = ProcessorFactory.get_processor("remove_punctuation")

    # ----------------------------------- Layout App -----------------------------------
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
            st.sidebar.title("Enter txt file with list of PMIDs", anchor="center")
            st.session_state.uploaded_file = st.file_uploader("Choose a file", type=["txt"],
                                                              accept_multiple_files=False, label_visibility="collapsed")
            if st.session_state.uploaded_file is not None:
                if st.button("Load PMIDs file", use_container_width=True):

                    self.handle_user_dataset()
            st.text("or choose a toy dataset")
            if st.button("Load toy dataset", use_container_width=True):
                self.handle_preloaded_dataset()
            st.text("Set parameters for TF-IDF")
            st.session_state.max_features = st.number_input("Enter a number of features", min_value=3, max_value=200,
                                                            value=10, step=1)
            st.session_state.num_clusters = st.number_input("Enter a number of clusters", min_value=1, max_value=30,
                                                            value=8, step=1)

            if st.session_state.name_deque:
                selected_dataset = st.selectbox("Previously saved datasets", st.session_state.name_deque)
                if st.button("Load previously saved dataset"):
                    idx = st.session_state.name_deque.index(selected_dataset)
                    st.session_state.pmid_df = st.session_state.local_df_deque[idx]
                    self.handle_preloaded_dataset(load_toy_dataset=False)



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
            if st.session_state.success_flag:
                plot_placeholder = st.empty()
                plot_placeholder.empty()

                plot_placeholder.plotly_chart(self.load_3d_plot("3d_plot_selected"), key="3d_plot_selected")


                col1, col2, col3, col4 = st.columns(4)
                #filters
                with col1:
                    p1 = st.selectbox("Pmid",["<select>"] + sorted(st.session_state.pmid_df["Pmid"].unique().tolist()),
                        key="Pmid"
                    )
                with col2:
                    p2 = st.selectbox("Organism",["<select>"] + st.session_state.pmid_df["Organism"].unique().tolist(),
                        key="Organism"
                    )
                with col3:
                    p3 = st.selectbox("Experiment type",["<select>"] + st.session_state.pmid_df["Experiment_type"].unique().tolist(),
                        key="Experiment_type"
                    )
                with col4:
                    if st.button("Filter"):
                        selected_pmid = st.session_state["Pmid"]
                        selected_organism = st.session_state["Organism"]
                        selected_experiment_type = st.session_state["Experiment_type"]

                        conditions = []
                        if selected_pmid != "<select>":
                            conditions.append(
                                st.session_state.pmid_df["Pmid"] == selected_pmid)
                        if selected_organism != "<select>":
                            conditions.append(
                                st.session_state.pmid_df["Organism"] == selected_organism)
                        if selected_experiment_type != "<select>":
                            conditions.append(st.session_state.pmid_df[
                                                  "Experiment_type"] == selected_experiment_type)
                        if conditions:
                            st.session_state.pmid_df["is_selected"] = np.logical_and.reduce(
                                conditions).astype(int)
                        else:
                            st.session_state.pmid_df["is_selected"] = 1

                        plot_placeholder.empty()
                        plot_placeholder.plotly_chart(self.load_3d_plot("3d_plot_selected"), key="3d_plot_filtered")
                st.dataframe(st.session_state.pmid_df[['GSE_code','Title','Summary','Organism','Experiment_type','Overall_design']]
                             [st.session_state.pmid_df["is_selected"] == 1])

        with tab_info:
            with open('./App/info.md','r') as f:
                st.markdown(f.read())

    # ----------------------------------- Displaying Errors -----------------------------------
    def update_on_error(self,*args,**kwargs):
        """
        Updates the error message displayed in the Streamlit application when an error occurs.

        Parameters:
        observable (Observable): The observable object that notifies the observer of an error.
        **kwargs: Additional keyword arguments, expected to contain a 'message' key with the error message.
        """
        if "message" in kwargs:
            self.error_placeholder.error(kwargs.get("message"))

    def update_progress(self,*args,**kwargs):
        """
        Updates the progress bar in the Streamlit application when progress is notified in PubMedAPI class.

        Parameters:
        observable (Observable): The observable object that notifies the observer of progress.
        **kwargs: Additional keyword arguments, expected to contain a 'measure' key with the progress value.
        """
        if "measure" in kwargs:
            self.progress_bar_placeholder.progress(kwargs.get("measure"))

    # ----------------------------------- Toy dataset handling -----------------------------------
    def handle_preloaded_dataset(self,load_toy_dataset: bool=True) -> None:
        """
        Handles the loading and preprocessing of a dataset.

        Parameters:
        load_toy_dataset (bool): If True, loads a toy dataset.
                                 If False, loads a previously saved dataset st selection_box.
        """
        st.session_state.current_num_clusters = st.session_state.num_clusters
        if load_toy_dataset:
            self.load_toy_dataset_from_csv()
        self.validate_user_preprocessing_parameters()
        self.reset_select_boxes()
        self.preprocess_raw_text()
        st.session_state.success_flag = True
    @staticmethod
    def reset_select_boxes() -> None:
        """
        After loading a new dataset and setting a new 3D plot,
        reset the previous selections in the select boxes.
        """
        st.session_state["Pmid"] = "<select>"
        st.session_state["Organism"] = "<select>"
        st.session_state["Experiment_type"] = "<select>"

    @staticmethod
    def load_toy_dataset_from_csv() -> None:
        """
        Load toy dataset from csv file
        """
        csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'PubMedAPI', 'PubMed_data.csv'))
        st.session_state.pmid_df = pd.read_csv(csv_path)

    # ----------------------------------- User data handling -----------------------------------

    def set_dataframe_from_pmids(self, list_of_pmids) -> None:
        """
        Create a DataFrame with the following columns:
        Pmid, Geo_dataset_ind, GSE_code, Title, Summary, Overall_design, Experiment_type, Organism.
        The DataFrame is created using a list of PMIDs and `self.pubmed_api`,
        which is an instance of the PubMedAPI class.
        """
        self.pubmed_api.pmids = list_of_pmids
        self.pubmed_api.create_dataframe(list_of_pmids=self.pubmed_api.pmids)
        st.session_state.pmid_df = self.pubmed_api.df

    def load_user_data(self) -> None:
        """
        Load user data from the uploaded file.
        This method retrieves the uploaded file from the session state, validates the PMIDs in the file,
        and updates the error message if there are fewer than 10 valid PMIDs.
        """
        uploaded_file = st.session_state.uploaded_file

        self.pubmed_api.pmids = self.validate_chosen_file(uploaded_file)

    def validate_chosen_file(self, uploaded_file) -> list[int] | None:
        """
        Function checks whether the uploaded file is in the correct format and extracts PMIDs from it.
        In case user uploaded less than 10 correct PMIDs, an error message is displayed.
        If txt file contains less than 10 PMIDs, the error message is displayed.

        :param uploaded_file: The file uploaded by the user.

        :return list[int]: A list of unique PMIDs extracted from the file.
        """
        file_content = uploaded_file.read().decode("utf-8")
        list_of_pmids = []
        pmids = file_content.split("\n")
        for line in pmids:
            line = line.replace(" ", "").strip()
            if line.isdigit():
                list_of_pmids.append(int(line))
        list_of_pmids = list(set(list_of_pmids))
        if len(list_of_pmids) < MainApp.MIN_LEN_PMID_LIST:
            self.update_on_error(message="Please enter at least 10 PMIDs.")
            raise Exception
        return list_of_pmids

    def handle_user_dataset(self) -> None:
        """
        Processes PMIDs provided by the user through a .txt file.
        Displays a descriptive message if any of the underlying methods raise an error.
        """
        try:
            st.session_state.current_num_clusters = st.session_state.num_clusters
            self.reset_select_boxes()
            self.load_user_data()
            self.update_progress(measure=0)
            self.set_dataframe_from_pmids(self.pubmed_api.pmids)
            self.validate_user_preprocessing_parameters()
            self.preprocess_raw_text()
            self.error_placeholder.empty()
            self.progress_bar_placeholder.empty()
            self.save_locally_dataset()
            st.session_state.success_flag = True
        except Exception as e:
            return

    @staticmethod
    def save_locally_dataset() -> None:
        """
        Saving last 3 datasets to deque with max length 3, which later can be visualized again
        by selecting them in st.select_box
        """
        now = datetime.datetime.now()
        st.session_state.name_deque.appendleft(f"Dataset: {now.strftime('%Y-%m-%d %H-%M-%S')}")
        st.session_state.local_df_deque.appendleft(st.session_state.pmid_df)


    # ----------------------------------- Preprocessing -----------------------------------
    @staticmethod
    def validate_user_preprocessing_parameters() -> None:
        """
        This method checks whether the `max_features` and `num_clusters` parameters are set in the session state.
        If not, it assigns default values.
        The `perplexity` parameter must be set manually. If its value is higher than the number of data points
        in the DataFrame, t-SNE will raise an error.
        If the user provides an incorrect value for num_features or num_clusters, the last valid parameters will be used instead.
        """
        if st.session_state.max_features is None:
            st.session_state.max_features = 10
        if st.session_state.num_clusters is None:
            st.session_state.num_clusters = 8
        n_samples = len(st.session_state.pmid_df)
        perplexity = min(MainApp.PERPLEXITY_MIN, n_samples - 1)

        st.session_state.tsne_processor = ProcessorFactory.get_processor("tsne",perplexity=perplexity)
        st.session_state.kmeans_processor = ProcessorFactory.get_processor("kmeans",n_clusters=st.session_state.num_clusters)
        st.session_state.tfidf_processor = ProcessorFactory.get_processor("tfidf",max_features=st.session_state.max_features)

    @staticmethod
    def preprocess_raw_text() -> None:
        """
        Main function for processing raw text from a DataFrame into 3D points.
        Steps:
        1) Handle and remove semi-duplicated 'Experiment_type' entries.
        2) Concatenate all relevant columns.
        3) Set the 'is_selected' column to 1 by default (ensuring no points have lower opacity).
        4) Apply TF-IDF to the concatenated text.
        5) Reduce dimensionality to 3D.
        6) Fit the KMeans algorithm and store the resulting labels in st.session_state.
        """
        st.session_state.pmid_df = st.session_state.remove_punctuation.process(st.session_state.pmid_df)
        st.session_state.current_X = st.session_state.tfidf_processor.process(st.session_state.pmid_df["Text"])
        st.session_state.current_X = st.session_state.tsne_processor.process(st.session_state.current_X)
        st.session_state.kmeans_processor.process(st.session_state.current_X)
        st.session_state.current_labels = st.session_state.kmeans_processor.cluster.labels_.astype(str)

    # ----------------------------------- Visualization -----------------------------------
    def load_3d_plot(self, key) -> go.Figure:
        """
        Main function responsible for displaying interactive 3D plot visualizing
        layout of the data points in 3D space.

        :return go.Figure: prepared 3D plot ready to display
        """
        # setting list of colors for each point in the dataframe
        self.set_colors_and_opacity()
        #creating hover text for these points that were selected by user
        hover_text_selected = self._create_hover_text(is_selected=1)
        hover_text_not_selected = self._create_hover_text(is_selected=0)
        # set of selected points with opacity 1
        trace1 = self._create_trace(is_selected=1, opacity=1, hover_text=hover_text_selected)
        trace2 = self._create_trace(is_selected=0, opacity=0.08, hover_text=hover_text_not_selected)

        fig = go.Figure()
        fig.add_trace(trace1)
        fig.add_trace(trace2)

        fig.update_layout(scene=dict(xaxis_title='X',yaxis_title='Y',zaxis_title='Z'),
            width=MainApp.PLOT_WIDTH,height=MainApp.PLOT_HEIGHT,showlegend=False)
        return fig

    @staticmethod
    def _create_hover_text(is_selected: int) -> list[str]:
        hover_text_selected = [
            f"<b>{row['Title']}</b><br>GSE Code: {row['GSE_code']}<br>PMID: {row['Pmid']}<br>Organism: {row['Organism']}<br>Experiment_type: {row['Experiment_type']}"
            for _, row in st.session_state.pmid_df[st.session_state.pmid_df["is_selected"] == is_selected].iterrows()
        ]
        return hover_text_selected

    @staticmethod
    def _create_trace(is_selected: int,opacity: float,hover_text: list[str]) -> go.Scatter3d:
        return go.Scatter3d(
            x=st.session_state.current_X[st.session_state.pmid_df["is_selected"] == is_selected, 0],
            y=st.session_state.current_X[st.session_state.pmid_df["is_selected"] == is_selected, 1],
            z=st.session_state.current_X[st.session_state.pmid_df["is_selected"] == is_selected, 2],
            mode='markers',
            marker=dict(
                color=st.session_state.pmid_df["colors"][st.session_state.pmid_df["is_selected"] == is_selected],
                size=8,
                opacity=opacity
            ),
            hovertext=hover_text,
            hoverinfo='text',
        )
    @classmethod
    def set_colors_and_opacity(cls) -> None:
        """
        Function assigns color and opacity to each label from the KMeans algorithm.
        To easly distingush points that satisfied filter conditions, points that were not selected
        """
        unique_labels = np.arange(0, st.session_state.current_num_clusters,1).astype(str)
        colors = px.colors.qualitative.Alphabet
        color_palette = colors[:len(unique_labels)]
        # mapping from unique_labels to color
        map_dict = dict(zip(unique_labels, color_palette))
        #assigning color to each point based on its label
        list_of_colors = [map_dict[label] for label in st.session_state.current_labels]
        idx = 0
        color_palette_final = []
        # looping through all points in dataframe and
        # setting opacity based on whether they were selected by user or not
        for col in list_of_colors:
            if st.session_state.pmid_df["is_selected"].iloc[idx] == 1:
                color_palette_final.append(cls.hex_to_rgba(col, alpha=1))
            else:
                color_palette_final.append(cls.hex_to_rgba(col, alpha=0.2))
            idx += 1
        st.session_state.pmid_df["colors"] = color_palette_final

    @staticmethod
    def load_css_styles() -> None:
        """
        Load CSS styles responsible for setting a fixed sidebar width.
        """
        css_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Static', 'style.css'))
        with open(css_path) as css:
            st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

    @staticmethod
    def hex_to_rgba(hex_color, alpha) -> str:
        """
        Converting hex color format to rgb
        """
        rgba = mcolors.to_rgba(hex_color, alpha)
        return f'rgb({int(rgba[0] * 255)}, {int(rgba[1] * 255)}, {int(rgba[2] * 255)})'


