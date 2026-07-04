import pytest

from src.api_client.dtos import DatasetLinkDto, OverallDesignDto
from src.api_client.parsers import (
    parse_dataset_summaries,
    parse_overall_design,
    parse_pmids_to_dbidx,
)
from src.exceptions.api_client_exceptions import ParserError


@pytest.mark.unit
def test_parse_pmids_to_dbidx_single_link_success(
    single_link_json,
    single_link_pmid,
    expected_single_link_dto,
):
    result = parse_pmids_to_dbidx(
        response_result=single_link_json,
        pmids=[single_link_pmid],
    )

    assert result == [expected_single_link_dto]


@pytest.mark.unit
def test_parse_pmids_to_dbidx_multi_link_success(
    multi_links_json,
    multi_link_pmid,
    expected_multi_link_dto,
):
    result = parse_pmids_to_dbidx(
        response_result=multi_links_json,
        pmids=[multi_link_pmid],
    )

    assert result == [expected_multi_link_dto]


@pytest.mark.unit
def test_parse_pmids_to_dbidx_preserves_input_order():
    response = {
        "linksets": [
            {
                "dbfrom": "pubmed",
                "ids": ["222"],
                "linksetdbs": [{"dbto": "gds", "linkname": "pubmed_gds", "links": ["2"]}],
            },
            {
                "dbfrom": "pubmed",
                "ids": ["111"],
                "linksetdbs": [{"dbto": "gds", "linkname": "pubmed_gds", "links": ["1"]}],
            },
        ]
    }

    result = parse_pmids_to_dbidx(response_result=response, pmids=["111", "222"])

    assert result == [
        DatasetLinkDto(pmid="111", db_idx=["1"]),
        DatasetLinkDto(pmid="222", db_idx=["2"]),
    ]


@pytest.mark.unit
def test_parse_pmids_to_dbidx_returns_empty_db_idx_when_no_datasets():
    response = {"linksets": [{"dbfrom": "pubmed", "ids": ["12345"]}]}

    result = parse_pmids_to_dbidx(response_result=response, pmids=["12345"])

    assert result == [DatasetLinkDto(pmid="12345", db_idx=[])]


@pytest.mark.unit
def test_parse_pmids_to_dbidx_returns_empty_db_idx_for_pmid_missing_from_response():
    result = parse_pmids_to_dbidx(response_result={"linksets": []}, pmids=["12345"])

    assert result == [DatasetLinkDto(pmid="12345", db_idx=[])]


@pytest.mark.unit
def test_parse_pmids_to_dbidx_returns_none_when_linksets_key_missing():
    result = parse_pmids_to_dbidx(response_result={}, pmids=["12345"])

    assert result is None


@pytest.mark.unit
def test_parse_dataset_summaries_success(
    esummary_json,
    dataset_summary_db_idx,
    expected_dataset_summary_dto,
):
    result = parse_dataset_summaries(
        response_result=esummary_json,
        db_ids=[dataset_summary_db_idx],
    )

    assert result == [expected_dataset_summary_dto]


@pytest.mark.unit
def test_parse_dataset_summaries_skips_ids_missing_from_response(
    esummary_json,
    dataset_summary_db_idx,
    expected_dataset_summary_dto,
):
    result = parse_dataset_summaries(
        response_result=esummary_json,
        db_ids=[dataset_summary_db_idx, "999999999"],
    )

    assert result == [expected_dataset_summary_dto]


@pytest.mark.unit
def test_parse_dataset_summaries_skips_items_with_missing_fields():
    response = {"result": {"200145669": {"title": "title1"}}}

    result = parse_dataset_summaries(response_result=response, db_ids=["200145669"])

    assert result == []


@pytest.mark.unit
def test_parse_dataset_summaries_raises_when_result_key_missing():
    with pytest.raises(ParserError):
        parse_dataset_summaries(response_result={}, db_ids=["200145669"])


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


@pytest.mark.unit
def test_parse_overall_design_returns_none_on_malformed_xml():
    result = parse_overall_design(xml_text="<<<not valid xml>>>", gse_code="GSE123")

    assert result == OverallDesignDto(gse_code="GSE123", overall_design=None)


@pytest.mark.unit
def test_parse_overall_design_returns_empty_string_when_overall_design_field_absent():
    xml = "<MINiML><Series><Title>test</Title></Series></MINiML>"
    result = parse_overall_design(xml_text=xml, gse_code="GSE123")

    assert result == OverallDesignDto(gse_code="GSE123", overall_design="")
