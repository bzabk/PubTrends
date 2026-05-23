import pytest

from src.api_client.dtos import OverallDesignDto
from src.api_client.parsers import (
    parse_dataset_summary,
    parse_overall_design,
    parse_pmid_to_dbidx,
)
from src.exceptions.api_client_exceptions import ParserError


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




@pytest.mark.unit
def test_parse_pmid_to_dbidx_raises_on_empty_response():
    with pytest.raises(ParserError):
        parse_pmid_to_dbidx(response_result={}, pmid="12345")


@pytest.mark.unit
def test_parse_pmid_to_dbidx_raises_on_empty_linksets():
    with pytest.raises(ParserError):
        parse_pmid_to_dbidx(response_result={"linksets": []}, pmid="12345")


@pytest.mark.unit
def test_parse_pmid_to_dbidx_raises_when_linksetdbs_missing():
    with pytest.raises(ParserError):
        parse_pmid_to_dbidx(
            response_result={"linksets": [{"dbfrom": "pubmed", "ids": ["12345"]}]},
            pmid="12345",
        )


@pytest.mark.unit
def test_parse_pmid_to_dbidx_raises_when_linksetdbs_empty():
    with pytest.raises(ParserError):
        parse_pmid_to_dbidx(
            response_result={"linksets": [{"linksetdbs": []}]},
            pmid="12345",
        )


@pytest.mark.unit
def test_parse_pmid_to_dbidx_error_contains_pmid():
    pmid = "99999"
    with pytest.raises(ParserError, match=pmid):
        parse_pmid_to_dbidx(response_result={}, pmid=pmid)



@pytest.mark.unit
def test_parse_dataset_summary_raises_on_empty_response():
    with pytest.raises(ParserError):
        parse_dataset_summary(response_result={}, db_idx="200145669")


@pytest.mark.unit
def test_parse_dataset_summary_raises_when_db_idx_missing():
    with pytest.raises(ParserError):
        parse_dataset_summary(
            response_result={"result": {"uids": ["200145669"]}},
            db_idx="200145669",
        )


@pytest.mark.unit
def test_parse_dataset_summary_raises_when_required_field_missing():
    with pytest.raises(ParserError):
        parse_dataset_summary(
            response_result={"result": {"200145669": {"title": "test title"}}},
            db_idx="200145669",
        )


@pytest.mark.unit
def test_parse_dataset_summary_error_contains_db_idx():
    db_idx = "200145669"
    with pytest.raises(ParserError, match=db_idx):
        parse_dataset_summary(response_result={}, db_idx=db_idx)



@pytest.mark.unit
def test_parse_overall_design_raises_on_malformed_xml():
    with pytest.raises(ParserError):
        parse_overall_design(xml_text="<<<not valid xml>>>", gse_code="GSE123")


@pytest.mark.unit
def test_parse_overall_design_raises_when_miniml_key_missing():
    with pytest.raises(ParserError):
        parse_overall_design(
            xml_text="<Root><Series><Overall-Design>test</Overall-Design></Series></Root>",
            gse_code="GSE123",
        )


@pytest.mark.unit
def test_parse_overall_design_raises_when_series_key_missing():
    with pytest.raises(ParserError):
        parse_overall_design(
            xml_text="<MINiML><NoSeries/></MINiML>",
            gse_code="GSE123",
        )


@pytest.mark.unit
def test_parse_overall_design_returns_none_when_overall_design_field_absent():
    xml = "<MINiML><Series><Title>test</Title></Series></MINiML>"
    result = parse_overall_design(xml_text=xml, gse_code="GSE123")
    assert result == OverallDesignDto(gse_code="GSE123", overall_design=None)


@pytest.mark.unit
def test_parse_overall_design_error_contains_gse_code():
    gse_code = "GSE99999"
    with pytest.raises(ParserError, match=gse_code):
        parse_overall_design(xml_text="<<<invalid>>>", gse_code=gse_code)
