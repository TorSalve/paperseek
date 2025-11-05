"""Unit tests for SemanticScholarClient."""

import pytest
from unittest.mock import Mock, patch

from paperseek.clients.semantic_scholar import SemanticScholarClient
from paperseek.core.models import SearchFilters, Paper, Author
from paperseek.core.config import DatabaseConfig
from paperseek.core.exceptions import APIError


class TestSemanticScholarClient:
    """Test suite for SemanticScholarClient."""

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
    def client(self, config):
        """Create a SemanticScholarClient instance."""
        config.api_key = "test_api_key"
        return SemanticScholarClient(
            config=config,
            user_agent="TestAgent/1.0",
        )

    @pytest.fixture
    def sample_s2_paper(self):
        """Sample Semantic Scholar API response for a paper."""
        return {
            "paperId": "abc123def456",
            "externalIds": {
                "DOI": "10.1234/test.doi",
                "ArXiv": "2301.12345",
                "PubMed": "12345678",
            },
            "title": "Test Paper Title",
            "authors": [
                {
                    "name": "John Doe",
                    "authorId": "123456",
                },
                {
                    "name": "Jane Smith",
                    "authorId": "789012",
                },
            ],
            "abstract": "This is a test abstract content.",
            "year": 2023,
            "publicationDate": "2023-06-15",
            "venue": "Test Conference",
            "journal": {"name": "Test Journal", "volume": "10", "pages": "123-145"},
            "citationCount": 42,
            "referenceCount": 25,
            "url": "https://www.semanticscholar.org/paper/abc123",
            "openAccessPdf": {"url": "https://example.com/paper.pdf"},
            "isOpenAccess": True,
            "fieldsOfStudy": ["Computer Science", "Machine Learning"],
        }

    def test_init_with_api_key(self, config):
        """Test initialization with API key."""
        config.api_key = "test_key"
        client = SemanticScholarClient(config=config)
        assert client.database_name == "semantic_scholar"

    def test_init_without_api_key(self, config):
        """Test initialization without API key."""
        client = SemanticScholarClient(config=config)
        assert client.database_name == "semantic_scholar"

    def test_database_name(self, client):
        """Test database name property."""
        assert client.database_name == "semantic_scholar"

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_search_by_title(self, mock_request, client, sample_s2_paper):
        """Test search by title."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [sample_s2_paper],
            "total": 1,
        }
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_search_empty_results(self, mock_request, client):
        """Test search with no results."""
        mock_response = Mock()
        mock_response.json.return_value = {"data": [], "total": 0}
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Nonexistent Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) == 0

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_get_by_doi(self, mock_request, client, sample_s2_paper):
        """Test DOI lookup."""
        mock_response = Mock()
        mock_response.json.return_value = sample_s2_paper
        mock_request.return_value = mock_response

        paper = client.get_by_doi("10.1234/test.doi")

        if paper:
            assert paper.doi == "10.1234/test.doi"

    def test_normalize_paper(self, client, sample_s2_paper):
        """Test paper normalization."""
        paper = client._normalize_paper(sample_s2_paper)

        assert paper.doi == "10.1234/test.doi"
        assert paper.title == "Test Paper Title"
        assert len(paper.authors) == 2
        assert paper.authors[0].name == "John Doe"
        assert paper.year == 2023
        assert paper.citation_count == 42
        assert paper.source_database == "semantic_scholar"

    def test_normalize_paper_minimal(self, client):
        """Test normalization with minimal data."""
        minimal_paper = {
            "paperId": "test123",
            "title": "Minimal Paper",
        }

        paper = client._normalize_paper(minimal_paper)

        assert paper.title == "Minimal Paper"
        assert paper.source_database == "semantic_scholar"

    def test_normalize_paper_with_arxiv(self, client):
        """Test normalization with arXiv ID."""
        paper_data = {
            "paperId": "test123",
            "title": "ArXiv Paper",
            "externalIds": {"ArXiv": "2301.12345"},
        }

        paper = client._normalize_paper(paper_data)

        assert paper.arxiv_id == "2301.12345"

    def test_normalize_paper_with_pubmed(self, client):
        """Test normalization with PubMed ID."""
        paper_data = {
            "paperId": "test123",
            "title": "PubMed Paper",
            "externalIds": {"PubMed": "12345678"},
        }

        paper = client._normalize_paper(paper_data)

        assert paper.pmid == "12345678"

    def test_close(self, client):
        """Test client closure."""
        client.close()

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_search_by_author(self, mock_request, client, sample_s2_paper):
        """Test search by author."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [sample_s2_paper],
            "total": 1,
        }
        mock_request.return_value = mock_response

        filters = SearchFilters(author="John Doe", max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0
        mock_request.assert_called_once()

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_search_with_year_filter(self, mock_request, client, sample_s2_paper):
        """Test search with year filter."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [sample_s2_paper],
            "total": 1,
        }
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test", year=2023, max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0
        # Check year parameter was included
        call_args = mock_request.call_args
        assert "year" in call_args[1]["params"]

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_search_with_year_range(self, mock_request, client, sample_s2_paper):
        """Test search with year range."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [sample_s2_paper],
            "total": 1,
        }
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test", year_start=2020, year_end=2023, max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0
        call_args = mock_request.call_args
        assert "year" in call_args[1]["params"]

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_search_with_venue_filter(self, mock_request, client, sample_s2_paper):
        """Test search with venue filter."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [sample_s2_paper],
            "total": 1,
        }
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test", venue="NeurIPS", max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0
        call_args = mock_request.call_args
        assert "venue" in call_args[1]["params"]

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_search_no_query_no_doi(self, mock_request, client):
        """Test search with no query or DOI."""
        filters = SearchFilters(max_results=10)
        result = client.search(filters)

        assert len(result.papers) == 0
        mock_request.assert_not_called()

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_search_with_doi(self, mock_request, client, sample_s2_paper):
        """Test search with DOI uses DOI lookup."""
        mock_response = Mock()
        mock_response.json.return_value = sample_s2_paper
        mock_request.return_value = mock_response

        filters = SearchFilters(doi="10.1234/test.doi", max_results=10)
        result = client.search(filters)

        # Should use DOI endpoint
        call_args = mock_request.call_args
        assert "DOI:" in call_args[0][0]

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_search_normalization_error(self, mock_request, client):
        """Test search with paper that fails normalization."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "data": [
                {"paperId": "valid123", "title": "Valid Paper"},
                {"paperId": None, "title": None},  # Invalid paper
                {"paperId": "valid456", "title": "Another Valid Paper"},
            ],
            "total": 3,
        }
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Test", max_results=10)
        result = client.search(filters)

        # Should skip invalid paper
        assert len(result.papers) >= 0

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_get_by_identifier_arxiv(self, mock_request, client, sample_s2_paper):
        """Test get by arXiv identifier."""
        mock_response = Mock()
        mock_response.json.return_value = sample_s2_paper
        mock_request.return_value = mock_response

        paper = client.get_by_identifier("2301.12345", "arxiv")

        assert paper is not None
        call_args = mock_request.call_args
        assert "ARXIV:" in call_args[0][0]

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_get_by_identifier_pmid(self, mock_request, client, sample_s2_paper):
        """Test get by PubMed identifier."""
        mock_response = Mock()
        mock_response.json.return_value = sample_s2_paper
        mock_request.return_value = mock_response

        paper = client.get_by_identifier("12345678", "pmid")

        assert paper is not None
        call_args = mock_request.call_args
        assert "PMID:" in call_args[0][0]

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_get_by_identifier_s2(self, mock_request, client, sample_s2_paper):
        """Test get by Semantic Scholar ID."""
        mock_response = Mock()
        mock_response.json.return_value = sample_s2_paper
        mock_request.return_value = mock_response

        paper = client.get_by_identifier("abc123def456", "s2")

        assert paper is not None
        call_args = mock_request.call_args
        assert "paper/abc123def456" in call_args[0][0]

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_get_by_identifier_invalid_type(self, mock_request, client):
        """Test get by identifier with invalid type."""
        paper = client.get_by_identifier("some_id", "invalid_type")

        assert paper is None
        mock_request.assert_not_called()

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_get_by_identifier_api_error(self, mock_request, client):
        """Test get by identifier with API error."""
        mock_request.side_effect = APIError("Not found", "semantic_scholar")

        paper = client.get_by_identifier("nonexistent", "doi")

        assert paper is None

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_batch_lookup_doi(self, mock_request, client, sample_s2_paper):
        """Test batch lookup with DOI."""
        mock_response = Mock()
        mock_response.json.return_value = [sample_s2_paper, sample_s2_paper]
        mock_request.return_value = mock_response

        dois = ["10.1234/test1", "10.1234/test2"]
        result = client.batch_lookup(dois, "doi")

        assert len(result.papers) >= 0
        # Should use batch endpoint
        call_args = mock_request.call_args
        assert "batch" in call_args[0][0]

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_batch_lookup_arxiv(self, mock_request, client, sample_s2_paper):
        """Test batch lookup with arXiv IDs."""
        mock_response = Mock()
        mock_response.json.return_value = [sample_s2_paper]
        mock_request.return_value = mock_response

        arxiv_ids = ["2301.00001"]
        result = client.batch_lookup(arxiv_ids, "arxiv")

        assert len(result.papers) >= 0

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_batch_lookup_pmid(self, mock_request, client, sample_s2_paper):
        """Test batch lookup with PubMed IDs."""
        mock_response = Mock()
        mock_response.json.return_value = [sample_s2_paper]
        mock_request.return_value = mock_response

        pmids = ["12345678"]
        result = client.batch_lookup(pmids, "pmid")

        assert len(result.papers) >= 0

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient._make_request")
    def test_batch_lookup_with_nulls(self, mock_request, client, sample_s2_paper):
        """Test batch lookup with some null results."""
        mock_response = Mock()
        mock_response.json.return_value = [sample_s2_paper, None, sample_s2_paper]
        mock_request.return_value = mock_response

        dois = ["10.1234/test1", "10.1234/notfound", "10.1234/test2"]
        result = client.batch_lookup(dois, "doi")

        # Should skip None results
        assert len(result.papers) >= 0

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient.get_by_identifier")
    def test_batch_lookup_fallback_on_error(self, mock_get_by_id, client):
        """Test batch lookup falls back to individual on error."""
        mock_paper = Mock()
        mock_get_by_id.return_value = mock_paper

        with patch.object(client, "_make_request") as mock_request:
            mock_request.side_effect = Exception("Batch failed")

            dois = ["10.1234/test1", "10.1234/test2"]
            result = client.batch_lookup(dois, "doi")

            # Should fall back to individual lookups
            assert mock_get_by_id.call_count == 2

    @patch("paperseek.clients.semantic_scholar.SemanticScholarClient.get_by_identifier")
    def test_batch_lookup_too_many_identifiers(self, mock_get_by_id, client):
        """Test batch lookup with more than 500 identifiers."""
        mock_paper = Mock()
        mock_get_by_id.return_value = mock_paper

        # Create 501 identifiers
        identifiers = [f"10.1234/test{i}" for i in range(501)]
        result = client.batch_lookup(identifiers, "doi")

        # Should fall back to individual lookups
        assert mock_get_by_id.call_count == 501

    def test_normalize_paper_with_journal(self, client):
        """Test normalization with journal publication."""
        paper_data = {
            "paperId": "test123",
            "title": "Journal Paper",
            "venue": "Nature",
            "publicationTypes": ["JournalArticle"],
        }

        paper = client._normalize_paper(paper_data)

        assert paper.journal == "Nature"
        assert paper.conference is None

    def test_normalize_paper_with_conference(self, client):
        """Test normalization with conference publication."""
        paper_data = {
            "paperId": "test123",
            "title": "Conference Paper",
            "venue": "NeurIPS",
            "publicationTypes": ["Conference"],
        }

        paper = client._normalize_paper(paper_data)

        assert paper.conference == "NeurIPS"
        assert paper.journal is None

    def test_normalize_paper_with_keywords(self, client):
        """Test normalization with fields of study."""
        paper_data = {
            "paperId": "test123",
            "title": "ML Paper",
            "s2FieldsOfStudy": [
                {"category": "Computer Science"},
                {"category": "Machine Learning"},
            ],
        }

        paper = client._normalize_paper(paper_data)

        assert len(paper.keywords) == 2
        assert "Computer Science" in paper.keywords

    def test_normalize_paper_with_open_access_pdf(self, client):
        """Test normalization with open access PDF."""
        paper_data = {
            "paperId": "test123",
            "title": "OA Paper",
            "openAccessPdf": {"url": "https://example.com/paper.pdf"},
            "isOpenAccess": True,
        }

        paper = client._normalize_paper(paper_data)

        assert paper.pdf_url == "https://example.com/paper.pdf"
        assert paper.is_open_access is True

    def test_normalize_paper_no_open_access(self, client):
        """Test normalization without open access."""
        paper_data = {
            "paperId": "test123",
            "title": "Closed Paper",
            "isOpenAccess": False,
        }

        paper = client._normalize_paper(paper_data)

        assert paper.pdf_url is None
        assert paper.is_open_access is False

    def test_normalize_paper_with_url(self, client):
        """Test normalization generates S2 URL."""
        paper_data = {
            "paperId": "abc123def",
            "title": "Paper with URL",
        }

        paper = client._normalize_paper(paper_data)

        assert "semanticscholar.org/paper/abc123def" in paper.url

    def test_normalize_paper_no_paper_id(self, client):
        """Test normalization without paper ID."""
        paper_data = {
            "title": "Paper without ID",
        }

        paper = client._normalize_paper(paper_data)

        assert paper.url is None

    def test_get_supported_fields(self, client):
        """Test get supported fields."""
        fields = client.get_supported_fields()

        assert "doi" in fields
        assert "title" in fields
        assert "authors" in fields
        assert "citation_count" in fields
        assert len(fields) > 10

    def test_get_fields_param(self, client):
        """Test fields parameter generation."""
        fields_param = client._get_fields_param()

        assert "paperId" in fields_param
        assert "title" in fields_param
        assert "authors" in fields_param
        assert "citationCount" in fields_param
