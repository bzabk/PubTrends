import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.ApiClient.apiclient_utils import PmData
from unittest.mock import AsyncMock
import pandas as pd
import pytest


@pytest.fixture
def sample_pmdata():
    return PmData(
        Title="Sample Title",
        Summary="This is a sample summary",
        Organism="Homo sapiens",
        Experiment_type="Expression profiling",
        GSE_code="GSE123456",
    )


@pytest.fixture
def sample_dataframe():
    data = {
        "Pmid": [123, 456, 789],
        "db_idx": [1, 2, 3],
        "Title": ["Title 1", "Title 2", "Title 3"],
        "Summary": ["Summary 1", "Summary 2", "Summary 3"],
        "Organism": ["Human", "Mouse", "Rat"],
        "Experiment_type": ["Expression profiling", "ChIP-seq", "RNA-seq"],
        "GSE_code": ["GSE001", "GSE002", "GSE003"],
        "Overall_design": ["Design 1", "Design 2", "Design 3"],
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_redis_client():
    mock = AsyncMock()
    mock.check_if_exists = AsyncMock(return_value=False)
    mock.sadd = AsyncMock(return_value=1)
    mock.get_dataframe_from_redis = AsyncMock(return_value=[])
    return mock


@pytest.fixture
def mock_aiohttp_response():
    mock = AsyncMock()
    mock.status = 200
    mock.text = AsyncMock(return_value="<xml></xml>")
    mock.json = AsyncMock(return_value={"result": {}})
    return mock


@pytest.fixture
def mock_aiohttp_response_error():
    mock = AsyncMock()
    mock.status = 500
    return mock
