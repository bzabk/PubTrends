import pytest
from unittest.mock import AsyncMock, patch
from src.ApiClient.apiclient import ApiClient
from src.Exceptions.api_client_exceptions import ResponseStatusException


@pytest.fixture
def api_client(mock_redis_client):
    client = ApiClient(redis_client=mock_redis_client)
    client.api_key = "test_api_key"
    return client


class TestApiClientInitialization:
    def test_initialization(self, mock_redis_client):
        client = ApiClient(redis_client=mock_redis_client)
        assert client.session is None
        assert client.semaphore is not None
        assert client.failed_pmid_list == []
        assert client.redis_client is mock_redis_client

    def test_semaphore_size(self, mock_redis_client):
        client = ApiClient(redis_client=mock_redis_client)
        assert client.semaphore._value == ApiClient._SEMAPHORE_SIZE


class TestCheckApiAvailability:
    @pytest.mark.asyncio
    async def test_check_api_availability_failure(self, api_client):
        mock_response1 = AsyncMock()
        mock_response1.status = 500
        mock_response2 = AsyncMock()
        mock_response2.status = 200
        mock_response3 = AsyncMock()
        mock_response3.status = 200
        with patch("aiohttp.ClientSession.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = [mock_response1, mock_response2, mock_response3]
            with pytest.raises(ResponseStatusException):
                await api_client.check_api_availability(with_api_key=False)


class TestReduceUserPmidList:
    @pytest.mark.asyncio
    async def test_reduce_pmid_list_partial_cached(self, api_client):
        api_client.redis_client.check_if_exists = AsyncMock(side_effect=[True, False, True])
        pmid_list = [123, 456, 789]
        result = await api_client.reduce_user_pmid_list_with_cached_data(pmid_list)
        assert result == [456]


class TestIsDataInCache:
    @pytest.mark.asyncio
    async def test_is_data_in_cache_exists(self, api_client):
        api_client.redis_client.check_if_exists = AsyncMock(return_value=True)
        result = await api_client.is_data_in_cache(123)
        assert result is None

    @pytest.mark.asyncio
    async def test_is_data_in_cache_not_exists(self, api_client):
        api_client.redis_client.check_if_exists = AsyncMock(return_value=False)
        result = await api_client.is_data_in_cache(123)
        assert result == 123


class TestApiClientConstants:
    def test_retrieval_times_constant(self):
        assert ApiClient._RETRIEVAL_TIMES == 3

    def test_semaphore_size_constant(self):
        assert ApiClient._SEMAPHORE_SIZE == 10

    def test_api_urls_are_valid(self):
        assert "ncbi.nlm.nih.gov" in ApiClient._BASE_URL_OVERALL_DESIGN
        assert "ncbi.nlm.nih.gov" in ApiClient._BASE_URL_DB_IDX
        assert "ncbi.nlm.nih.gov" in ApiClient._BASE_URL_SUMMARY
