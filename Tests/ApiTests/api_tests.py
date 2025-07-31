import pytest
from unittest.mock import mock_open, patch
from src.ApiClient.apiclient_utils import load_pmids_from_file

@pytest.mark.parametrize("mock_data, expected", [
    ("", []),
    ("123\n456\n789\n", [123, 456, 789]),
    ("123\nabc\n456\n!@#\n789\n", [123, 456, 789]),
    ("123\n456\n123\n789\n456\n", [123, 456, 789]),
])
def test_load_pmids_from_file(mock_data, expected):
    with patch("builtins.open", mock_open(read_data=mock_data)):
        assert sorted(load_pmids_from_file()) == expected