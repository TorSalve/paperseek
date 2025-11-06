"""Unit tests for CSV exporter."""

import pytest
import tempfile
import csv
from pathlib import Path

from paperseek.exporters.csv_exporter import CSVExporter, StreamingCSVExporter
from paperseek.core.models import SearchResult, Paper, Author
from paperseek.core.exceptions import ExportError


class TestCSVExporter:
    """Test suite for CSVExporter."""

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        author1 = Author(name="John Doe", affiliation="University A")
        author2 = Author(name="Jane Smith", affiliation="University B")
        
        paper1 = Paper(
            doi="10.1234/paper1",
            title="First Paper",
            authors=[author1],
            year=2023,
            journal="Test Journal",
            abstract="This is a test abstract",
            keywords=["machine learning", "AI"],
            citation_count=10,
            url="https://example.com/paper1",
            source_database="test",
        )
        
        paper2 = Paper(
            doi="10.1234/paper2",
            title="Second Paper",
            authors=[author1, author2],
            year=2024,
            conference="Test Conference",
            abstract="Another abstract",
            keywords=["deep learning"],
            citation_count=5,
            source_database="test",
        )
        
        return [paper1, paper2]

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
        exporter = CSVExporter()
        assert exporter.logger is not None

    def test_export_basic(self, search_result):
        """Test basic CSV export."""
        exporter = CSVExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath)
            
            # Verify file exists
            assert Path(filepath).exists()
            
            # Read and verify content
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                # Skip metadata rows (start with #)
                content = f.read()
                f.seek(0)
                
                # Find where actual CSV starts
                lines = f.readlines()
                csv_start = 0
                for i, line in enumerate(lines):
                    if not line.startswith('#') and line.strip():
                        csv_start = i
                        break
                
                # Read CSV from actual start
                f.seek(0)
                for _ in range(csv_start):
                    f.readline()
                
                reader = csv.DictReader(f)
                rows = list(reader)
                
            assert len(rows) == 2
            assert rows[0]['title'] == "First Paper"
            assert rows[0]['doi'] == "10.1234/paper1"
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_without_metadata(self, search_result):
        """Test export without metadata."""
        exporter = CSVExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath, include_metadata=False)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
                # No metadata lines should start with #
                assert not any(line.startswith('#') for line in content.split('\n'))
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_custom_columns(self, search_result):
        """Test export with custom columns."""
        exporter = CSVExporter()
        columns = ["title", "year", "doi"]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath, columns=columns, include_metadata=False)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
            assert len(rows) == 2
            # Check only requested columns are present
            assert set(rows[0].keys()) == set(columns)
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_creates_directory(self, search_result):
        """Test that export creates parent directory if needed."""
        exporter = CSVExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "subdir" / "output.csv"
            
            exporter.export(search_result, str(filepath))
            
            assert filepath.exists()
        
    def test_export_empty_result(self):
        """Test exporting empty search result."""
        exporter = CSVExporter()
        empty_result = SearchResult(
            query_info={},
            databases_queried=["test"],
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(empty_result, filepath, include_metadata=False)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 0
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_authors_format(self, search_result):
        """Test that authors are formatted correctly."""
        exporter = CSVExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath, include_metadata=False)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # First paper has 1 author
            assert rows[0]['authors'] == "John Doe"
            # Second paper has 2 authors
            assert rows[1]['authors'] == "John Doe; Jane Smith"
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_keywords_format(self, search_result):
        """Test that keywords are formatted correctly."""
        exporter = CSVExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath, include_metadata=False)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert rows[0]['keywords'] == "machine learning, AI"
            assert rows[1]['keywords'] == "deep learning"
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_field_statistics(self, search_result):
        """Test exporting field statistics."""
        exporter = CSVExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export_field_statistics(search_result, filepath)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
            
            # Check header
            assert rows[0] == ["Field", "Available", "Total", "Percentage"]
            
            # Check data rows exist
            assert len(rows) > 1
            
            # Check format of data rows
            for row in rows[1:]:
                assert len(row) == 4
                # Percentage should end with %
                assert row[3].endswith('%')
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_error_handling(self, search_result):
        """Test error handling during export."""
        exporter = CSVExporter()
        
        # Try to export to invalid path
        with pytest.raises(ExportError):
            exporter.export(search_result, "/invalid/path/that/does/not/exist/file.csv")


class TestStreamingCSVExporter:
    """Test suite for StreamingCSVExporter."""

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        author = Author(name="John Doe")
        
        papers = []
        for i in range(10):
            paper = Paper(
                doi=f"10.1234/paper{i}",
                title=f"Paper {i}",
                authors=[author],
                year=2023,
                source_database="test",
            )
            papers.append(paper)
        
        return papers

    def test_init(self):
        """Test streaming exporter initialization."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            exporter = StreamingCSVExporter(filepath)
            assert exporter.filename == filepath
            assert exporter.count == 0
            exporter.close()
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_write_single_paper(self, sample_papers):
        """Test writing a single paper."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            exporter = StreamingCSVExporter(filepath)
            exporter.write_paper(sample_papers[0])
            exporter.close()
            
            # Verify
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 1
            assert rows[0]['title'] == "Paper 0"
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_write_multiple_papers(self, sample_papers):
        """Test writing multiple papers."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            exporter = StreamingCSVExporter(filepath)
            exporter.write_papers(sample_papers[:5])
            exporter.close()
            
            # Verify
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 5
            assert exporter.count == 5
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_context_manager(self, sample_papers):
        """Test using as context manager."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            with StreamingCSVExporter(filepath) as exporter:
                for paper in sample_papers:
                    exporter.write_paper(paper)
            
            # Verify file is closed and data is written
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 10
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_custom_columns(self, sample_papers):
        """Test with custom columns."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            filepath = f.name
        
        try:
            columns = ["title", "year", "doi"]
            exporter = StreamingCSVExporter(filepath, columns=columns)
            exporter.write_paper(sample_papers[0])
            exporter.close()
            
            # Verify columns
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert set(rows[0].keys()) == set(columns)
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_creates_directory(self, sample_papers):
        """Test that it creates parent directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "subdir" / "output.csv"
            
            exporter = StreamingCSVExporter(str(filepath))
            exporter.write_paper(sample_papers[0])
            exporter.close()
            
            assert filepath.exists()
