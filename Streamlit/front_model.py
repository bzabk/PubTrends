import numpy as np
import streamlit as st
import pandas as pd
import sys
import os
import plotly.express as px
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from Preprocessing.text_preprocessing import TextPipeline
from PubMedAPI.pubmed_api import PubMedAPI
class MainApp:


    def __init__(self):
        self.prepared_pubmed_dataframe = None

        self.pubmed_api = PubMedAPI()
        self.sucess_flag = False

        self.current_X = None
        self.current_labels = None

        self.text_pipeline = TextPipeline(n_clusters=8,max_features=10)
        if "uploaded_file" not in st.session_state:
            st.session_state.uploaded_file = None
    #----------------------------------- Streamlit layout preparation -----------------------------------
    def prepare_side_bar(self):
        with st.sidebar:
            st.sidebar.title("Enter txt file with list of PMIDs", anchor="center")
            st.session_state.uploaded_file = st.file_uploader("Choose a file", type=["txt"], accept_multiple_files=False, label_visibility="collapsed")
            if st.session_state.uploaded_file is not None:
                if st.button("Load PMIDS file", use_container_width=True):
                    self.handle_user_dataset()
            st.text("or choose a preloaded dataset")

            if st.button("Load preloaded dataset", use_container_width=True):
                self.handle_preloaded_dataset()

    def prepare_main_window(self):
        with st.container(key="app_title"):
            st.title("PubTrends: Data Insights for Enhanced Paper Relevance")

    def prepare_tabs(self):
        tab_visualization, tab_info = st.tabs(["Visualization", "Info"])
        with tab_visualization:
            if self.sucess_flag:
                self.load_3d_plot()
                self.sucess_flag = False
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.selectbox("Original PMID", self.prepared_pubmed_dataframe["Original_PMID"].unique(), key="original_pmid", index=0)
                with col2:
                    st.selectbox("Organism", self.prepared_pubmed_dataframe["Organism"].unique())
                with col3:
                    st.selectbox("Experiment type", self.prepared_pubmed_dataframe["Experiment_type"].unique())




        with tab_info:
            pass
    #----------------------------------- Preloaded data handling -----------------------------------
    def handle_preloaded_dataset(self):
        self.load_preloaded_dataset_from_csv()
        self.preprocess_raw_text()
        self.sucess_flag = True

    def load_preloaded_dataset_from_csv(self):
        csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'PubMedAPI', 'PubMed_data.csv'))
        self.prepared_pubmed_dataframe = pd.read_csv(csv_path)

    #----------------------------------- Handling user data -----------------------------------
    def validate_chosen_file(self,uploaded_file):
        file_content = uploaded_file.read().decode("utf-8")
        list_of_pmids = []
        pmids = file_content.split("\n")
        for line in pmids:
            line = line.replace(" ", "")
            if line.isdigit():
                list_of_pmids.append(int(line))
        return list_of_pmids

    def load_user_data(self):
        uploaded_file = st.session_state.uploaded_file
        self.pubmed_api.pmids = self.validate_chosen_file(uploaded_file)

    def handle_user_dataset(self):
        self.load_user_data()
        self.set_dataframe_from_pmids(self.pubmed_api.pmids)
        self.preprocess_raw_text()
        self.sucess_flag = True

    def set_dataframe_from_pmids(self,list_of_pmids):
        self.pubmed_api.pmids = list_of_pmids
        self.pubmed_api.create_dataframe(is_from_file=False,list_of_pmids=self.pubmed_api.pmids)
        self.prepared_pubmed_dataframe = self.pubmed_api.df

    # ----------------------------------- Preprocessing -----------------------------------
    def preprocess_raw_text(self):
        self.prepared_pubmed_dataframe["Text"] = self.prepared_pubmed_dataframe[["Title","Summary","Overall_design","Experiment_type","Organism"]].apply(lambda x: ' '.join(x),axis=1)
        self.prepared_pubmed_dataframe["Experiment_type"] = self.prepared_pubmed_dataframe["Experiment_type"].apply(lambda x: self.remove_duplicated_experiment_type(x))
        X = self.text_pipeline.fit_transform_text_processing_pipeline(self.prepared_pubmed_dataframe["Text"]).toarray()

        self.text_pipeline.fit_kmeans(X)
        self.current_X = self.text_pipeline.fit_transform_tsne(X)
        self.current_labels = self.text_pipeline.cluster.labels_.astype(str)

    # ----------------------------------- Visualization -----------------------------------
    def load_3d_plot(self):
        self.prepared_pubmed_dataframe["Formatted_Title"] = self.prepared_pubmed_dataframe["Title"].apply(lambda x: self.format_title(x))
        fig = px.scatter_3d(
            x = self.current_X[:,0],
            y = self.current_X[:,1],
            z = self.current_X[:,2],
            color = self.current_labels,
            size_max=3,
            category_orders={"color": np.unique(self.current_labels)},
            hover_data={
                'Gse_code': self.prepared_pubmed_dataframe["GSE_code"],
                'Original_PMID': self.prepared_pubmed_dataframe["Original_PMID"],
                'Title': self.prepared_pubmed_dataframe["Formatted_Title"],
                'Organism': self.prepared_pubmed_dataframe["Organism"]
            }
        )

        fig.update_traces(hovertemplate='<b>%{customdata[2]}</b><br>GSE Code: %{customdata[0]}<br>PMID: %{customdata[1]}<br>Organism: %{customdata[3]}',
                          hoverlabel=dict(align='left'))
        fig.update_layout(scene=dict(
            xaxis_title='X',
            yaxis_title='Y',
            zaxis_title='Z'
        ),width=900, height=600)

        st.plotly_chart(fig)

    @staticmethod
    def load_styles():
        css_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'Static', 'style.css'))
        with open(css_path) as css:
            st.markdown(f"<style>{css.read()}</style>", unsafe_allow_html=True)

    @staticmethod
    def format_title(text: str) -> str:
        words = text.split()
        new_text = ""
        for i in range(0,len(text),5):
            new_text += ' '.join(words[i:i+5]) + "\n"
        return new_text.strip()

    @staticmethod
    def remove_duplicated_experiment_type(text: str) -> str:
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

if __name__ == "__main__":
    app = MainApp()
    app.load_styles()
    app.prepare_main_window()
    app.prepare_side_bar()
    app.prepare_tabs()

