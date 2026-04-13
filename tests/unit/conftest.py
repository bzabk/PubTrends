import json
from io import BytesIO
from pathlib import Path

import pytest

from src.api_client.dtos import DatasetLinkDto, DatasetSummaryDto, OverallDesignDto


FIXTURES_DIR = Path(__file__).resolve().parents[1]/"fixtures"


def _load_json_fixture(filename: str) -> dict:
    with (FIXTURES_DIR/filename).open() as fixture_file:
        return json.load(fixture_file)


def _load_text_fixture(filename: str) -> str:
    return (FIXTURES_DIR / filename).read_text()


class FakeUploadedFile(BytesIO):
    def __init__(self, content: str, name: str = "pmids.txt"):
        super().__init__(content.encode("utf-8"))
        self.name = name


def _load_uploaded_text_fixture(filename: str) -> FakeUploadedFile:
    return FakeUploadedFile(_load_text_fixture(filename), name=filename)


@pytest.fixture
def single_link_pmid() -> str:
    return "33309739"


@pytest.fixture
def multi_link_pmid() -> str:
    return "33763704"


@pytest.fixture
def dataset_summary_db_idx() -> str:
    return "200145669"


@pytest.fixture
def overall_design_gse_code() -> str:
    return "GSE145669"


@pytest.fixture
def single_link_json() -> dict:
    return _load_json_fixture("single_link.json")


@pytest.fixture
def multi_links_json() -> dict:
    return _load_json_fixture("multi_links.json")


@pytest.fixture
def esummary_json() -> dict:
    return _load_json_fixture("esummary.json")


@pytest.fixture
def overall_design_xml() -> str:
    return _load_text_fixture("GSE145669.xml")


@pytest.fixture
def expected_single_link_dto(single_link_pmid: str) -> DatasetLinkDto:
    return DatasetLinkDto(
        pmid=single_link_pmid,
        db_ids=["200146264"],
    )


@pytest.fixture
def expected_multi_link_dto(multi_link_pmid: str) -> DatasetLinkDto:
    return DatasetLinkDto(
        pmid=multi_link_pmid,
        db_ids=[
            "200165870",
            "200145669",
            "200145668",
            "200145531",
        ],
    )


@pytest.fixture
def expected_dataset_summary_dto(dataset_summary_db_idx: str) -> DatasetSummaryDto:
    return DatasetSummaryDto(
        db_idx=dataset_summary_db_idx,
        title="test_title",
        summary="test_summary",
        organism="test_organism",
        experiment_type="test_experiment_type",
        gse_code="test_gse_code",
    )


@pytest.fixture
def expected_overall_design_dto(overall_design_gse_code: str) -> OverallDesignDto:
    return OverallDesignDto(
        gse_code=overall_design_gse_code,
        overall_design="test_overall_design",
    )



@pytest.fixture
def min_len_pmid_list() -> int:
    return 10

@pytest.fixture
def empty_uploaded_pmid_file() -> FakeUploadedFile:
    return _load_uploaded_text_fixture("pmids_empty.txt")

@pytest.fixture
def too_short_uploaded_pmid_file() -> FakeUploadedFile:
    return _load_uploaded_text_fixture("pmids_not_enough.txt")

@pytest.fixture
def valid_uploaded_pmid_file() -> FakeUploadedFile:
    return _load_uploaded_text_fixture("pmids_valid.txt")

@pytest.fixture
def duplicated_pmids_file() -> FakeUploadedFile:
    return _load_uploaded_text_fixture("pmids_valid_duplicated.txt")

@pytest.fixture
def only_invalid_uploaded_pmid_file() -> FakeUploadedFile:
    return _load_uploaded_text_fixture("pmids_with_no_numeric_signs.txt")


@pytest.fixture
def expected_valid_pmids() -> list[int]:
    return [
        11111,
        22222,
        33333,
        44444,
        55555,
        66666,
        77777,
        88888,
        99999,
        00000,
        12121,
        13131,
        14141,
    ]

@pytest.fixture
def unique_pmids_from_duplicated() -> list[int]:
    return [
        11111111,
        22222222,
        33333333,
        44444444,
        55555555,
        66666666,
        77777777,
        88888888,
        99999999,
        00000000,
        67676767,
        18989899,
    ]
