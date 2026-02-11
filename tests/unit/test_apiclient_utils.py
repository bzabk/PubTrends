import pytest
import pandas as pd
from unittest.mock import patch, mock_open
from src.ApiClient.apiclient_utils import (
    create_pmid_to_db_idx_df,
    create_db_idx_to_info_df,
    create_gse_to_overall_design_df,
    combine_all_data_frames,
    stack_data_frames,
    load_pmids_from_file,
)


class TestPmDataDataclass:
    def test_pmdata_creation(self, sample_pmdata):
        assert sample_pmdata.Title == "Sample Title"
        assert sample_pmdata.Summary == "This is a sample summary"
        assert sample_pmdata.Organism == "Homo sapiens"
        assert sample_pmdata.Experiment_type == "Expression profiling"
        assert sample_pmdata.GSE_code == "GSE123456"


class TestCreatePmidToDbIdxDf:
    def test_single_pmid_multiple_db_idx(self):
        db_idx_list = [1, 2, 3, 4, 5]
        df = create_pmid_to_db_idx_df(12345, db_idx_list)
        assert len(df) == 5
        assert all(df["Pmid"] == 12345)
        assert list(df["db_idx"]) == db_idx_list

    def test_empty_db_idx_list(self):
        df = create_pmid_to_db_idx_df(12345, [])
        assert len(df) == 0


class TestCreateDbIdxToInfoDf:
    def test_multiple_pmdata(self, sample_pmdata):
        db_idx_list = [1, 2, 3]
        pmdata_list = [sample_pmdata, sample_pmdata, sample_pmdata]
        df = create_db_idx_to_info_df(db_idx_list, pmdata_list)
        assert len(df) == 3
        assert list(df["db_idx"]) == [1, 2, 3]
        assert all(df["Title"] == "Sample Title")


class TestCreateGseToOverallDesignDf:
    def test_multiple_gse(self):
        gse_list = ["GSE001", "GSE002", "GSE003"]
        design_list = ["Design 1", "Design 2", "Design 3"]
        df = create_gse_to_overall_design_df(gse_list, design_list)
        assert len(df) == 3
        assert list(df["GSE_code"]) == gse_list
        assert list(df["Overall_design"]) == design_list


class TestCombineAllDataFrames:
    def test_missing_data_handling(self):
        df_db = pd.DataFrame({"Pmid": [123], "db_idx": [1]})
        df_info = pd.DataFrame({"db_idx": [1], "Title": ["Title"], "GSE_code": ["GSE999"]})
        df_design = pd.DataFrame({"GSE_code": ["GSE001"], "Overall_design": ["Design"]})
        result = combine_all_data_frames(df_db, df_info, df_design)
        assert len(result) == 1
        assert pd.isna(result.iloc[0]["Overall_design"])


class TestStackDataFrames:
    def test_stack_with_none_values(self):
        df1 = pd.DataFrame({"A": [1, 2]})
        df2 = None
        df3 = pd.DataFrame({"A": [3, 4]})
        result = stack_data_frames([df1, df2, df3])
        assert len(result) == 4
        assert list(result["A"]) == [1, 2, 3, 4]


class TestLoadPmidsFromFile:
    @pytest.mark.parametrize(
        "mock_data, expected",
        [
            ("", []),
            ("123\n456\n789\n", [123, 456, 789]),
            ("123\nabc\n456\n!@#\n789\n", [123, 456, 789]),
            ("123\n456\n123\n789\n456\n", [123, 456, 789]),
        ],
    )
    def test_load_pmids_various_inputs(self, mock_data, expected):
        with patch("builtins.open", mock_open(read_data=mock_data)):
            result = load_pmids_from_file()
            assert sorted(result) == sorted(expected)
