import pandas as pd
import pytest
from pandas.testing import assert_frame_equal

from src.api_client.api_dataframe_mapper import ApiDataFrameMapper
from src.api_client.dtos import CachedDatasetRecord, DatasetSummaryDto, OverallDesignDto


@pytest.fixture
def sample_records() -> list[CachedDatasetRecord]:
    return [
        CachedDatasetRecord(
            pmid="11111111",
            db_idx="2222222",
            title="title_one",
            summary="summary_one",
            organism="organism_one",
            experiment_type="experiment_type_one",
            gse_code="gse_code_one",
            overall_design="overall_design_one",
        ),
        CachedDatasetRecord(
            pmid="33333333",
            db_idx="4444444",
            title="title_two",
            summary="summary_two",
            organism="organism_two",
            experiment_type="experiment_type_two",
            gse_code="gse_code_two",
            overall_design="overall_design_two",
        ),
    ]


@pytest.mark.unit
def test_create_dataframe_from_single_pmid_merges_summaries_with_matching_designs():
    summaries = [
        DatasetSummaryDto(
            db_idx="2222222",
            title="title_one",
            summary="summary_one",
            organism="organism_one",
            experiment_type="experiment_type_one",
            gse_code="gse_code_one",
        ),
        DatasetSummaryDto(
            db_idx="3333333",
            title="title_two",
            summary="summary_two",
            organism="organism_two",
            experiment_type="experiment_type_two",
            gse_code="gse_code_two",
        ),
    ]
    overall_designs = [
        OverallDesignDto(
            gse_code="gse_code_one",
            overall_design="overall_design_one",
        ),
        OverallDesignDto(
            gse_code="gse_code_two",
            overall_design="overall_design_two",
        ),
    ]

    result = ApiDataFrameMapper.create_dataframe_from_single_pmid(
        pmid="11111111",
        summaries=summaries,
        overall_designs=overall_designs,
    )

    expected = pd.DataFrame(
        [
            {
                "Pmid": "11111111",
                "db_idx": "2222222",
                "Title": "title_one",
                "Summary": "summary_one",
                "Organism": "organism_one",
                "Experiment_type": "experiment_type_one",
                "GSE_code": "gse_code_one",
                "Overall_design": "overall_design_one",
            },
            {
                "Pmid": "11111111",
                "db_idx": "3333333",
                "Title": "title_two",
                "Summary": "summary_two",
                "Organism": "organism_two",
                "Experiment_type": "experiment_type_two",
                "GSE_code": "gse_code_two",
                "Overall_design": "overall_design_two",
            },
        ],
        columns=ApiDataFrameMapper.dataframe_columns(),
    )

    assert_frame_equal(result, expected)

@pytest.mark.unit
def test_combine_dataframes_ignores_empty_inputs_and_preserves_row_order():
    first = pd.DataFrame(
        [
            {
                "Pmid": "11111111",
                "db_idx": "2222222",
                "Title": "title_one",
                "Summary": "summary_one",
                "Organism": "organism_one",
                "Experiment_type": "experiment_type_one",
                "GSE_code": "gse_code_one",
                "Overall_design": "overall_design_one",
            }
        ],
        columns=ApiDataFrameMapper.dataframe_columns(),
    )
    second = pd.DataFrame(
        [
            {
                "Pmid": "22222222",
                "db_idx": "4444444",
                "Title": "title_two",
                "Summary": "summary_two",
                "Organism": "organism_two",
                "Experiment_type": "experiment_type_two",
                "GSE_code": "gse_code_two",
                "Overall_design": "overall_design_two",
            }
        ],
        columns=ApiDataFrameMapper.dataframe_columns(),
    )

    result = ApiDataFrameMapper.combine_dataframes([None, pd.DataFrame(), first, second])

    expected = pd.concat([first, second], axis=0, ignore_index=True)

    assert_frame_equal(result, expected)


@pytest.mark.unit
def test_records_to_dataframe_and_back_preserves_record_values(
    sample_records: list[CachedDatasetRecord],
):
    expected_dataframe = pd.DataFrame(
        [
            {
                "Pmid": "11111111",
                "db_idx": "2222222",
                "Title": "title_one",
                "Summary": "summary_one",
                "Organism": "organism_one",
                "Experiment_type": "experiment_type_one",
                "GSE_code": "gse_code_one",
                "Overall_design": "overall_design_one",
            },
            {
                "Pmid": "33333333",
                "db_idx": "4444444",
                "Title": "title_two",
                "Summary": "summary_two",
                "Organism": "organism_two",
                "Experiment_type": "experiment_type_two",
                "GSE_code": "gse_code_two",
                "Overall_design": "overall_design_two",
            },
        ],
        columns=ApiDataFrameMapper.dataframe_columns(),
    )

    dataframe = ApiDataFrameMapper.records_to_dataframe(sample_records)
    restored_records = ApiDataFrameMapper.dataframe_to_records(dataframe)

    assert_frame_equal(dataframe, expected_dataframe)
    assert restored_records == sample_records
