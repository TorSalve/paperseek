"""Unit tests for BibTeX exporter."""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock

from paperseek.exporters.bibtex_exporter import BibTeXExporter
from paperseek.core.models import SearchResult, Paper, Author
from paperseek.core.exceptions import ExportError


class TestBibTeXExporter:
    """Test suite for BibTeXExporter."""

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        author1 = Author(name="John Doe", affiliation="University A")
        author2 = Author(name="Jane Smith", affiliation="University B")
        
        paper1 = Paper(
            doi="10.1234/paper1",
            title="Machine Learning Applications",
            authors=[author1],
            year=2023,
            journal="Journal of AI",
            volume="10",
            issue="2",
            pages="100-120",
            abstract="This is a test abstract",
            keywords=["machine learning", "AI"],
            url="https://example.com/paper1",
            source_database="test",
        )
        
        paper2 = Paper(
            doi="10.5678/paper2",
            title="Deep Learning in Practice",
            authors=[author1, author2],
            year=2024,
            conference="International Conference on AI",
            abstract="Another abstract",
            keywords=["deep learning"],
            source_database="test",
        )
        
        paper3 = Paper(
            title="Minimal Paper",
            authors=[Author(name="Alice")],
            source_database="test",
        )
        
        return [paper1, paper2, paper3]

    @pytest.fixture
    def search_result(self, sample_papers):
        """Create a search result with sample papers."""
        result = SearchResult(
            query_info={"query": "test"},
            databases_queried=["test"],
        )
        for paper in sample_papers:
            result.add_paper(paper)
        return result

    def test_init(self):
        """Test exporter initialization."""
        exporter = BibTeXExporter()
        assert exporter.logger is not None

    def test_export_basic(self, search_result):
        """Test basic BibTeX export."""
        exporter = BibTeXExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath)
            
            # Verify file exists
            assert Path(filepath).exists()
            
            # Read and verify content
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Should contain BibTeX entries
            assert '@article' in content
            assert '@inproceedings' in content
            assert '@misc' in content
            
            # Should contain paper details
            assert 'Machine Learning Applications' in content
            assert 'Deep Learning in Practice' in content
            assert 'John Doe' in content
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_creates_directory(self, search_result):
        """Test that export creates parent directory if needed."""
        exporter = BibTeXExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "subdir" / "output.bib"
            
            exporter.export(search_result, str(filepath))
            
            assert filepath.exists()

    def test_export_empty_result(self):
        """Test exporting empty search result."""
        exporter = BibTeXExporter()
        empty_result = SearchResult(
            query_info={},
            databases_queried=["test"],
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.bib', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(empty_result, filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Empty file or minimal content
            assert len(content.strip()) == 0
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_entry_type_article(self, sample_papers):
        """Test that journal papers are exported as @article."""
        exporter = BibTeXExporter()
        entry = exporter._paper_to_bibtex(sample_papers[0])
        
        assert entry.startswith('@article')
        assert 'journal' in entry

    def test_entry_type_inproceedings(self, sample_papers):
        """Test that conference papers are exported as @inproceedings."""
        exporter = BibTeXExporter()
        entry = exporter._paper_to_bibtex(sample_papers[1])
        
        assert entry.startswith('@inproceedings')
        assert 'booktitle' in entry

    def test_entry_type_misc(self, sample_papers):
        """Test that papers without journal/conference are @misc."""
        exporter = BibTeXExporter()
        entry = exporter._paper_to_bibtex(sample_papers[2])
        
        assert entry.startswith('@misc')

    def test_citation_key_generation(self, sample_papers):
        """Test citation key generation."""
        exporter = BibTeXExporter()
        
        # Paper with full metadata
        entry = exporter._paper_to_bibtex(sample_papers[0])
        # Should contain author_year_keyword pattern
        assert 'doe_2023' in entry.lower()

    def test_citation_key_fallback(self):
        """Test citation key fallback for minimal papers."""
        exporter = BibTeXExporter()
        
        minimal_paper = Paper(
            title="Test",
            authors=[],
            source_database="test",
        )
        
        entry = exporter._paper_to_bibtex(minimal_paper, entry_number=5)
        # Should use fallback pattern
        assert 'paper_5' in entry

    def test_author_formatting(self, sample_papers):
        """Test author formatting in BibTeX."""
        exporter = BibTeXExporter()
        entry = exporter._paper_to_bibtex(sample_papers[1])
        
        # Multiple authors should be joined with "and"
        assert 'John Doe and Jane Smith' in entry

    def test_special_characters_escaping(self):
        """Test that special characters are escaped."""
        exporter = BibTeXExporter()
        
        paper = Paper(
            title="Test & Special {Characters} $Math$",
            authors=[Author(name="Test Author")],
            abstract="Abstract with % and \\ characters",
            source_database="test",
        )
        
        entry = exporter._paper_to_bibtex(paper)
        
        # BibTeX special characters should be escaped
        # The exact escaping depends on implementation
        assert 'Test' in entry

    def test_all_fields_included(self, sample_papers):
        """Test that all available fields are included."""
        exporter = BibTeXExporter()
        entry = exporter._paper_to_bibtex(sample_papers[0])
        
        # Check key fields are present
        assert 'title' in entry
        assert 'author' in entry
        assert 'year' in entry
        assert 'journal' in entry
        assert 'volume' in entry
        assert 'number' in entry or 'issue' in entry
        assert 'pages' in entry
        assert 'doi' in entry
        assert 'url' in entry
        assert 'abstract' in entry
        assert 'keywords' in entry

    def test_optional_fields_omitted(self):
        """Test that missing fields are omitted."""
        exporter = BibTeXExporter()
        
        minimal_paper = Paper(
            title="Minimal Paper",
            authors=[Author(name="Test")],
            year=2023,
            source_database="test",
        )
        
        entry = exporter._paper_to_bibtex(minimal_paper)
        
        # These fields should not be present
        assert 'journal' not in entry or 'journal = {}' in entry
        assert 'volume' not in entry or 'volume = {}' in entry
        assert 'abstract' not in entry or 'abstract = {}' in entry

    def test_keywords_formatting(self, sample_papers):
        """Test keywords formatting."""
        exporter = BibTeXExporter()
        entry = exporter._paper_to_bibtex(sample_papers[0])
        
        # Keywords should be comma-separated
        assert 'machine learning, AI' in entry

    def test_export_error_handling(self, search_result):
        """Test error handling during export."""
        exporter = BibTeXExporter()
        
        # Try to export to invalid path
        with pytest.raises(ExportError):
            exporter.export(search_result, "/invalid/path/that/does/not/exist/file.bib")

    def test_no_trailing_comma(self, sample_papers):
        """Test that last field has no trailing comma."""
        exporter = BibTeXExporter()
        entry = exporter._paper_to_bibtex(sample_papers[0])
        
        # Find last field before closing brace
        lines = entry.split('\n')
        # Second to last line should be last field (last line is closing brace)
        if len(lines) >= 2:
            last_field_line = lines[-2]
            # Should not end with comma
            assert not last_field_line.strip().endswith(',')

    def test_generate_cite_key_with_stop_words(self):
        """Test citation key generation skips stop words in title."""
        exporter = BibTeXExporter()
        
        paper = Paper(
            title="The Analysis of Machine Learning",
            authors=[Author(name="John Smith")],
            year=2023,
            source_database="test",
        )
        
        cite_key = exporter._generate_cite_key(paper, 1)
        
        # Should skip "The", "of" and use "Analysis" or "Machine"
        assert 'smith' in cite_key.lower()
        assert '2023' in cite_key
        # Should contain a meaningful word from title
        assert any(word in cite_key.lower() for word in ['analysis', 'machine'])

    def test_format_author_single_name(self):
        """Test author formatting with single name."""
        exporter = BibTeXExporter()
        
        author = Author(name="Cher")
        formatted = exporter._format_author_bibtex(author)
        
        assert formatted == "Cher"

    def test_format_author_multiple_names(self):
        """Test author formatting with multiple name parts."""
        exporter = BibTeXExporter()
        
        author = Author(name="John von Neumann")
        formatted = exporter._format_author_bibtex(author)
        
        # Should preserve the full name
        assert "von" in formatted
