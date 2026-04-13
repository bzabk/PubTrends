import streamlit as st


class UIService:

    PLOT_WIDTH = 900
    PLOT_HEIGHT = 600
    INFO_MD_PATH = "src/app/info.md"

    def render_main_window(self):
        with st.container():
            st.title("PubTrends: Data Insights for Enhanced Paper Relevance")
        error_placeholder = st.empty()
        progress_bar_placeholder = st.empty()
        return error_placeholder, progress_bar_placeholder

    def render_sidebar(self, api_key_value):
        with st.sidebar:
            st.sidebar.title("Provide API key")
            api_key = st.text_input("Enter your ", type="password", value=api_key_value or "")
            save_api_key_clicked = st.button("Save api key")

            st.sidebar.title("Enter txt file with list of PMIDs", anchor="center")
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=["txt"],
                accept_multiple_files=False,
                label_visibility="collapsed",
            )
            load_pmids_clicked = uploaded_file is not None and st.button("Load PMIDs file", use_container_width=True)

            st.text("or choose a toy dataset")
            load_toy_clicked = st.button("Load toy dataset", use_container_width=True)

            st.text("Set parameters for TF-IDF")
            max_features = st.number_input(
                "Enter a number of features",
                min_value=3,
                max_value=200,
                value=10,
                step=1,
            )
            num_clusters = st.number_input(
                "Enter a number of clusters", min_value=1, max_value=30, value=8, step=1
            )

        return {
            "api_key": api_key,
            "save_api_key_clicked": save_api_key_clicked,
            "uploaded_file": uploaded_file,
            "load_pmids_clicked": load_pmids_clicked,
            "load_toy_clicked": load_toy_clicked,
            "max_features": max_features,
            "num_clusters": num_clusters,
        }

    def render_tabs(self, session_manager):
        tab_visualization, tab_info = st.tabs(["Visualization", "Info"])

        with tab_visualization:
            if session_manager.get("success_flag"):
                from src.app.front_model_utils import load_3d_plot

                plot_placeholder = st.empty()
                plot_placeholder.empty()

                plot_placeholder.plotly_chart(
                    load_3d_plot(UIService.PLOT_WIDTH, UIService.PLOT_HEIGHT),
                    key="3d_plot_selected",
                )

                pmid_df = session_manager.get("pmid_df")
                col1, col2, col3, col4 = st.columns(4)

                with col1:
                    selected_pmid = st.selectbox(
                        "Pmid",
                        ["<select>"] + sorted(pmid_df["Pmid"].unique().tolist()),
                        key="Pmid",
                    )
                with col2:
                    selected_organism = st.selectbox(
                        "Organism",
                        ["<select>"] + pmid_df["Organism"].unique().tolist(),
                        key="Organism",
                    )
                with col3:
                    selected_experiment_type = st.selectbox(
                        "Experiment type",
                        ["<select>"] + pmid_df["Experiment_type"].unique().tolist(),
                        key="Experiment_type",
                    )
                with col4:
                    if st.button("Filter"):
                        import numpy as np

                        conditions = []
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
                        session_manager.set("pmid_df", pmid_df)

                        plot_placeholder.empty()
                        plot_placeholder.plotly_chart(
                            load_3d_plot(UIService.PLOT_WIDTH, UIService.PLOT_HEIGHT),
                            key="3d_plot_filtered",
                        )

                st.dataframe(
                    pmid_df[
                        [
                            "GSE_code",
                            "Title",
                            "Summary",
                            "Organism",
                            "Experiment_type",
                            "Overall_design",
                        ]
                    ][pmid_df["is_selected"] == 1]
                )

        with tab_info:
            with open(UIService.INFO_MD_PATH, "r") as file:
                st.markdown(file.read())
