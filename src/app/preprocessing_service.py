import streamlit as st

from exceptions.front_model_exceptions import NotEnoughPmidsInTxtFileException, PmidTxtFileIsNoneException
from src.app.front_model_utils import (
    preprocess_raw_text,
    reset_select_boxes,
    validate_user_preprocessing_parameters,
)


class PreprocessingService:
    PERPLEXITY_MIN = 30

    def validate_chosen_file(self, uploaded_file, min_len_pmid_list=10) -> list[str] | None:
        """
        Function checks whether the uploaded file is in the correct format and extracts PMIDs from it.
        In case user uploaded less than 10 correct PMIDs, an error message is displayed.
        If txt file contains less than 10 PMIDs, the error message is displayed.

        :param uploaded_file: The file uploaded by the user.

        :return list[int]: A list of unique PMIDs extracted from the file.
        """
        if uploaded_file is None:
            raise PmidTxtFileIsNoneException
        file_content = uploaded_file.read().decode("utf-8")
        list_of_pmids = []
        pmids = file_content.split("\n")
        for line in pmids:
            line = line.replace(" ", "").strip()
            if line.isdigit():
                list_of_pmids.append(str(line))
        list_of_pmids = list(set(list_of_pmids))
        if len(list_of_pmids) < min_len_pmid_list:
            raise NotEnoughPmidsInTxtFileException
        st.session_state["pmid_list"] = list_of_pmids

    def process_dataframe_from_session_cache(self):
        validate_user_preprocessing_parameters(PreprocessingService.PERPLEXITY_MIN)
        reset_select_boxes()
        preprocess_raw_text()
        st.session_state["success_flag"] = True
