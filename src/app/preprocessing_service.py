import streamlit as st

from src.app.front_model_utils import (
    preprocess_raw_text,
    reset_select_boxes,
    validate_chosen_file,
    validate_user_preprocessing_parameters,
)


class PreprocessingService:
    PERPLEXITY_MIN = 30

    def validate_chosen_file(self, uploaded_file, min_len_pmid_list=10) -> None:
        pmid_list = validate_chosen_file(uploaded_file, min_len_pmid_list)
        st.session_state["pmid_list"] = pmid_list

    def process_dataframe_from_session_cache(self):
        validate_user_preprocessing_parameters(PreprocessingService.PERPLEXITY_MIN)
        reset_select_boxes()
        preprocess_raw_text()
        st.session_state["success_flag"] = True
