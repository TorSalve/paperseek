"""Unit tests for core models."""

import pytest
from datetime import datetime

from paperseek.core.models import (
    Paper,
    Author,
    SearchResult,
    SearchFilters,
    FieldStatistics,
)


class TestAuthor:
    """Test suite for Author model."""

    def test_author_creation(self):
        """Test creating an Author instance."""
        author = Author(name="John Doe", affiliation="Test University", orcid="0000-0001-2345-6789")

        assert author.name == "John Doe"
        assert author.affiliation == "Test University"
        assert author.orcid == "0000-0001-2345-6789"

    def test_author_minimal(self):
        """Test creating an Author with only name."""
        author = Author(name="Jane Smith")

        assert author.name == "Jane Smith"
        assert author.affiliation is None
        assert author.orcid is None

    def test_author_str(self):
        """Test string representation of Author."""
        author = Author(name="John Doe")
        assert str(author) == "John Doe"


class TestPaper:
    """Test suite for Paper model."""

    def test_paper_creation(self):
        """Test creating a Paper instance with all fields."""
        paper = Paper(
            doi="10.1234/test.doi",
            title="Test Paper",
            authors=[Author(name="John Doe"), Author(name="Jane Smith")],
            abstract="This is a test abstract.",
            year=2023,
            publication_date="2023-06-15",
            venue="Test Conference",
            journal="Test Journal",
            conference="ICML 2023",
            volume="10",
            issue="2",
            pages="123-145",
            keywords=["machine learning", "AI"],
            citation_count=42,
            reference_count=25,
            url="https://doi.org/10.1234/test.doi",
            pdf_url="https://example.com/paper.pdf",
            is_open_access=True,
            source_database="crossref",
            source_id="crossref:123",
        )

        assert paper.doi == "10.1234/test.doi"
        assert paper.title == "Test Paper"
        assert len(paper.authors) == 2
        assert paper.year == 2023
        assert paper.citation_count == 42
        assert paper.is_open_access is True

    def test_paper_minimal(self):
        """Test creating a Paper with minimal fields."""
        paper = Paper(
            title="Minimal Paper",
            source_database="test",
        )

        assert paper.title == "Minimal Paper"
        assert paper.doi is None
        assert paper.authors == []
        assert paper.year is None

    def test_paper_get_primary_id(self):
        """Test get_primary_id method."""
        paper = Paper(
            title="Test",
            doi="10.1234/test",
            pmid="12345678",
            source_database="test",
        )

        # Should prefer DOI
        assert paper.get_primary_id() == "10.1234/test"

        # Test with only PMID
        paper2 = Paper(title="Test", pmid="12345678", source_database="test")
        assert paper2.get_primary_id() == "12345678"

    def test_paper_get_available_fields(self):
        """Test get_available_fields method."""
        paper = Paper(
            title="Test",
            doi="10.1234/test",
            abstract="Test abstract",
            year=2023,
            source_database="test",
        )

        available = paper.get_available_fields()

        assert "title" in available
        assert "doi" in available
        assert "abstract" in available
        assert "year" in available
        assert "pdf_url" not in available  # This is None


class TestSearchFilters:
    """Test suite for SearchFilters model."""

    def test_filters_creation(self):
        """Test creating SearchFilters."""
        filters = SearchFilters(
            title="machine learning",
            author="John Doe",
            venue="ICML",
            year=2023,
            max_results=100,
        )

        assert filters.title == "machine learning"
        assert filters.author == "John Doe"
        assert filters.venue == "ICML"
        assert filters.year == 2023
        assert filters.max_results == 100

    def test_filters_defaults(self):
        """Test default values for SearchFilters."""
        filters = SearchFilters()

        assert filters.max_results == 100
        assert filters.offset == 0
        assert filters.combine_filters_with_and is True

    def test_filters_year_range(self):
        """Test year range filters."""
        filters = SearchFilters(year_start=2020, year_end=2023)

        assert filters.year_start == 2020
        assert filters.year_end == 2023
        assert filters.year is None

    def test_filters_required_fields(self):
        """Test required_fields filter."""
        filters = SearchFilters(required_fields=["abstract", "doi"])

        assert filters.required_fields is not None
        assert "abstract" in filters.required_fields
        assert "doi" in filters.required_fields


class TestFieldStatistics:
    """Test suite for FieldStatistics model."""

    def test_field_statistics_creation(self):
        """Test creating FieldStatistics."""
        stat = FieldStatistics(field_name="abstract", available_count=85, total_count=100, percentage=85.0)

        assert stat.field_name == "abstract"
        assert stat.available_count == 85
        assert stat.total_count == 100
        assert stat.percentage == 85.0

    def test_field_statistics_zero_total(self):
        """Test FieldStatistics with zero total."""
        stat = FieldStatistics(field_name="test", available_count=0, total_count=0, percentage=0.0)

        assert stat.percentage == 0.0

    def test_field_statistics_str(self):
        """Test string representation."""
        stat = FieldStatistics(field_name="abstract", available_count=85, total_count=100, percentage=85.0)

        assert str(stat) == "abstract: 85/100 (85.0%)"


class TestSearchResult:
    """Test suite for SearchResult model."""

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        return [
            Paper(
                title="Paper 1",
                doi="10.1234/paper1",
                abstract="Abstract 1",
                year=2023,
                source_database="crossref",
            ),
            Paper(
                title="Paper 2",
                doi="10.1234/paper2",
                year=2023,
                source_database="crossref",
            ),
            Paper(
                title="Paper 3",
                doi="10.1234/paper3",
                abstract="Abstract 3",
                source_database="crossref",
            ),
        ]

    def test_search_result_creation(self, sample_papers):
        """Test creating SearchResult."""
        result = SearchResult(
            papers=sample_papers,
            total_results=3,
            databases_queried=["crossref"],
        )

        assert len(result.papers) == 3
        assert result.total_results == 3
        assert "crossref" in result.databases_queried

    def test_search_result_len(self, sample_papers):
        """Test __len__ method."""
        result = SearchResult(papers=sample_papers)

        assert len(result) == 3

    def test_search_result_getitem(self, sample_papers):
        """Test __getitem__ method."""
        result = SearchResult(papers=sample_papers)

        assert result[0].title == "Paper 1"
        assert result[1].title == "Paper 2"

    def test_field_statistics(self, sample_papers):
        """Test field_statistics method."""
        result = SearchResult(papers=sample_papers)

        stats = result.field_statistics()

        assert "doi" in stats
        assert "abstract" in stats
        assert stats["doi"].available_count == 3
        assert stats["doi"].total_count == 3
        assert stats["abstract"].available_count == 2
        assert stats["abstract"].total_count == 3

    def test_filter_by_required_fields(self, sample_papers):
        """Test filter_by_required_fields method."""
        result = SearchResult(papers=sample_papers)

        filtered = result.filter_by_required_fields(["abstract"])

        assert len(filtered) == 2
        assert all(paper.abstract is not None for paper in filtered.papers)

    def test_filter_by_required_fields_empty(self, sample_papers):
        """Test filtering with no papers matching."""
        result = SearchResult(papers=sample_papers)

        filtered = result.filter_by_required_fields(["pdf_url"])

        assert len(filtered) == 0

    def test_get_field_coverage_report(self, sample_papers):
        """Test get_field_coverage_report method."""
        result = SearchResult(papers=sample_papers)

        report = result.get_field_coverage_report()

        assert "Field Coverage Report" in report
        assert "doi:" in report or "doi" in report
        assert "abstract:" in report or "abstract" in report

    def test_add_paper(self, sample_papers):
        """Test adding a single paper."""
        result = SearchResult()
        result.add_paper(sample_papers[0])

        assert len(result) == 1
        assert result.total_results == 1

    def test_extend_papers(self, sample_papers):
        """Test extending with multiple papers."""
        result = SearchResult()
        result.extend(sample_papers)

        assert len(result) == 3
        assert result.total_results == 3

    def test_empty_search_result(self):
        """Test empty search result."""
        result = SearchResult(papers=[])

        assert len(result) == 0
        assert result.field_statistics() == {}
