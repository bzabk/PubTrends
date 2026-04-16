import pytest

from src.app.front_model_utils import validate_chosen_file
from src.exceptions.front_model_exceptions import (
    NotEnoughPmidsInTxtFileException,
    PmidTxtFileIsNoneException,
)


@pytest.mark.unit
def test_validate_chosen_file_raises_when_file_is_none(min_len_pmid_list):
    with pytest.raises(PmidTxtFileIsNoneException):
        validate_chosen_file(None, min_len_pmid_list)


@pytest.mark.unit
def test_validate_chosen_file_raises_when_valid_pmids_are_below_minimum(
    too_short_uploaded_pmid_file,
    min_len_pmid_list,
):
    with pytest.raises(NotEnoughPmidsInTxtFileException):
        validate_chosen_file(too_short_uploaded_pmid_file, min_len_pmid_list)


@pytest.mark.unit
def test_validate_chosen_file_returns_unique_pmids_from_valid_file(
    valid_uploaded_pmid_file,
    min_len_pmid_list,
    expected_valid_pmids,
):
    result = validate_chosen_file(valid_uploaded_pmid_file, min_len_pmid_list)
    assert set(result) == set(expected_valid_pmids)


@pytest.mark.unit
def test_validate_chosen_file_duplicated_pmid_reduced_to_unique(
    duplicated_pmids_file,
    unique_pmids_from_duplicated,
    min_len_pmid_list,
):
    result = validate_chosen_file(duplicated_pmids_file, min_len_pmid_list)
    assert set(result) == set(unique_pmids_from_duplicated)


@pytest.mark.unit
def test_validate_chosen_file_raises_when_file_contains_only_invalid_lines(
    only_invalid_uploaded_pmid_file,
    min_len_pmid_list,
):
    with pytest.raises(NotEnoughPmidsInTxtFileException):
        validate_chosen_file(only_invalid_uploaded_pmid_file, min_len_pmid_list)
