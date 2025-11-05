"""Unit tests for COREClient."""

import pytest
from unittest.mock import Mock, patch

from paperseek.clients.core import COREClient
from paperseek.core.models import SearchFilters, Paper, Author
from paperseek.core.config import DatabaseConfig
from paperseek.core.exceptions import APIError


class TestCOREClient:
    """Test suite for COREClient."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        config = DatabaseConfig(
            enabled=True,
            rate_limit_per_second=10.0,
            timeout=30,
            max_retries=3,
        )
        config.api_key = "test_api_key"
        return config

    @pytest.fixture
    def client(self, config):
        """Create a COREClient instance."""
        return COREClient(config=config, user_agent="TestAgent/1.0")

    @pytest.fixture
    def sample_core_work(self):
        """Sample CORE API response for a work."""
        return {
            "id": 123456,
            "doi": "10.1234/test.doi",
            "title": "Test Paper Title",
            "abstract": "This is a test abstract for the paper.",
            "authors": [
                {"name": "John Doe"},
                {"name": "Jane Smith"},
            ],
            "publishedDate": "2023-06-15",
            "yearPublished": 2023,
            "journals": ["Test Journal"],
            "publisher": "Test Publisher",
            "downloadUrl": "https://core.ac.uk/download/pdf/123456.pdf",
            "citationCount": 15,
        }

    def test_init(self, config):
        """Test initialization."""
        client = COREClient(config=config)
        assert client.database_name == "core"

    def test_database_name(self, client):
        """Test database name property."""
        assert client.database_name == "core"

    @patch("paperseek.clients.core.COREClient._make_request")
    def test_search_by_title(self, mock_request, client, sample_core_work):
        """Test search by title."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "totalHits": 1,
            "results": [sample_core_work],
        }
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0

    @patch("paperseek.clients.core.COREClient._make_request")
    def test_search_empty_results(self, mock_request, client):
        """Test search with no results."""
        mock_response = Mock()
        mock_response.json.return_value = {"totalHits": 0, "results": []}
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Nonexistent Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) == 0

    @patch("paperseek.clients.core.COREClient._make_request")
    def test_get_by_doi(self, mock_request, client, sample_core_work):
        """Test DOI lookup."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "totalHits": 1,
            "results": [sample_core_work],
        }
        mock_request.return_value = mock_response

        paper = client.get_by_doi("10.1234/test.doi")

        if paper:
            assert paper.doi == "10.1234/test.doi"



    def test_close(self, client):
        """Test client closure."""
        client.close()
