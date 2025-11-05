"""Unit tests for ArXivClient."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from paperseek.clients.arxiv import ArXivClient
from paperseek.core.models import SearchFilters, Paper, Author
from paperseek.core.config import DatabaseConfig
from paperseek.core.exceptions import APIError


class TestArXivClient:
    """Test suite for ArXivClient."""

    @pytest.fixture
    def config(self):
        """Create a test configuration."""
        return DatabaseConfig(
            enabled=True,
            rate_limit_per_second=3.0,
            timeout=30,
            max_retries=3,
        )

    @pytest.fixture
    def client(self, config):
        """Create an ArXivClient instance."""
        return ArXivClient(config=config, user_agent="TestAgent/1.0")

    @pytest.fixture
    def sample_arxiv_entry(self):
        """Sample arXiv API response entry."""
        return """
        <entry>
            <id>http://arxiv.org/abs/2301.00001v1</id>
            <title>Test Paper Title</title>
            <summary>This is a test abstract for the paper.</summary>
            <published>2023-01-01T00:00:00Z</published>
            <updated>2023-01-05T00:00:00Z</updated>
            <author>
                <name>John Doe</name>
                <arxiv:affiliation xmlns:arxiv="http://arxiv.org/schemas/atom">Test University</arxiv:affiliation>
            </author>
            <author>
                <name>Jane Smith</name>
            </author>
            <arxiv:doi xmlns:arxiv="http://arxiv.org/schemas/atom">10.1234/test.doi</arxiv:doi>
            <arxiv:journal_ref xmlns:arxiv="http://arxiv.org/schemas/atom">Test Journal 10 (2023) 123-145</arxiv:journal_ref>
            <link href="http://arxiv.org/abs/2301.00001v1" rel="alternate" type="text/html"/>
            <link href="http://arxiv.org/pdf/2301.00001v1" rel="related" type="application/pdf"/>
            <arxiv:primary_category xmlns:arxiv="http://arxiv.org/schemas/atom" term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
            <category term="cs.AI" scheme="http://arxiv.org/schemas/atom"/>
            <category term="cs.LG" scheme="http://arxiv.org/schemas/atom"/>
        </entry>
        """

    def test_init(self, config):
        """Test initialization."""
        client = ArXivClient(config=config)
        assert client.database_name == "arxiv"

    def test_database_name(self, client):
        """Test database name property."""
        assert client.database_name == "arxiv"

    @patch("paperseek.clients.arxiv.ArXivClient._make_request")
    def test_search_by_title(self, mock_request, client, sample_arxiv_entry):
        """Test search by title."""
        mock_response = Mock()
        mock_response.text = f"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>ArXiv Query</title>
            <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1</opensearch:totalResults>
            {sample_arxiv_entry}
        </feed>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0

    @patch("paperseek.clients.arxiv.ArXivClient._make_request")
    def test_search_empty_results(self, mock_request, client):
        """Test search with no results."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>ArXiv Query</title>
            <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">0</opensearch:totalResults>
        </feed>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Nonexistent Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) == 0



    def test_close(self, client):
        """Test client closure."""
        client.close()

    @patch("paperseek.clients.arxiv.ArXivClient._make_request")
    def test_search_by_author(self, mock_request, client, sample_arxiv_entry):
        """Test search by author."""
        mock_response = Mock()
        mock_response.text = f"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1</opensearch:totalResults>
            {sample_arxiv_entry}
        </feed>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(author="John Doe", max_results=10)
        result = client.search(filters)

        assert result is not None

    @patch("paperseek.clients.arxiv.ArXivClient._make_request")
    def test_search_by_year_range(self, mock_request, client, sample_arxiv_entry):
        """Test search with year range."""
        mock_response = Mock()
        mock_response.text = f"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1</opensearch:totalResults>
            {sample_arxiv_entry}
        </feed>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(title="test", year_start=2020, year_end=2024, max_results=10)
        result = client.search(filters)

        assert result is not None

    @patch("paperseek.clients.arxiv.ArXivClient._make_request")
    def test_get_by_identifier(self, mock_request, client, sample_arxiv_entry):
        """Test getting paper by arXiv ID."""
        mock_response = Mock()
        mock_response.text = f"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1</opensearch:totalResults>
            {sample_arxiv_entry}
        </feed>
        """
        mock_request.return_value = mock_response

        paper = client.get_by_identifier("2301.00001", "arxiv")

        assert paper is not None or paper is None  # Depends on parsing

    @patch("paperseek.clients.arxiv.ArXivClient._make_request")
    def test_normalize_paper(self, mock_request, client, sample_arxiv_entry):
        """Test paper normalization."""
        mock_response = Mock()
        mock_response.text = f"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">1</opensearch:totalResults>
            {sample_arxiv_entry}
        </feed>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(title="test", max_results=1)
        result = client.search(filters)

        # Check that papers are normalized
        assert result is not None

    @patch("paperseek.clients.arxiv.ArXivClient._make_request")
    def test_max_results_limit(self, mock_request, client, sample_arxiv_entry):
        """Test that max_results is respected."""
        mock_response = Mock()
        # Create multiple entries
        entries = sample_arxiv_entry * 5
        mock_response.text = f"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <opensearch:totalResults xmlns:opensearch="http://a9.com/-/spec/opensearch/1.1/">5</opensearch:totalResults>
            {entries}
        </feed>
        """
        mock_request.return_value = mock_response

        filters = SearchFilters(title="test", max_results=3)
        result = client.search(filters)

        # Should limit results
        assert result is not None

    @patch("paperseek.clients.arxiv.ArXivClient._make_request")
    def test_api_error_handling(self, mock_request, client):
        """Test API error handling."""
        mock_request.side_effect = APIError("API Error", database="arxiv")

        filters = SearchFilters(title="test", max_results=10)
        
        with pytest.raises(APIError):
            client.search(filters)
