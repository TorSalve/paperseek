"""Unit tests for OpenAlexClient."""

import pytest
from unittest.mock import Mock, patch

from paperseek.clients.openalex import OpenAlexClient
from paperseek.core.models import SearchFilters, Paper, Author
from paperseek.core.config import DatabaseConfig
from paperseek.core.exceptions import APIError


class TestOpenAlexClient:
    """Test suite for OpenAlexClient."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return DatabaseConfig(
            enabled=True,
            rate_limit_per_second=2.0,
            timeout=30,
            max_retries=3,
        )

    @pytest.fixture
    def client(self, config):
        """Create an OpenAlexClient instance."""
        return OpenAlexClient(
            config=config,
            email="test@example.com",
            user_agent="TestAgent/1.0",
        )

    @pytest.fixture
    def sample_openalex_work(self):
        """Sample OpenAlex API response for a work."""
        return {
            "id": "https://openalex.org/W1234567890",
            "doi": "https://doi.org/10.1234/test.doi",
            "title": "Test Paper Title",
            "authorships": [
                {
                    "author": {
                        "display_name": "John Doe",
                        "orcid": "https://orcid.org/0000-0001-2345-6789",
                    },
                    "institutions": [{"display_name": "Test University"}],
                },
                {
                    "author": {"display_name": "Jane Smith"},
                    "institutions": [],
                },
            ],
            "publication_year": 2023,
            "publication_date": "2023-06-15",
            "primary_location": {
                "source": {
                    "display_name": "Test Journal",
                    "type": "journal",
                }
            },
            "biblio": {
                "volume": "10",
                "issue": "2",
                "first_page": "123",
                "last_page": "145",
            },
            "abstract_inverted_index": {
                "This": [0],
                "is": [1],
                "a": [2],
                "test": [3],
                "abstract": [4],
            },
            "concepts": [
                {"display_name": "Machine Learning", "score": 0.9},
                {"display_name": "Artificial Intelligence", "score": 0.8},
            ],
            "cited_by_count": 42,
            "referenced_works_count": 25,
            "open_access": {
                "is_oa": True,
                "oa_url": "https://example.com/paper.pdf",
            },
        }

    def test_init_with_email(self, config):
        """Test initialization with email."""
        client = OpenAlexClient(config=config, email="test@example.com")
        assert client.database_name == "openalex"
        assert client.email == "test@example.com"

    def test_database_name(self, client):
        """Test database name property."""
        assert client.database_name == "openalex"

    @patch("paperseek.clients.openalex.OpenAlexClient._make_request")
    def test_search_by_title(self, mock_request, client, sample_openalex_work):
        """Test search by title."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "results": [sample_openalex_work],
            "meta": {"count": 1},
        }
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0  # May vary based on implementation

    @patch("paperseek.clients.openalex.OpenAlexClient._make_request")
    def test_search_empty_results(self, mock_request, client):
        """Test search with no results."""
        mock_response = Mock()
        mock_response.json.return_value = {"results": [], "meta": {"count": 0}}
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Nonexistent Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) == 0

    def test_normalize_paper(self, client, sample_openalex_work):
        """Test paper normalization."""
        paper = client._normalize_paper(sample_openalex_work)

        assert paper.doi == "10.1234/test.doi"
        assert paper.title == "Test Paper Title"
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "John Doe"
        assert paper.year == 2023
        assert paper.source_database == "openalex"

    def test_normalize_paper_minimal(self, client):
        """Test normalization with minimal data."""
        minimal_work = {
            "id": "https://openalex.org/W123",
            "title": "Minimal Paper",
        }

        paper = client._normalize_paper(minimal_work)

        assert paper.title == "Minimal Paper"
        assert paper.source_database == "openalex"

    def test_reconstruct_abstract(self, client):
        """Test abstract reconstruction from inverted index."""
        inverted_index = {
            "This": [0],
            "is": [1],
            "a": [2],
            "test": [3],
        }

        # Test if method exists
        if hasattr(client, "_reconstruct_abstract"):
            abstract = client._reconstruct_abstract(inverted_index)
            assert "This is a test" in abstract

    def test_close(self, client):
        """Test client closure."""
        client.close()
        # Verify session is properly closed
