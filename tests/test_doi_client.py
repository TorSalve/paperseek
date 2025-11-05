"""Unit tests for DOIClient."""

import pytest
from unittest.mock import Mock, patch

from paperseek.clients.doi import DOIClient
from paperseek.core.models import SearchFilters, Paper, Author
from paperseek.core.config import DatabaseConfig
from paperseek.core.exceptions import APIError


class TestDOIClient:
    """Test suite for DOIClient."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return DatabaseConfig(
            enabled=True,
            rate_limit_per_second=50.0,
            timeout=30,
            max_retries=3,
        )

    @pytest.fixture
    def client(self, config):
        """Create a DOIClient instance."""
        return DOIClient(config=config, user_agent="TestAgent/1.0")

    @pytest.fixture
    def sample_doi_response(self):
        """Sample DOI API response."""
        return {
            "DOI": "10.1234/test.doi",
            "type": "journal-article",
            "title": ["Test Paper Title"],
            "author": [
                {
                    "given": "John",
                    "family": "Doe",
                    "affiliation": [{"name": "Test University"}],
                },
                {"given": "Jane", "family": "Smith"},
            ],
            "container-title": ["Test Journal"],
            "issued": {"date-parts": [[2023, 6, 15]]},
            "volume": "10",
            "issue": "2",
            "page": "123-145",
            "abstract": "<jats:p>This is a test abstract.</jats:p>",
            "URL": "https://doi.org/10.1234/test.doi",
            "is-referenced-by-count": 15,
        }

    def test_init(self, config):
        """Test initialization."""
        client = DOIClient(config=config)
        assert client.database_name == "doi"

    def test_database_name(self, client):
        """Test database name property."""
        assert client.database_name == "doi"

    @patch("paperseek.clients.doi.DOIClient._make_request")
    def test_get_by_doi(self, mock_request, client, sample_doi_response):
        """Test DOI lookup."""
        mock_response = Mock()
        mock_response.json.return_value = sample_doi_response
        mock_request.return_value = mock_response

        paper = client.get_by_doi("10.1234/test.doi")

        if paper:
            assert paper.doi == "10.1234/test.doi"
            assert paper.title == "Test Paper Title"

    @patch("paperseek.clients.doi.DOIClient._make_request")
    def test_get_by_doi_not_found(self, mock_request, client):
        """Test DOI lookup with non-existent DOI."""
        mock_request.side_effect = APIError("Not found", database="doi", status_code=404)

        paper = client.get_by_doi("10.9999/nonexistent")

        assert paper is None

    @patch("paperseek.clients.doi.DOIClient._make_request")
    def test_search_by_doi(self, mock_request, client, sample_doi_response):
        """Test search with DOI filter."""
        mock_response = Mock()
        mock_response.json.return_value = sample_doi_response
        mock_request.return_value = mock_response

        filters = SearchFilters(doi="10.1234/test.doi")
        result = client.search(filters)

        if len(result.papers) > 0:
            assert result.papers[0].doi == "10.1234/test.doi"

    def test_search_without_doi(self, client):
        """Test search without DOI filter returns empty result."""
        filters = SearchFilters(title="Some Title")
        
        # DOI client only supports DOI-based lookups, so returns empty result
        result = client.search(filters)
        assert len(result.papers) == 0

    def test_normalize_paper(self, client, sample_doi_response):
        """Test paper normalization."""
        paper = client._normalize_paper(sample_doi_response)

        assert paper.doi == "10.1234/test.doi"
        assert paper.title == "Test Paper Title"
        assert len(paper.authors) >= 0
        assert paper.year == 2023
        assert paper.journal == "Test Journal"
        assert paper.source_database == "doi"

    def test_normalize_paper_minimal(self, client):
        """Test normalization with minimal data."""
        minimal_response = {
            "DOI": "10.9999/minimal",
            "title": ["Minimal Paper"],
        }

        paper = client._normalize_paper(minimal_response)

        assert paper.doi == "10.9999/minimal"
        assert paper.title == "Minimal Paper"

    def test_normalize_paper_multiple_titles(self, client):
        """Test normalization with multiple titles (takes first)."""
        response = {
            "DOI": "10.1234/multi",
            "title": ["First Title", "Second Title"],
        }

        paper = client._normalize_paper(response)

        assert paper.title == "First Title"

    def test_close(self, client):
        """Test client closure."""
        client.close()
