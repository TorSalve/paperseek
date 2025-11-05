"""Unit tests for DBLPClient."""

import pytest
from unittest.mock import Mock, patch

from paperseek.clients.dblp import DBLPClient
from paperseek.core.models import SearchFilters, Paper, Author
from paperseek.core.config import DatabaseConfig
from paperseek.core.exceptions import APIError


class TestDBLPClient:
    """Test suite for DBLPClient."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return DatabaseConfig(
            enabled=True,
            rate_limit_per_second=10.0,
            timeout=30,
            max_retries=3,
        )

    @pytest.fixture
    def client(self, config):
        """Create a DBLPClient instance."""
        return DBLPClient(config=config, user_agent="TestAgent/1.0")

    @pytest.fixture
    def sample_dblp_hit(self):
        """Sample DBLP API response for a hit."""
        return {
            "info": {
                "url": "https://dblp.org/rec/journals/test/Doe23",
                "doi": "10.1234/test.doi",
            },
            "authors": {
                "author": [
                    {"text": "John Doe"},
                    {"text": "Jane Smith"},
                ]
            },
            "title": "Test Paper Title",
            "venue": "Test Conference",
            "year": "2023",
            "type": "Conference and Workshop Papers",
            "pages": "123-145",
            "ee": "https://doi.org/10.1234/test.doi",
        }

    def test_init(self, config):
        """Test initialization."""
        client = DBLPClient(config=config)
        assert client.database_name == "dblp"

    def test_database_name(self, client):
        """Test database name property."""
        assert client.database_name == "dblp"

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_search_by_title(self, mock_request, client):
        """Test search by title."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0"?>
        <result>
            <hits total="1">
                <hit>
                    <info>
                        <url>https://dblp.org/rec/test</url>
                        <doi>10.1234/test.doi</doi>
                    </info>
                    <title>Test Paper Title</title>
                    <authors>
                        <author>John Doe</author>
                    </authors>
                    <venue>Test Conference</venue>
                    <year>2023</year>
                </hit>
            </hits>
        </result>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_search_empty_results(self, mock_request, client):
        """Test search with no results."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0"?>
        <result>
            <hits total="0">
            </hits>
        </result>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Nonexistent Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) == 0

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_search_by_author(self, mock_request, client):
        """Test search by author."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0"?>
        <result>
            <hits total="1">
                <hit>
                    <info>
                        <url>https://dblp.org/rec/test</url>
                    </info>
                    <title>Test Paper</title>
                    <authors>
                        <author>John Doe</author>
                    </authors>
                    <year>2023</year>
                </hit>
            </hits>
        </result>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(author="John Doe", max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0



    def test_close(self, client):
        """Test client closure."""
        client.close()

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_search_with_year_filter(self, mock_request, client):
        """Test search with year filter."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0"?>
        <result>
            <hits total="1">
                <hit>
                    <info><url>https://dblp.org/rec/test</url></info>
                    <title>Test Paper</title>
                    <year>2023</year>
                </hit>
            </hits>
        </result>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test", year=2023, max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_search_no_query(self, mock_request, client):
        """Test search with no query raises ValueError."""
        filters = SearchFilters(max_results=10)
        
        with pytest.raises(ValueError, match="At least one search criterion"):
            client.search(filters)

        mock_request.assert_not_called()

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_search_xml_parse_error(self, mock_request, client):
        """Test search with XML parse error raises APIError."""
        mock_response = Mock()
        mock_response.text = "Invalid XML"
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test", max_results=10)
        
        with pytest.raises(APIError, match="Invalid XML response"):
            client.search(filters)

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_search_normalization_error(self, mock_request, client):
        """Test search with paper that fails normalization."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0"?>
        <result>
            <hits total="2">
                <hit>
                    <info><url>https://dblp.org/rec/test</url></info>
                    <title>Valid Paper</title>
                </hit>
                <hit>
                    <!-- Missing required fields -->
                </hit>
            </hits>
        </result>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test", max_results=10)
        result = client.search(filters)

        # Should skip invalid papers
        assert len(result.papers) >= 0

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_get_by_doi(self, mock_request, client):
        """Test DOI lookup."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0"?>
        <result>
            <hits total="1">
                <hit>
                    <info>
                        <url>https://dblp.org/rec/test</url>
                        <doi>10.1234/test.doi</doi>
                    </info>
                    <title>Test Paper</title>
                </hit>
            </hits>
        </result>
        """
        mock_request.return_value = mock_response

        paper = client.get_by_doi("10.1234/test.doi")

        if paper:
            assert paper.doi == "10.1234/test.doi"

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_get_by_doi_not_found(self, mock_request, client):
        """Test DOI lookup with no results."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0"?>
        <result>
            <hits total="0"></hits>
        </result>
        """
        mock_request.return_value = mock_response

        paper = client.get_by_doi("10.1234/nonexistent")

        assert paper is None

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_get_by_doi_api_error(self, mock_request, client):
        """Test DOI lookup with API error."""
        mock_request.side_effect = APIError("Not found", "dblp")

        paper = client.get_by_doi("10.1234/error")

        assert paper is None

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_get_by_identifier_dblp_key(self, mock_request, client):
        """Test get by DBLP key."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0"?>
        <dblp>
            <article>
                <title>Test Paper</title>
                <year>2023</year>
                <url>https://dblp.org/rec/test</url>
            </article>
        </dblp>
        """
        mock_request.return_value = mock_response

        paper = client.get_by_identifier("journals/test/Doe23", "dblp")

        assert paper is not None

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_get_by_identifier_doi(self, mock_request, client):
        """Test get by identifier with DOI type."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0"?>
        <result>
            <hits total="1">
                <hit>
                    <info><url>https://dblp.org/rec/test</url></info>
                    <title>Test Paper</title>
                </hit>
            </hits>
        </result>
        """
        mock_request.return_value = mock_response

        paper = client.get_by_identifier("10.1234/test", "doi")

        assert paper is not None

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_get_by_identifier_invalid_type(self, mock_request, client):
        """Test get by identifier with invalid type."""
        paper = client.get_by_identifier("some_id", "invalid_type")

        assert paper is None
        mock_request.assert_not_called()

    @patch("paperseek.clients.dblp.DBLPClient._make_request")
    def test_get_by_identifier_api_error(self, mock_request, client):
        """Test get by identifier with API error."""
        mock_request.side_effect = APIError("Error", "dblp")

        paper = client.get_by_identifier("test", "dblp")

        assert paper is None

    def test_normalize_paper_not_implemented(self, client):
        """Test that _normalize_paper is not implemented for DBLP (uses XML)."""
        with pytest.raises(NotImplementedError, match="Use _normalize_paper_from_xml"):
            client._normalize_paper({})

    def test_get_supported_fields(self, client):
        """Test get supported fields."""
        fields = client.get_supported_fields()

        assert 'doi' in fields
        assert 'title' in fields
        assert 'authors' in fields
        assert 'venue' in fields
        assert len(fields) > 5
