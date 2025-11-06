"""Tests for normalization utilities."""

import pytest
from datetime import datetime

from paperseek.utils.normalization import (
    TextNormalizer,
    DateNormalizer,
    AuthorNormalizer,
    IdentifierNormalizer,
    URLNormalizer,
    VenueNormalizer,
)
from paperseek.core.models import Author


class TestTextNormalizer:
    """Tests for TextNormalizer."""

    def test_clean_text_basic(self):
        """Test basic text cleaning."""
        result = TextNormalizer.clean_text("  Hello World  ")
        assert result == "Hello World"

    def test_clean_text_multiple_spaces(self):
        """Test cleaning multiple spaces."""
        result = TextNormalizer.clean_text("Hello    World   Test")
        assert result == "Hello World Test"

    def test_clean_text_newlines(self):
        """Test cleaning newlines."""
        result = TextNormalizer.clean_text("Hello\n\nWorld\nTest")
        assert result == "Hello World Test"

    def test_clean_text_tabs(self):
        """Test cleaning tabs."""
        result = TextNormalizer.clean_text("Hello\t\tWorld")
        assert result == "Hello World"

    def test_clean_text_none(self):
        """Test cleaning None."""
        result = TextNormalizer.clean_text(None)
        assert result is None

    def test_clean_text_empty(self):
        """Test cleaning empty string."""
        result = TextNormalizer.clean_text("")
        assert result is None

    def test_clean_text_whitespace_only(self):
        """Test cleaning whitespace-only string."""
        result = TextNormalizer.clean_text("   \n\t   ")
        assert result is None

    def test_truncate_text_basic(self):
        """Test basic text truncation."""
        text = "a" * 100
        result = TextNormalizer.truncate_text(text, max_length=50)
        assert result is not None
        assert len(result) == 53  # 50 + "..."
        assert result.endswith("...")

    def test_truncate_text_no_truncation_needed(self):
        """Test text that doesn't need truncation."""
        text = "Hello World"
        result = TextNormalizer.truncate_text(text, max_length=100)
        assert result == "Hello World"

    def test_truncate_text_none(self):
        """Test truncating None."""
        result = TextNormalizer.truncate_text(None)
        assert result is None

    def test_truncate_text_with_cleaning(self):
        """Test truncation also cleans text."""
        text = "  " + "a" * 100 + "  "
        result = TextNormalizer.truncate_text(text, max_length=50)
        assert result is not None
        assert len(result) == 53
        assert not result.startswith(" ")


class TestDateNormalizer:
    """Tests for DateNormalizer."""

    def test_extract_year_from_int(self):
        """Test extracting year from integer."""
        assert DateNormalizer.extract_year(2023) == 2023

    def test_extract_year_from_string_year(self):
        """Test extracting year from string year."""
        assert DateNormalizer.extract_year("2023") == 2023

    def test_extract_year_from_iso_date(self):
        """Test extracting year from ISO date string."""
        assert DateNormalizer.extract_year("2023-05-15") == 2023

    def test_extract_year_from_iso_datetime(self):
        """Test extracting year from ISO datetime string."""
        assert DateNormalizer.extract_year("2023-05-15T10:30:00Z") == 2023

    def test_extract_year_from_datetime_object(self):
        """Test extracting year from datetime object."""
        dt = datetime(2023, 5, 15)
        assert DateNormalizer.extract_year(dt) == 2023

    def test_extract_year_from_date_parts_list(self):
        """Test extracting year from date parts list."""
        assert DateNormalizer.extract_year([[2023, 5, 15]]) == 2023

    def test_extract_year_from_simple_list(self):
        """Test extracting year from simple list."""
        assert DateNormalizer.extract_year([2023, 5, 15]) == 2023

    def test_extract_year_from_dict(self):
        """Test extracting year from dictionary."""
        assert DateNormalizer.extract_year({"year": 2023}) == 2023

    def test_extract_year_from_text(self):
        """Test extracting year from text containing year."""
        assert DateNormalizer.extract_year("Published in 2023") == 2023

    def test_extract_year_invalid_range(self):
        """Test extracting year with invalid range."""
        assert DateNormalizer.extract_year(1800) is None
        assert DateNormalizer.extract_year(2200) is None

    def test_extract_year_none(self):
        """Test extracting year from None."""
        assert DateNormalizer.extract_year(None) is None

    def test_extract_year_empty_string(self):
        """Test extracting year from empty string."""
        assert DateNormalizer.extract_year("") is None

    def test_parse_date_parts_full(self):
        """Test parsing full date parts."""
        result = DateNormalizer.parse_date_parts([[2023, 5, 15]])
        assert result == "2023-05-15"

    def test_parse_date_parts_year_month(self):
        """Test parsing date parts with year and month only."""
        result = DateNormalizer.parse_date_parts([[2023, 5]])
        assert result == "2023-05-01"

    def test_parse_date_parts_year_only(self):
        """Test parsing date parts with year only."""
        result = DateNormalizer.parse_date_parts([[2023]])
        assert result == "2023-01-01"

    def test_parse_date_parts_dict(self):
        """Test parsing date parts from CrossRef-style dict."""
        result = DateNormalizer.parse_date_parts({"date-parts": [[2023, 5, 15]]})
        assert result == "2023-05-15"

    def test_parse_date_parts_simple_list(self):
        """Test parsing simple list of date parts."""
        result = DateNormalizer.parse_date_parts([2023, 5, 15])
        assert result == "2023-05-15"

    def test_parse_date_parts_none(self):
        """Test parsing None date parts."""
        assert DateNormalizer.parse_date_parts(None) is None

    def test_parse_date_parts_empty(self):
        """Test parsing empty date parts."""
        assert DateNormalizer.parse_date_parts([]) is None


class TestAuthorNormalizer:
    """Tests for AuthorNormalizer."""

    def test_normalize_author_name_full(self):
        """Test normalizing with full name."""
        result = AuthorNormalizer.normalize_author_name(full_name="John Doe")
        assert result == "John Doe"

    def test_normalize_author_name_given_family(self):
        """Test normalizing with given and family names."""
        result = AuthorNormalizer.normalize_author_name(given="John", family="Doe")
        assert result == "John Doe"

    def test_normalize_author_name_family_only(self):
        """Test normalizing with family name only."""
        result = AuthorNormalizer.normalize_author_name(family="Doe")
        assert result == "Doe"

    def test_normalize_author_name_given_only(self):
        """Test normalizing with given name only."""
        result = AuthorNormalizer.normalize_author_name(given="John")
        assert result == "John"

    def test_normalize_author_name_none(self):
        """Test normalizing with all None."""
        result = AuthorNormalizer.normalize_author_name()
        assert result == "Unknown"

    def test_normalize_author_name_whitespace(self):
        """Test normalizing with whitespace."""
        result = AuthorNormalizer.normalize_author_name(given="  John  ", family="  Doe  ")
        assert result == "John Doe"

    def test_normalize_author_name_full_preferred(self):
        """Test that full name is preferred over given/family."""
        result = AuthorNormalizer.normalize_author_name(
            full_name="Jane Smith", given="John", family="Doe"
        )
        assert result == "Jane Smith"

    def test_create_author_full(self):
        """Test creating author with all fields."""
        author = AuthorNormalizer.create_author(
            name="John Doe",
            affiliation="MIT",
            orcid="0000-0001-2345-6789",
        )
        assert isinstance(author, Author)
        assert author.name == "John Doe"
        assert author.affiliation == "MIT"
        assert author.orcid == "0000-0001-2345-6789"

    def test_create_author_minimal(self):
        """Test creating author with minimal fields."""
        author = AuthorNormalizer.create_author(name="John Doe")
        assert isinstance(author, Author)
        assert author.name == "John Doe"
        assert author.affiliation is None
        assert author.orcid is None

    def test_create_author_given_family(self):
        """Test creating author from given and family names."""
        author = AuthorNormalizer.create_author(given="John", family="Doe")
        assert isinstance(author, Author)
        assert author.name == "John Doe"

    def test_create_author_whitespace_cleaning(self):
        """Test that whitespace is cleaned in author creation."""
        author = AuthorNormalizer.create_author(
            name="  John Doe  ",
            affiliation="  MIT  ",
            orcid="  0000-0001-2345-6789  ",
        )
        assert author.name == "John Doe"
        assert author.affiliation == "MIT"
        assert author.orcid == "0000-0001-2345-6789"


class TestIdentifierNormalizer:
    """Tests for IdentifierNormalizer."""

    def test_clean_doi_basic(self):
        """Test basic DOI cleaning."""
        result = IdentifierNormalizer.clean_doi("10.1234/test")
        assert result == "10.1234/test"

    def test_clean_doi_with_prefix(self):
        """Test cleaning DOI with doi: prefix."""
        result = IdentifierNormalizer.clean_doi("doi:10.1234/test")
        assert result == "10.1234/test"

    def test_clean_doi_with_DOI_prefix(self):
        """Test cleaning DOI with DOI: prefix."""
        result = IdentifierNormalizer.clean_doi("DOI:10.1234/test")
        assert result == "10.1234/test"

    def test_clean_doi_with_url(self):
        """Test cleaning DOI from URL."""
        result = IdentifierNormalizer.clean_doi("https://doi.org/10.1234/test")
        assert result == "10.1234/test"

    def test_clean_doi_with_dx_url(self):
        """Test cleaning DOI from dx.doi.org URL."""
        result = IdentifierNormalizer.clean_doi("http://dx.doi.org/10.1234/test")
        assert result == "10.1234/test"

    def test_clean_doi_whitespace(self):
        """Test cleaning DOI with whitespace."""
        result = IdentifierNormalizer.clean_doi("  10.1234/test  ")
        assert result == "10.1234/test"

    def test_clean_doi_none(self):
        """Test cleaning None DOI."""
        assert IdentifierNormalizer.clean_doi(None) is None

    def test_clean_doi_empty(self):
        """Test cleaning empty DOI."""
        assert IdentifierNormalizer.clean_doi("") is None

    def test_extract_arxiv_id_basic(self):
        """Test extracting basic arXiv ID."""
        result = IdentifierNormalizer.extract_arxiv_id("2301.12345")
        assert result == "2301.12345"

    def test_extract_arxiv_id_with_prefix(self):
        """Test extracting arXiv ID with prefix."""
        result = IdentifierNormalizer.extract_arxiv_id("arXiv:2301.12345")
        assert result == "2301.12345"

    def test_extract_arxiv_id_with_version(self):
        """Test extracting arXiv ID with version."""
        result = IdentifierNormalizer.extract_arxiv_id("2301.12345v2")
        assert result == "2301.12345v2"

    def test_extract_arxiv_id_from_abs_url(self):
        """Test extracting arXiv ID from abs URL."""
        result = IdentifierNormalizer.extract_arxiv_id("https://arxiv.org/abs/2301.12345")
        assert result == "2301.12345"

    def test_extract_arxiv_id_from_pdf_url(self):
        """Test extracting arXiv ID from pdf URL."""
        result = IdentifierNormalizer.extract_arxiv_id("https://arxiv.org/pdf/2301.12345.pdf")
        assert result == "2301.12345"

    def test_extract_arxiv_id_none(self):
        """Test extracting arXiv ID from None."""
        assert IdentifierNormalizer.extract_arxiv_id(None) is None

    def test_extract_arxiv_id_invalid(self):
        """Test extracting arXiv ID from invalid text."""
        assert IdentifierNormalizer.extract_arxiv_id("not an arxiv id") is None

    def test_extract_pmid_basic(self):
        """Test extracting basic PMID."""
        result = IdentifierNormalizer.extract_pmid("12345678")
        assert result == "12345678"

    def test_extract_pmid_from_url(self):
        """Test extracting PMID from URL."""
        result = IdentifierNormalizer.extract_pmid("https://pubmed.ncbi.nlm.nih.gov/12345678/")
        assert result == "12345678"

    def test_extract_pmid_none(self):
        """Test extracting PMID from None."""
        assert IdentifierNormalizer.extract_pmid(None) is None

    def test_extract_pmid_invalid(self):
        """Test extracting PMID from invalid text."""
        assert IdentifierNormalizer.extract_pmid("not a pmid") is None


class TestURLNormalizer:
    """Tests for URLNormalizer."""

    def test_clean_url_basic(self):
        """Test basic URL cleaning."""
        result = URLNormalizer.clean_url("https://example.com")
        assert result == "https://example.com"

    def test_clean_url_with_path(self):
        """Test cleaning URL with path."""
        result = URLNormalizer.clean_url("https://example.com/path/to/resource")
        assert result == "https://example.com/path/to/resource"

    def test_clean_url_with_query(self):
        """Test cleaning URL with query parameters."""
        result = URLNormalizer.clean_url("https://example.com?param=value")
        assert result == "https://example.com?param=value"

    def test_clean_url_http(self):
        """Test cleaning HTTP URL."""
        result = URLNormalizer.clean_url("http://example.com")
        assert result == "http://example.com"

    def test_clean_url_whitespace(self):
        """Test cleaning URL with whitespace."""
        result = URLNormalizer.clean_url("  https://example.com  ")
        assert result == "https://example.com"

    def test_clean_url_none(self):
        """Test cleaning None URL."""
        assert URLNormalizer.clean_url(None) is None

    def test_clean_url_empty(self):
        """Test cleaning empty URL."""
        assert URLNormalizer.clean_url("") is None

    def test_clean_url_invalid(self):
        """Test cleaning invalid URL."""
        assert URLNormalizer.clean_url("not a url") is None

    def test_clean_url_no_scheme(self):
        """Test cleaning URL without scheme."""
        assert URLNormalizer.clean_url("example.com") is None

    def test_extract_pdf_url_by_content_type(self):
        """Test extracting PDF URL by content-type."""
        links = [
            {"content-type": "application/pdf", "URL": "https://example.com/paper.pdf"}
        ]
        result = URLNormalizer.extract_pdf_url(links)
        assert result == "https://example.com/paper.pdf"

    def test_extract_pdf_url_by_title(self):
        """Test extracting PDF URL by title."""
        links = [
            {"title": "pdf", "url": "https://example.com/paper.pdf"}
        ]
        result = URLNormalizer.extract_pdf_url(links)
        assert result == "https://example.com/paper.pdf"

    def test_extract_pdf_url_by_rel(self):
        """Test extracting PDF URL by rel."""
        links = [
            {"rel": "pdf", "href": "https://example.com/paper.pdf"}
        ]
        result = URLNormalizer.extract_pdf_url(links)
        assert result == "https://example.com/paper.pdf"

    def test_extract_pdf_url_multiple_links(self):
        """Test extracting PDF URL from multiple links."""
        links = [
            {"content-type": "text/html", "URL": "https://example.com/page.html"},
            {"content-type": "application/pdf", "URL": "https://example.com/paper.pdf"},
        ]
        result = URLNormalizer.extract_pdf_url(links)
        assert result == "https://example.com/paper.pdf"

    def test_extract_pdf_url_empty_list(self):
        """Test extracting PDF URL from empty list."""
        assert URLNormalizer.extract_pdf_url([]) is None

    def test_extract_pdf_url_no_pdf(self):
        """Test extracting PDF URL when no PDF link exists."""
        links = [
            {"content-type": "text/html", "URL": "https://example.com/page.html"}
        ]
        assert URLNormalizer.extract_pdf_url(links) is None


class TestVenueNormalizer:
    """Tests for VenueNormalizer."""

    def test_classify_venue_type_conference_by_type(self):
        """Test classifying conference by publication type."""
        journal, conference = VenueNormalizer.classify_venue_type(
            venue="Test Venue",
            publication_type="proceedings-article"
        )
        assert journal is None
        assert conference == "Test Venue"

    def test_classify_venue_type_journal_by_type(self):
        """Test classifying journal by publication type."""
        journal, conference = VenueNormalizer.classify_venue_type(
            venue="Test Venue",
            publication_type="journal-article"
        )
        assert journal == "Test Venue"
        assert conference is None

    def test_classify_venue_type_conference_by_name(self):
        """Test classifying conference by venue name."""
        journal, conference = VenueNormalizer.classify_venue_type(
            venue="International Conference on Machine Learning"
        )
        assert journal is None
        assert conference == "International Conference on Machine Learning"

    def test_classify_venue_type_journal_by_name(self):
        """Test classifying journal by venue name."""
        journal, conference = VenueNormalizer.classify_venue_type(
            venue="Journal of Machine Learning Research"
        )
        assert journal == "Journal of Machine Learning Research"
        assert conference is None

    def test_classify_venue_type_default_journal(self):
        """Test default classification to journal."""
        journal, conference = VenueNormalizer.classify_venue_type(
            venue="Some Venue"
        )
        assert journal == "Some Venue"
        assert conference is None

    def test_classify_venue_type_none(self):
        """Test classifying None venue."""
        journal, conference = VenueNormalizer.classify_venue_type(None)
        assert journal is None
        assert conference is None

    def test_classify_venue_type_symposium(self):
        """Test classifying symposium as conference."""
        journal, conference = VenueNormalizer.classify_venue_type(
            venue="Annual Symposium on Foundations of Computer Science"
        )
        assert journal is None
        assert conference == "Annual Symposium on Foundations of Computer Science"

    def test_classify_venue_type_workshop(self):
        """Test classifying workshop as conference."""
        journal, conference = VenueNormalizer.classify_venue_type(
            venue="Workshop on Neural Information Processing Systems"
        )
        assert journal is None
        assert conference == "Workshop on Neural Information Processing Systems"

    def test_extract_venue_from_list_single(self):
        """Test extracting venue from single-item list."""
        result = VenueNormalizer.extract_venue_from_list(["Test Venue"])
        assert result == "Test Venue"

    def test_extract_venue_from_list_multiple(self):
        """Test extracting venue from multiple-item list."""
        result = VenueNormalizer.extract_venue_from_list(["Test Venue", "Other Venue"])
        assert result == "Test Venue"

    def test_extract_venue_from_list_empty(self):
        """Test extracting venue from empty list."""
        result = VenueNormalizer.extract_venue_from_list([])
        assert result is None

    def test_extract_venue_from_list_none(self):
        """Test extracting venue from None."""
        result = VenueNormalizer.extract_venue_from_list(None)
        assert result is None

    def test_extract_venue_from_list_with_default(self):
        """Test extracting venue with default value."""
        result = VenueNormalizer.extract_venue_from_list([], default="Default Venue")
        assert result == "Default Venue"

    def test_extract_venue_from_list_whitespace(self):
        """Test extracting venue with whitespace cleaning."""
        result = VenueNormalizer.extract_venue_from_list(["  Test Venue  "])
        assert result == "Test Venue"

    def test_extract_venue_from_list_skip_empty(self):
        """Test extracting venue skips empty strings."""
        result = VenueNormalizer.extract_venue_from_list(["", "  ", "Test Venue"])
        assert result == "Test Venue"
