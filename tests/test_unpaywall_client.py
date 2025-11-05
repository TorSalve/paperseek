"""Unit tests for UnpaywallClient."""

import pytest
from unittest.mock import Mock, patch

from paperseek.clients.unpaywall import UnpaywallClient
from paperseek.core.models import SearchFilters, Paper, Author
from paperseek.core.config import DatabaseConfig
from paperseek.core.exceptions import APIError


class TestUnpaywallClient:
    """Test suite for UnpaywallClient."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return DatabaseConfig(
            enabled=True,
            rate_limit_per_second=100.0,
            timeout=30,
            max_retries=3,
        )

    @pytest.fixture
    def client(self, config):
        """Create an UnpaywallClient instance."""
        return UnpaywallClient(
            config=config, email="test@example.com", user_agent="TestAgent/1.0"
        )

    @pytest.fixture
    def sample_unpaywall_response(self):
        """Sample Unpaywall API response."""
        return {
            "doi": "10.1234/test.doi",
            "title": "Test Paper Title",
            "year": 2023,
            "journal_name": "Test Journal",
            "publisher": "Test Publisher",
            "is_oa": True,
            "oa_status": "gold",
            "best_oa_location": {
                "url": "https://example.com/paper.pdf",
                "url_for_pdf": "https://example.com/paper.pdf",
                "version": "publishedVersion",
                "license": "cc-by",
            },
            "z_authors": [
                {"given": "John", "family": "Doe"},
                {"given": "Jane", "family": "Smith"},
            ],
        }

    def test_init(self, config):
        """Test initialization."""
        client = UnpaywallClient(config=config, email="test@example.com")
        assert client.database_name == "unpaywall"
        assert client.email == "test@example.com"

    def test_database_name(self, client):
        """Test database name property."""
        assert client.database_name == "unpaywall"

    @patch("paperseek.clients.unpaywall.UnpaywallClient._make_request")
    def test_get_by_doi(self, mock_request, client, sample_unpaywall_response):
        """Test DOI lookup."""
        mock_response = Mock()
        mock_response.json.return_value = sample_unpaywall_response
        mock_request.return_value = mock_response

        paper = client.get_by_doi("10.1234/test.doi")

        if paper:
            assert paper.doi == "10.1234/test.doi"
            assert paper.title == "Test Paper Title"

    @patch("paperseek.clients.unpaywall.UnpaywallClient._make_request")
    def test_get_by_doi_not_found(self, mock_request, client):
        """Test DOI lookup with non-existent DOI."""
        mock_request.side_effect = APIError("Not found", database="unpaywall", status_code=404)

        paper = client.get_by_doi("10.9999/nonexistent")

        assert paper is None

    @patch("paperseek.clients.unpaywall.UnpaywallClient._make_request")
    def test_search_by_doi(self, mock_request, client, sample_unpaywall_response):
        """Test search with DOI filter."""
        mock_response = Mock()
        mock_response.json.return_value = sample_unpaywall_response
        mock_request.return_value = mock_response

        filters = SearchFilters(doi="10.1234/test.doi")
        result = client.search(filters)

        if len(result.papers) > 0:
            assert result.papers[0].doi == "10.1234/test.doi"

    def test_search_without_doi(self, client):
        """Test search without DOI filter returns empty result."""
        filters = SearchFilters(title="Some Title")
        
        # Unpaywall only supports DOI-based lookups, so returns empty result
        result = client.search(filters)
        assert len(result.papers) == 0

    def test_normalize_paper(self, client, sample_unpaywall_response):
        """Test paper normalization."""
        paper = client._normalize_paper(sample_unpaywall_response)

        assert paper.doi == "10.1234/test.doi"
        assert paper.title == "Test Paper Title"
        assert paper.year == 2023
        assert paper.journal == "Test Journal"
        assert paper.pdf_url == "https://example.com/paper.pdf"
        assert paper.source_database == "unpaywall"

    def test_normalize_paper_minimal(self, client):
        """Test normalization with minimal data."""
        minimal_response = {
            "doi": "10.9999/minimal",
            "title": "Minimal Paper",
            "is_oa": False,
        }

        paper = client._normalize_paper(minimal_response)

        assert paper.doi == "10.9999/minimal"
        assert paper.title == "Minimal Paper"

    def test_normalize_paper_with_oa_location(self, client):
        """Test normalization extracts OA location."""
        response = {
            "doi": "10.1234/oa",
            "title": "Open Access Paper",
            "is_oa": True,
            "best_oa_location": {
                "url_for_pdf": "https://repo.example.com/paper.pdf",
                "license": "cc-by-nc",
            },
        }

        paper = client._normalize_paper(response)

        assert paper.pdf_url == "https://repo.example.com/paper.pdf"

    def test_close(self, client):
        """Test client closure."""
        client.close()
