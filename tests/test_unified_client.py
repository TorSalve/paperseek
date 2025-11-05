"""Unit tests for the UnifiedSearchClient."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from paperseek import UnifiedSearchClient
from paperseek.core.models import SearchFilters, SearchResult, Paper, Author
from paperseek.core.config import AcademicSearchConfig, DatabaseConfig
from paperseek.core.exceptions import SearchError, ConfigurationError


class TestUnifiedSearchClient:
    """Test suite for UnifiedSearchClient."""

    def test_init_with_default_config(self):
        """Test initialization with default configuration."""
        with patch("paperseek.core.unified_client.load_config") as mock_load:
            mock_config = AcademicSearchConfig()
            mock_config.crossref.enabled = True
            mock_config.openalex.enabled = True
            mock_load.return_value = mock_config

            client = UnifiedSearchClient()

            assert client.config is not None
            mock_load.assert_called_once()

    def test_init_with_custom_databases(self):
        """Test initialization with specific databases."""
        config_dict = {
            "email": "test@example.com",
            "crossref": {"enabled": True, "rate_limit_per_second": 1.0},
            "openalex": {"enabled": True, "rate_limit_per_second": 2.0},
        }

        client = UnifiedSearchClient(databases=["crossref", "openalex"], config_dict=config_dict)

        assert "crossref" in client.clients
        assert "openalex" in client.clients
        assert "semantic_scholar" not in client.clients

    def test_search_basic(self):
        """Test basic search functionality."""
        config_dict = {"crossref": {"enabled": True, "rate_limit_per_second": 1.0}}

        client = UnifiedSearchClient(databases=["crossref"], config_dict=config_dict)

        # Mock the client search method
        mock_result = SearchResult(
            papers=[
                Paper(
                    title="Test Paper",
                    authors=[Author(name="Test Author")],
                    year=2023,
                    source_database="crossref",
                )
            ],
            databases_queried=["crossref"],
        )

        client.clients["crossref"].search = Mock(return_value=mock_result)

        results = client.search(venue="ICML", year=2023, max_results=10)

        assert len(results) == 1
        assert results[0].title == "Test Paper"
        assert "crossref" in results.databases_queried

    def test_search_with_filters(self):
        """Test search with SearchFilters object."""
        config_dict = {"crossref": {"enabled": True, "rate_limit_per_second": 1.0}}

        client = UnifiedSearchClient(databases=["crossref"], config_dict=config_dict)

        filters = SearchFilters(venue="ICML", year=2023, max_results=10)

        mock_result = SearchResult(papers=[], databases_queried=["crossref"])
        client.clients["crossref"].search = Mock(return_value=mock_result)

        results = client.search_with_filters(filters)

        assert isinstance(results, SearchResult)
        client.clients["crossref"].search.assert_called_once()

    def test_get_by_doi(self):
        """Test DOI lookup."""
        config_dict = {"crossref": {"enabled": True, "rate_limit_per_second": 1.0}}

        client = UnifiedSearchClient(databases=["crossref"], config_dict=config_dict)

        mock_paper = Paper(
            title="Test Paper",
            authors=[Author(name="Test Author")],
            doi="10.1234/test",
            year=2023,
            source_database="crossref",
        )

        client.clients["crossref"].get_by_doi = Mock(return_value=mock_paper)

        paper = client.get_by_doi("10.1234/test")

        assert paper is not None
        assert paper.title == "Test Paper"
        assert paper.doi == "10.1234/test"

    def test_batch_lookup(self):
        """Test batch lookup functionality."""
        config_dict = {"crossref": {"enabled": True, "rate_limit_per_second": 1.0}}

        client = UnifiedSearchClient(databases=["crossref"], config_dict=config_dict)

        dois = ["10.1234/test1", "10.1234/test2"]

        mock_result = SearchResult(
            papers=[
                Paper(
                    title="Paper 1", authors=[], doi=dois[0], year=2023, source_database="crossref"
                ),
                Paper(
                    title="Paper 2", authors=[], doi=dois[1], year=2023, source_database="crossref"
                ),
            ],
            databases_queried=["crossref"],
        )

        client.clients["crossref"].batch_lookup = Mock(return_value=mock_result)

        results = client.batch_lookup(dois, id_type="doi")

        assert len(results) == 2
        assert results[0].doi == dois[0]
        assert results[1].doi == dois[1]

    def test_parallel_search_mode(self):
        """Test parallel search mode."""
        config_dict = {
            "crossref": {"enabled": True, "rate_limit_per_second": 1.0},
            "openalex": {"enabled": True, "rate_limit_per_second": 2.0},
        }

        client = UnifiedSearchClient(
            databases=["crossref", "openalex"], fallback_mode="parallel", config_dict=config_dict
        )

        # Mock results from both databases
        mock_result1 = SearchResult(
            papers=[Paper(title="Paper 1", authors=[], year=2023, source_database="crossref")],
            databases_queried=["crossref"],
        )

        mock_result2 = SearchResult(
            papers=[Paper(title="Paper 2", authors=[], year=2023, source_database="openalex")],
            databases_queried=["openalex"],
        )

        client.clients["crossref"].search = Mock(return_value=mock_result1)
        client.clients["openalex"].search = Mock(return_value=mock_result2)

        results = client.search(venue="ICML", year=2023)

        # Should get results from both databases
        assert len(results) >= 2
        assert len(results.databases_queried) == 2

    def test_context_manager(self):
        """Test context manager functionality."""
        config_dict = {"crossref": {"enabled": True, "rate_limit_per_second": 1.0}}

        with UnifiedSearchClient(config_dict=config_dict) as client:
            assert client is not None
            assert "crossref" in client.clients

        # Client should be closed after exiting context

    def test_invalid_fallback_mode(self):
        """Test initialization with invalid fallback mode."""
        config_dict = {"fallback_mode": "invalid_mode", "crossref": {"enabled": True}}

        # Pydantic will raise ValidationError, not ConfigurationError
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            client = UnifiedSearchClient(config_dict=config_dict)
            filters = SearchFilters(venue="ICML", year=2023)
            client.search_with_filters(filters)

    def test_no_enabled_databases(self):
        """Test behavior when no databases are enabled."""
        config_dict = {
            "crossref": {"enabled": False},
            "openalex": {"enabled": False},
            "semantic_scholar": {"enabled": False},
            "doi": {"enabled": False},
        }

        # Client can be created with no databases enabled (will just return empty results)
        client = UnifiedSearchClient(config_dict=config_dict)
        assert client is not None


class TestSearchResult:
    """Test suite for SearchResult model."""

    def test_field_statistics(self):
        """Test field statistics calculation."""
        papers = [
            Paper(
                title="Paper 1",
                authors=[Author(name="Author 1")],
                abstract="Abstract 1",
                year=2023,
                doi="10.1234/1",
                source_database="test",
            ),
            Paper(
                title="Paper 2",
                authors=[Author(name="Author 2")],
                abstract=None,  # Missing abstract
                year=2023,
                doi="10.1234/2",
                source_database="test",
            ),
        ]

        result = SearchResult(papers=papers)
        stats = result.field_statistics()

        assert "abstract" in stats
        assert stats["abstract"].available_count == 1
        assert stats["abstract"].total_count == 2
        assert stats["abstract"].percentage == 50.0

    def test_filter_by_required_fields(self):
        """Test filtering by required fields."""
        papers = [
            Paper(
                title="Paper 1",
                authors=[],
                abstract="Abstract",
                doi="10.1234/1",
                year=2023,
                source_database="test",
            ),
            Paper(
                title="Paper 2",
                authors=[],
                abstract=None,  # Missing abstract
                doi="10.1234/2",
                year=2023,
                source_database="test",
            ),
        ]

        result = SearchResult(papers=papers)
        filtered = result.filter_by_required_fields(["abstract", "doi"])

        assert len(filtered) == 1
        assert filtered[0].title == "Paper 1"

    def test_export_methods_exist(self):
        """Test that export methods are available."""
        result = SearchResult(papers=[])

        assert hasattr(result, "to_csv")
        assert hasattr(result, "to_json")
        assert hasattr(result, "to_jsonl")
        assert hasattr(result, "to_bibtex")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
