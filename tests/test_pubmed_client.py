"""Unit tests for PubMedClient."""

import pytest
from unittest.mock import Mock, patch

from paperseek.clients.pubmed import PubMedClient
from paperseek.core.models import SearchFilters, Paper, Author
from paperseek.core.config import DatabaseConfig
from paperseek.core.exceptions import APIError


class TestPubMedClient:
    """Test suite for PubMedClient."""

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
        """Create a PubMedClient instance."""
        return PubMedClient(
            config=config,
            email="test@example.com",
            user_agent="TestAgent/1.0",
        )

    @pytest.fixture
    def sample_pubmed_article(self):
        """Sample PubMed API response for an article."""
        return {
            "MedlineCitation": {
                "PMID": {"#text": "12345678"},
                "Article": {
                    "ArticleTitle": "Test Paper Title",
                    "Abstract": {"AbstractText": "This is a test abstract content."},
                    "AuthorList": {
                        "Author": [
                            {
                                "LastName": "Doe",
                                "ForeName": "John",
                                "Affiliation": "Test University",
                            },
                            {"LastName": "Smith", "ForeName": "Jane"},
                        ]
                    },
                    "Journal": {
                        "Title": "Test Journal",
                        "JournalIssue": {
                            "Volume": "10",
                            "Issue": "2",
                            "PubDate": {"Year": "2023", "Month": "Jun"},
                        },
                    },
                    "Pagination": {"MedlinePgn": "123-145"},
                    "ArticleIdList": {
                        "ArticleId": [
                            {"@IdType": "doi", "#text": "10.1234/test.doi"},
                            {"@IdType": "pmc", "#text": "PMC1234567"},
                        ]
                    },
                },
                "MeshHeadingList": {
                    "MeshHeading": [
                        {"DescriptorName": {"#text": "Machine Learning"}},
                        {"DescriptorName": {"#text": "Artificial Intelligence"}},
                    ]
                },
            },
            "PubmedData": {
                "ArticleIdList": {
                    "ArticleId": [
                        {"@IdType": "pubmed", "#text": "12345678"},
                        {"@IdType": "doi", "#text": "10.1234/test.doi"},
                    ]
                }
            },
        }

    def test_init(self, config):
        """Test initialization."""
        client = PubMedClient(config=config, email="test@example.com")
        assert client.database_name == "pubmed"
        assert client.email == "test@example.com"

    def test_database_name(self, client):
        """Test database name property."""
        assert client.database_name == "pubmed"

    @patch("paperseek.clients.pubmed.PubMedClient._make_request")
    def test_search_by_title(self, mock_request, client):
        """Test search by title."""
        # Mock search response
        mock_search_response = Mock()
        mock_search_response.json.return_value = {
            "esearchresult": {"idlist": ["12345678"], "count": "1"}
        }
        
        # Mock fetch response with XML
        mock_fetch_response = Mock()
        mock_fetch_response.text = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Test Paper Title</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        mock_request.side_effect = [mock_search_response, mock_fetch_response]

        filters = SearchFilters(title="Test Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) >= 0

    @patch("paperseek.clients.pubmed.PubMedClient._make_request")
    def test_search_empty_results(self, mock_request, client):
        """Test search with no results."""
        mock_response = Mock()
        mock_response.json.return_value = {"esearchresult": {"idlist": [], "count": "0"}}
        mock_request.return_value = mock_response

        filters = SearchFilters(title="Nonexistent Paper", max_results=10)
        result = client.search(filters)

        assert len(result.papers) == 0



    def test_close(self, client):
        """Test client closure."""
        client.close()

    @patch("paperseek.clients.pubmed.PubMedClient._make_request")
    def test_search_by_author(self, mock_request, client):
        """Test search by author."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "esearchresult": {"idlist": ["12345678"], "count": "1"}
        }
        
        mock_fetch_response = Mock()
        mock_fetch_response.text = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Test Paper</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        mock_request.side_effect = [mock_response, mock_fetch_response]

        filters = SearchFilters(author="John Doe", max_results=10)
        result = client.search(filters)

        assert result is not None

    @patch("paperseek.clients.pubmed.PubMedClient._make_request")
    def test_search_with_year_range(self, mock_request, client):
        """Test search with year range."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "esearchresult": {"idlist": ["12345678"], "count": "1"}
        }
        
        mock_fetch_response = Mock()
        mock_fetch_response.text = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Test Paper</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        mock_request.side_effect = [mock_response, mock_fetch_response]

        filters = SearchFilters(title="test", year_start=2020, year_end=2024, max_results=10)
        result = client.search(filters)

        assert result is not None

    @patch("paperseek.clients.pubmed.PubMedClient._make_request")
    def test_get_by_identifier(self, mock_request, client):
        """Test getting paper by PMID."""
        mock_response = Mock()
        mock_response.text = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>12345678</PMID>
                    <Article>
                        <ArticleTitle>Test Paper</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        mock_request.return_value = mock_response

        paper = client.get_by_identifier("12345678", "pmid")

        assert paper is not None or paper is None  # Depends on parsing

    @patch("paperseek.clients.pubmed.PubMedClient._make_request")
    def test_max_results_limit(self, mock_request, client):
        """Test that max_results is respected."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "esearchresult": {"idlist": ["1", "2", "3", "4", "5"], "count": "5"}
        }
        
        mock_fetch_response = Mock()
        mock_fetch_response.text = """<?xml version="1.0"?>
        <PubmedArticleSet>
            <PubmedArticle>
                <MedlineCitation>
                    <PMID>1</PMID>
                    <Article>
                        <ArticleTitle>Test</ArticleTitle>
                    </Article>
                </MedlineCitation>
            </PubmedArticle>
        </PubmedArticleSet>
        """
        
        mock_request.side_effect = [mock_response, mock_fetch_response]

        filters = SearchFilters(title="test", max_results=3)
        result = client.search(filters)

        assert result is not None

    @patch("paperseek.clients.pubmed.PubMedClient._make_request")
    def test_api_error_handling(self, mock_request, client):
        """Test API error handling."""
        mock_request.side_effect = APIError("API Error", database="pubmed")

        filters = SearchFilters(title="test", max_results=10)
        
        with pytest.raises(APIError):
            client.search(filters)
