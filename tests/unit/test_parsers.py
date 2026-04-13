import pytest

from src.api_client.parsers import (
    parse_dataset_summary,
    parse_overall_design,
    parse_pmid_to_dbidx,
)


@pytest.mark.unit
def test_parse_pmid_to_dbidx_single_link_success(
    single_link_json,
    single_link_pmid,
    expected_single_link_dto,
):
    result = parse_pmid_to_dbidx(
        response_result=single_link_json,
        pmid=single_link_pmid,
    )

    assert result == expected_single_link_dto


@pytest.mark.unit
def test_parse_pmid_to_dbidx_multi_link_success(
    multi_links_json,
    multi_link_pmid,
    expected_multi_link_dto,
):
    result = parse_pmid_to_dbidx(
        response_result=multi_links_json,
        pmid=multi_link_pmid,
    )

    assert result == expected_multi_link_dto


@pytest.mark.unit
def test_parse_dataset_summary_success(
    esummary_json,
    dataset_summary_db_idx,
    expected_dataset_summary_dto,
):
    result = parse_dataset_summary(
        response_result=esummary_json,
        db_idx=dataset_summary_db_idx,
    )

    assert result == expected_dataset_summary_dto


@pytest.mark.unit
def test_parse_overall_design_success(
    overall_design_xml,
    overall_design_gse_code,
    expected_overall_design_dto,
):
    result = parse_overall_design(
        xml_text=overall_design_xml,
        gse_code=overall_design_gse_code,
    )

    assert result == expected_overall_design_dto
