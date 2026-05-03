from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import streamlit as st


@dataclass(frozen=True)
class SidebarState:
    api_key: str
    save_api_key_clicked: bool
    uploaded_file: Any
    load_pmids_clicked: bool
    load_toy_clicked: bool
    max_features: int
    num_clusters: int


class UIService:
    PLOT_WIDTH = 900
    PLOT_HEIGHT = 600
    INFO_MD_PATH = Path(__file__).with_name("info.md")
    SELECT_PLACEHOLDER = "<select>"
    DATAFRAME_COLUMNS = [
        "GSE_code",
        "Title",
        "Summary",
        "Organism",
        "Experiment_type",
        "Overall_design",
    ]

    def render_main_window(self):
        with st.container():
            st.title("PubTrends: Data Insights for Enhanced Paper Relevance")
        error_placeholder = st.empty()
        progress_bar_placeholder = st.empty()
        return error_placeholder, progress_bar_placeholder

    def render_sidebar(self) -> SidebarState:
        with st.sidebar:
            st.title("Provide API key")
            api_key = st.text_input(
                "Enter your API key",
                type="password",
                value="",
            )
            save_api_key_clicked = st.button("Save API key")

            st.title("Enter txt file with list of PMIDs")
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=["txt"],
                accept_multiple_files=False,
                label_visibility="collapsed",
            )
            load_pmids_clicked = uploaded_file is not None and st.button("Load PMIDs file", use_container_width=True)

            st.caption("or choose a toy dataset")
            load_toy_clicked = st.button("Load toy dataset", use_container_width=True)

            st.caption("Set parameters for TF-IDF")
            max_features = st.number_input(
                "Enter a number of features",
                min_value=3,
                max_value=200,
                value=int(st.session_state.get("max_features", 10)),
                step=1,
            )
            num_clusters = st.number_input(
                "Enter a number of clusters",
                min_value=1,
                max_value=30,
                value=int(st.session_state.get("num_clusters", 8)),
                step=1,
            )

        return SidebarState(
            api_key=api_key,
            save_api_key_clicked=save_api_key_clicked,
            uploaded_file=uploaded_file,
            load_pmids_clicked=load_pmids_clicked,
            load_toy_clicked=load_toy_clicked,
            max_features=max_features,
            num_clusters=num_clusters,
        )

    def render_tabs(self) -> None:
        tab_visualization, tab_info = st.tabs(["Visualization", "Info"])

        with tab_visualization:
            if st.session_state.get("success_flag", False):
                self._render_visualization()

        with tab_info:
            st.markdown(self.INFO_MD_PATH.read_text(encoding="utf-8"))

    def _render_visualization(self) -> None:
        from src.app.front_model_utils import load_3d_plot

        plot_placeholder = st.empty()
        pmid_df = st.session_state.get("pmid_df")

        plot_placeholder.plotly_chart(
            load_3d_plot(self.PLOT_WIDTH, self.PLOT_HEIGHT),
            key="3d_plot_selected",
        )

        if pmid_df is None or pmid_df.empty:
            st.warning("The dataset is empty.")
            return

        selected_pmid, selected_organism, selected_experiment_type = self._render_filters(pmid_df)
        if st.button("Filter"):
            filtered_df = self._apply_filters(
                pmid_df,
                selected_pmid=selected_pmid,
                selected_organism=selected_organism,
                selected_experiment_type=selected_experiment_type,
            )
            st.session_state["pmid_df"] = filtered_df
            plot_placeholder.plotly_chart(
                load_3d_plot(self.PLOT_WIDTH, self.PLOT_HEIGHT),
                key="3d_plot_filtered",
            )
            pmid_df = filtered_df

        self._render_dataframe_preview(pmid_df)

    def _render_filters(self, pmid_df: pd.DataFrame):
        col1, col2, col3, _ = st.columns(4)

        with col1:
            selected_pmid = st.selectbox(
                "Pmid",
                [self.SELECT_PLACEHOLDER] + sorted(pmid_df["Pmid"].unique().tolist()),
                key="Pmid",
            )
        with col2:
            selected_organism = st.selectbox(
                "Organism",
                [self.SELECT_PLACEHOLDER] + pmid_df["Organism"].unique().tolist(),
                key="Organism",
            )
        with col3:
            selected_experiment_type = st.selectbox(
                "Experiment type",
                [self.SELECT_PLACEHOLDER] + pmid_df["Experiment_type"].unique().tolist(),
                key="Experiment_type",
            )

        return selected_pmid, selected_organism, selected_experiment_type

    def _apply_filters(
        self,
        pmid_df: pd.DataFrame,
        selected_pmid,
        selected_organism,
        selected_experiment_type,
    ) -> pd.DataFrame:
        filtered_df = pmid_df.copy()
        conditions = []

        if selected_pmid != self.SELECT_PLACEHOLDER:
            conditions.append(filtered_df["Pmid"] == selected_pmid)
        if selected_organism != self.SELECT_PLACEHOLDER:
            conditions.append(filtered_df["Organism"] == selected_organism)
        if selected_experiment_type != self.SELECT_PLACEHOLDER:
            conditions.append(filtered_df["Experiment_type"] == selected_experiment_type)

        if conditions:
            filtered_df["is_selected"] = np.logical_and.reduce(conditions).astype(int)
        else:
            filtered_df["is_selected"] = 1
        return filtered_df

    def _render_dataframe_preview(self, pmid_df: pd.DataFrame) -> None:
        available_columns = [column for column in self.DATAFRAME_COLUMNS if column in pmid_df.columns]
        if not available_columns:
            st.warning("The dataset does not contain the expected preview columns.")
            return

        filtered_df = pmid_df[pmid_df["is_selected"] == 1] if "is_selected" in pmid_df.columns else pmid_df
        st.dataframe(filtered_df[available_columns])
