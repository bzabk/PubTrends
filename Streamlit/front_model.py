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
from Preprocessing.text_preprocessing import TextPipeline
from PubMedAPI.pubmed_api import PubMedAPI
import matplotlib.colors as mcolors


class MainApp:

    def __init__(self):

        if "prepared_pubmed_dataframe" not in st.session_state:
            st.session_state.prepared_pubmed_dataframe = None
        if "success_flag" not in st.session_state:
            st.session_state.success_flag = False
        if "uploaded_file" not in st.session_state:
            st.session_state.uploaded_file = None
        if "current_labels" not in st.session_state:
            st.session_state.current_labels = None
        if "current_X" not in st.session_state:
            st.session_state.current_X = None
        if "error_message" not in st.session_state:
            st.session_state.error_message = ""
        if "saved_locally_dataset" not in st.session_state:
            st.session_state.saved_locally_dataset = []
        if "name_deque" not in st.session_state:
            st.session_state.name_deque = deque(maxlen=3)
        if "local_df_deque" not in st.session_state:
            st.session_state.local_df_deque = deque(maxlen=3)

        self.error_placeholder = None
        self.tqdm_placeholder = None

        self.pubmed_api = PubMedAPI(error_callback=self.update_error_message, tqdm_callback=self.set_tqdm_bar)

    # ----------------------------------- Layout Streamlit -----------------------------------
    def prepare_main_window(self) -> None:
        with st.container(key="app_title"):
            st.title("PubTrends: Data Insights for Enhanced Paper Relevance")
        self.error_placeholder = st.empty()
        self.tqdm_placeholder = st.empty()

    def prepare_side_bar(self) -> None:
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
            st.session_state.max_features = st.number_input("Enter a number of features", min_value=1, max_value=200,
                                                            value=10, step=1)
            st.session_state.num_clusters = st.number_input("Enter a number of clusters", min_value=1, max_value=30,
                                                            value=8, step=1)

            if st.session_state.name_deque:
                selected_dataset = st.selectbox("Previously saved datasets", st.session_state.name_deque)
                if st.button("Load previously saved dataset"):
                    index = st.session_state.name_deque.index(selected_dataset)
                    st.session_state.prepared_pubmed_dataframe = st.session_state.local_df_deque[index]
                    self.handle_preloaded_dataset(load_toy_dataset=False)



    def prepare_tabs(self) -> None:
        tab_visualization, tab_info = st.tabs(["Visualization", "Info"])
        with tab_visualization:
            if st.session_state.success_flag:
                plot_placeholder = st.empty()
                plot_placeholder.empty()

                plot_placeholder.plotly_chart(self.load_3d_plot("3d_plot_selected"), key="3d_plot_selected")


                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    p1 = st.selectbox(
                        "Pmid",
                        ["<select>"] + sorted(
                            st.session_state.prepared_pubmed_dataframe["Pmid"].unique().tolist()),
                        key="Pmid"
                    )
                with col2:
                    p2 = st.selectbox(
                        "Organism",
                        ["<select>"] + st.session_state.prepared_pubmed_dataframe["Organism"].unique().tolist(),
                        key="Organism"
                    )
                with col3:
                    p3 = st.selectbox(
                        "Experiment type",
                        ["<select>"] + st.session_state.prepared_pubmed_dataframe["Experiment_type"].unique().tolist(),
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
                                st.session_state.prepared_pubmed_dataframe["Pmid"] == selected_pmid)
                        if selected_organism != "<select>":
                            conditions.append(
                                st.session_state.prepared_pubmed_dataframe["Organism"] == selected_organism)
                        if selected_experiment_type != "<select>":
                            conditions.append(st.session_state.prepared_pubmed_dataframe[
                                                  "Experiment_type"] == selected_experiment_type)
                        if conditions:
                            st.session_state.prepared_pubmed_dataframe["is_selected"] = np.logical_and.reduce(
                                conditions).astype(int)
                        else:
                            st.session_state.prepared_pubmed_dataframe["is_selected"] = 1

                        plot_placeholder.empty()
                        plot_placeholder.plotly_chart(self.load_3d_plot("3d_plot_selected"), key="3d_plot_filtered")
                st.dataframe(st.session_state.prepared_pubmed_dataframe[['GSE_code','Title','Summary','Organism','Experiment_type','Overall_design']]
                             [st.session_state.prepared_pubmed_dataframe["is_selected"] == 1])

        with tab_info:
            with open('./Streamlit/info.md','r') as f:
                st.markdown(f.read())

    def update_error_message(self, message) -> None:
        st.session_state.error_message = message
        self.error_placeholder.error(st.session_state.error_message)

    def set_tqdm_bar(self,val) -> None:
        self.tqdm_placeholder.progress(val)

    # ----------------------------------- Preloaded dataset handling -----------------------------------
    def handle_preloaded_dataset(self,load_toy_dataset=True) -> None:
        st.session_state.current_num_clusters = st.session_state.num_clusters
        if load_toy_dataset:
            self.load_preloaded_dataset_from_csv()
        self.validate_user_preprocessing_parameters()
        self.reset_select_boxes()
        self.preprocess_raw_text()
        st.session_state.prepared_pubmed_dataframe["is_selected"] = 1
        st.session_state.success_flag = True

    def reset_select_boxes(self) -> None:
        st.session_state["Pmid"] = "<select>"
        st.session_state["Organism"] = "<select>"
        st.session_state["Experiment_type"] = "<select>"

    def load_preloaded_dataset_from_csv(self) -> None:
        csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'PubMedAPI', 'PubMed_data.csv'))
        st.session_state.prepared_pubmed_dataframe = pd.read_csv(csv_path)

    # ----------------------------------- User data handling -----------------------------------

    def set_dataframe_from_pmids(self, list_of_pmids) -> None:
        self.pubmed_api.pmids = list_of_pmids
        self.pubmed_api.create_dataframe(list_of_pmids=self.pubmed_api.pmids)
        st.session_state.prepared_pubmed_dataframe = self.pubmed_api.df

    def load_user_data(self) -> None:
        uploaded_file = st.session_state.uploaded_file
        self.pubmed_api.pmids = self.validate_chosen_file(uploaded_file)
        if len(self.pubmed_api.pmids) < 10:
            self.update_error_message("Please enter at least 10 PMIDs.")

    def validate_chosen_file(self, uploaded_file) -> list[int]:
        file_content = uploaded_file.read().decode("utf-8")
        list_of_pmids = []
        pmids = file_content.split("\n")
        for line in pmids:
            line = line.replace(" ", "").strip()
            if line.isdigit():
                list_of_pmids.append(int(line))
        list_of_pmids = self.remove_duplicated_pmids_from_user_list(list_of_pmids)
        if len(list_of_pmids) < 10:
            self.update_error_message("Please enter at least 10 PMIDs.")
        return list_of_pmids

    def handle_user_dataset(self) -> None:
        st.session_state.current_num_clusters = st.session_state.num_clusters
        self.reset_select_boxes()
        self.load_user_data()
        self.tqdm_placeholder.progress(0)
        self.set_dataframe_from_pmids(self.pubmed_api.pmids)
        self.validate_user_preprocessing_parameters()
        self.preprocess_raw_text()
        st.session_state.prepared_pubmed_dataframe["is_selected"] = 1
        self.error_placeholder.empty()
        self.tqdm_placeholder.empty()
        st.session_state.success_flag = True
        self.save_locally_dataset()

    def save_locally_dataset(self) -> None:
        now = datetime.datetime.now()
        idx = len(st.session_state.name_deque)
        st.session_state.name_deque.appendleft(f"Dataset: [{idx}] {now.strftime('%Y-%m-%d %H-%M-%S')}")
        st.session_state.local_df_deque.appendleft(st.session_state.prepared_pubmed_dataframe)


    # ----------------------------------- Preprocessing -----------------------------------
    def validate_user_preprocessing_parameters(self) -> None:
        if st.session_state.max_features is None:
            st.session_state.max_features = 10
        if st.session_state.num_clusters is None:
            st.session_state.num_clusters = 8
        n_samples = len(st.session_state.prepared_pubmed_dataframe)
        perplexity = min(30, n_samples - 1)
        st.session_state.text_pipeline = TextPipeline(n_clusters=st.session_state.num_clusters,
                                                      max_features=st.session_state.max_features,
                                                      perplexity=perplexity)

    def preprocess_raw_text(self) -> None:
        st.session_state.prepared_pubmed_dataframe["Text"] = st.session_state.prepared_pubmed_dataframe[
            ["Title", "Summary", "Overall_design", "Experiment_type", "Organism"]
        ].apply(lambda x: ' '.join(x), axis=1)

        st.session_state.prepared_pubmed_dataframe["Experiment_type"] = st.session_state.prepared_pubmed_dataframe[
            "Experiment_type"].apply(
            lambda x: self.remove_semi_duplicated_experiment_type(x)
        )
        st.session_state.prepared_pubmed_dataframe["is_selected"] = 1
        X = st.session_state.text_pipeline.fit_transform_text_processing_pipeline(
            st.session_state.prepared_pubmed_dataframe["Text"]
        ).toarray()
        st.session_state.text_pipeline.fit_kmeans(X)
        st.session_state.current_X = st.session_state.text_pipeline.fit_transform_tsne(X)
        st.session_state.current_labels = st.session_state.text_pipeline.cluster.labels_.astype(str)

    # ----------------------------------- Visualization -----------------------------------
    def load_3d_plot(self, key) -> go.Figure:
        colors = self.set_colors_and_opacity()
        st.session_state.prepared_pubmed_dataframe["colors"] = colors
        hover_text_selected = [
            f"<b>{title}</b><br>GSE Code: {gse_code}<br>PMID: {pmid}<br>Organism: {organism}<br>Experiment_type: {experiment_type}"
            for title, gse_code, pmid, organism, experiment_type in zip(

                st.session_state.prepared_pubmed_dataframe["Title"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 1],
                st.session_state.prepared_pubmed_dataframe["GSE_code"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 1],
                st.session_state.prepared_pubmed_dataframe["Pmid"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 1],
                st.session_state.prepared_pubmed_dataframe["Organism"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 1],
                st.session_state.prepared_pubmed_dataframe["Experiment_type"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 1],
            )

        ]

        hover_text_not_selected = [
            f"<b>{title}</b><br>GSE Code: {gse_code}<br>PMID: {pmid}<br>Organism: {organism}<br>Experiment_type: {experiment_type}"
            for title, gse_code, pmid, organism, experiment_type in zip(
                st.session_state.prepared_pubmed_dataframe["Title"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 0],
                st.session_state.prepared_pubmed_dataframe["GSE_code"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 0],
                st.session_state.prepared_pubmed_dataframe["Pmid"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 0],
                st.session_state.prepared_pubmed_dataframe["Organism"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 0],
                st.session_state.prepared_pubmed_dataframe["Experiment_type"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 0]
            )
        ]

        trace1 = go.Scatter3d(
            x=st.session_state.current_X[st.session_state.prepared_pubmed_dataframe["is_selected"] == 1, 0],
            y=st.session_state.current_X[st.session_state.prepared_pubmed_dataframe["is_selected"] == 1, 1],
            z=st.session_state.current_X[st.session_state.prepared_pubmed_dataframe["is_selected"] == 1, 2],
            mode='markers',
            marker=dict(
                color=st.session_state.prepared_pubmed_dataframe["colors"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 1],
                size=8,
                opacity=1
            ),
            hovertext=hover_text_selected,
            hoverinfo='text',
        )

        trace2 = go.Scatter3d(
            x=st.session_state.current_X[st.session_state.prepared_pubmed_dataframe["is_selected"] == 0, 0],
            y=st.session_state.current_X[st.session_state.prepared_pubmed_dataframe["is_selected"] == 0, 1],
            z=st.session_state.current_X[st.session_state.prepared_pubmed_dataframe["is_selected"] == 0, 2],
            mode='markers',
            marker=dict(
                color=st.session_state.prepared_pubmed_dataframe["colors"][
                    st.session_state.prepared_pubmed_dataframe["is_selected"] == 0],
                size=8,
                opacity=0.08
            ),
            hovertext=hover_text_not_selected,
            hoverinfo='text',
        )

        fig = go.Figure()
        fig.add_trace(trace1)
        fig.add_trace(trace2)

        fig.update_layout(
            scene=dict(
                xaxis_title='X',
                yaxis_title='Y',
                zaxis_title='Z'
            ),
            width=900, height=600
        )
        fig.update_layout(showlegend=False)

        return fig

    def set_colors_and_opacity(self) -> list[str]:
        unique_labels = np.arange(0, st.session_state.current_num_clusters,1).astype(str)
        colors = px.colors.qualitative.Alphabet
        color_palette = colors[:len(unique_labels)]
        map_dict = dict(zip(unique_labels, color_palette))
        list_of_colors = [map_dict[label] for label in st.session_state.current_labels]
        idx = 0
        color_palette_final = []
        for col in list_of_colors:
            if st.session_state.prepared_pubmed_dataframe["is_selected"].iloc[idx] == 1:
                color_palette_final.append(self.hex_to_rgba(col, alpha=1))
            else:
                color_palette_final.append(self.hex_to_rgba(col, alpha=0.2))
            idx += 1
        return color_palette_final

    @staticmethod
    def load_styles() -> None:
        css_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Static', 'style.css'))
        with open(css_path) as css:
            st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

    @staticmethod
    def remove_semi_duplicated_experiment_type(text: str) -> str:
        text = text.split(";")
        text = [t.strip() for t in text]
        text.sort()
        if "Other" in text:
            text.remove("Other")
        text = [t for t in text if t.strip() != "Other"]
        new_text = ";".join(text)
        return new_text

    @staticmethod
    def remove_duplicated_pmids_from_user_list(pmids: list[int]) -> list[int]:
        return list(set(pmids))

    @staticmethod
    def hex_to_rgba(hex_color, alpha) -> str:
        rgba = mcolors.to_rgba(hex_color, alpha)
        return f'rgba({int(rgba[0] * 255)}, {int(rgba[1] * 255)}, {int(rgba[2] * 255)})'


if __name__ == "__main__":
    app = MainApp()
    app.load_styles()
    app.prepare_main_window()
    app.prepare_side_bar()
    app.prepare_tabs()
