"""Unit tests for BaseDatabaseClient."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from paperseek.core.base import DatabaseClient
from paperseek.core.models import SearchFilters, SearchResult, Paper
from paperseek.core.config import DatabaseConfig
from paperseek.core.exceptions import (
    APIError,
    RateLimitError,
    AuthenticationError,
    TimeoutError as PaperseekTimeoutError,
)


class TestBaseDatabaseClient:
    """Test suite for BaseDatabaseClient."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return DatabaseConfig(
            enabled=True,
            rate_limit_per_second=1.0,
            timeout=30,
            max_retries=3,
        )

    @pytest.fixture
    def mock_client(self, config):
        """Create a mock client implementation."""
        class MockClient(DatabaseClient):
            @property
            def database_name(self) -> str:
                return "mock_db"

            def search(self, filters: SearchFilters) -> SearchResult:
                return SearchResult(
                    query_info={"filters": filters.model_dump()},
                    databases_queried=[self.database_name],
                )
            
            def get_by_doi(self, doi: str):
                return None
            
            def get_by_identifier(self, identifier: str, id_type: str):
                return None
            
            def batch_lookup(self, identifiers, id_type: str):
                return SearchResult(
                    query_info={},
                    databases_queried=[self.database_name],
                )
            
            def _normalize_paper(self, raw_data):
                return Paper(
                    doi="test",
                    title="Test",
                    authors=[],
                    source_database=self.database_name,
                )

        return MockClient(config=config)

    def test_init(self, mock_client):
        """Test client initialization."""
        assert mock_client.config is not None
        assert mock_client.database_name == "mock_db"

    def test_context_manager(self, mock_client):
        """Test context manager protocol."""
        with mock_client as client:
            assert client is not None
            assert hasattr(client, 'session')

    def test_close(self, mock_client):
        """Test client closure - with SessionPool, session is not closed."""
        mock_client.session = Mock()
        mock_client.close()
        # With SessionPool integration, close() doesn't actually close the session
        # as it's shared. So we just verify close() doesn't raise an error.
        assert mock_client.session is not None

    @patch('requests.Session.request')
    def test_make_request_success(self, mock_request, mock_client):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": "test"}
        mock_request.return_value = mock_response

        response = mock_client._make_request("https://api.test.com/endpoint")
        
        assert response.status_code == 200
        mock_request.assert_called_once()

    @patch('requests.Session.request')
    def test_make_request_with_params(self, mock_request, mock_client):
        """Test request with query parameters."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response

        params = {"query": "test", "limit": 10}
        mock_client._make_request("https://api.test.com", params=params)

        mock_request.assert_called_once()
        call_kwargs = mock_request.call_args[1]
        assert call_kwargs['params'] == params

    @patch('requests.Session.request')
    def test_make_request_404_error(self, mock_request, mock_client):
        """Test handling of 404 errors."""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.ok = False
        mock_response.text = "Not Found"
        mock_request.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            mock_client._make_request("https://api.test.com")
        
        assert "404" in str(exc_info.value)

    @patch('requests.Session.request')
    def test_make_request_429_rate_limit(self, mock_request, mock_client):
        """Test handling of rate limit errors (429)."""
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.ok = False
        mock_response.headers = {"Retry-After": "60"}
        mock_request.return_value = mock_response

        with pytest.raises(RateLimitError) as exc_info:
            mock_client._make_request("https://api.test.com")
        
        assert exc_info.value.retry_after == 60

    @patch('requests.Session.request')
    def test_make_request_401_auth_error(self, mock_request, mock_client):
        """Test handling of authentication errors (401)."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.ok = False
        mock_response.text = "Unauthorized"
        mock_request.return_value = mock_response

        with pytest.raises(AuthenticationError):
            mock_client._make_request("https://api.test.com")

    @patch('requests.Session.request')
    def test_make_request_403_forbidden(self, mock_request, mock_client):
        """Test handling of forbidden errors (403)."""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_response.ok = False
        mock_response.text = "Forbidden"
        mock_request.return_value = mock_response

        with pytest.raises(AuthenticationError):
            mock_client._make_request("https://api.test.com")

    @patch('requests.Session.request')
    def test_make_request_500_server_error(self, mock_request, mock_client):
        """Test handling of server errors (500)."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.ok = False
        mock_response.text = "Internal Server Error"
        mock_request.return_value = mock_response

        with pytest.raises(APIError) as exc_info:
            mock_client._make_request("https://api.test.com")
        
        assert "500" in str(exc_info.value)

    @patch('requests.Session.request')
    def test_make_request_timeout(self, mock_request, mock_client):
        """Test handling of timeout errors."""
        mock_request.side_effect = requests.exceptions.Timeout()

        with pytest.raises(PaperseekTimeoutError) as exc_info:
            mock_client._make_request("https://api.test.com")
        
        assert "timed out" in str(exc_info.value).lower()

    @patch('requests.Session.request')
    def test_make_request_connection_error(self, mock_request, mock_client):
        """Test handling of connection errors."""
        mock_request.side_effect = requests.exceptions.ConnectionError()

        with pytest.raises(APIError):
            mock_client._make_request("https://api.test.com")

    def test_get_by_doi_not_implemented(self, mock_client):
        """Test that get_by_doi returns None by default."""
        result = mock_client.get_by_doi("10.1234/test")
        assert result is None

    def test_batch_lookup_not_implemented(self, mock_client):
        """Test that batch_lookup returns empty result by default."""
        result = mock_client.batch_lookup(["id1", "id2"], "doi")
        assert isinstance(result, SearchResult)
        assert len(result.papers) == 0
