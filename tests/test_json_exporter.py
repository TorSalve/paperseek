"""Unit tests for JSON exporter."""

import pytest
import json
import tempfile
from pathlib import Path

from paperseek.exporters.json_exporter import JSONExporter
from paperseek.core.models import Paper, Author, SearchResult


class TestJSONExporter:
    """Test suite for JSONExporter."""

    @pytest.fixture
    def sample_papers(self):
        """Create sample papers for testing."""
        return [
            Paper(
                doi="10.1234/paper1",
                title="First Paper",
                authors=[Author(name="John Doe", affiliation="University A")],
                abstract="This is the first paper",
                year=2023,
                journal="Test Journal",
                source_database="crossref",
            ),
            Paper(
                doi="10.1234/paper2",
                title="Second Paper",
                authors=[Author(name="Jane Smith")],
                year=2024,
                source_database="openalex",
            ),
        ]

    @pytest.fixture
    def search_result(self, sample_papers):
        """Create a search result."""
        result = SearchResult(
            query_info={"query": "test"},
            databases_queried=["crossref", "openalex"],
        )
        for paper in sample_papers:
            result.add_paper(paper)
        return result

    def test_init(self):
        """Test exporter initialization."""
        exporter = JSONExporter()
        assert exporter.logger is not None

    def test_export_to_file_pretty(self, search_result):
        """Test exporting to file with pretty printing."""
        exporter = JSONExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath, pretty=True)
            
            # Verify file was created and contains valid JSON
            with open(filepath, 'r') as f:
                content = f.read()
                data = json.loads(content)
            
            assert "papers" in data
            assert len(data["papers"]) == 2
            # Pretty-printed JSON should have newlines
            assert '\n' in content
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_to_file_compact(self, search_result):
        """Test exporting to file without pretty printing."""
        exporter = JSONExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath, pretty=False)
            
            # Verify file was created
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert "papers" in data
            assert len(data["papers"]) == 2
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_empty_result(self):
        """Test exporting empty search result."""
        exporter = JSONExporter()
        empty_result = SearchResult(
            query_info={},
            databases_queried=["test"],
        )
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(empty_result, filepath)
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert "papers" in data
            assert len(data["papers"]) == 0
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_with_raw_data(self, search_result):
        """Test exporting with raw API data included."""
        exporter = JSONExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath, include_raw=True)
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert "papers" in data
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_without_raw_data(self, search_result):
        """Test exporting without raw API data."""
        exporter = JSONExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath, include_raw=False)
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert "papers" in data
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_creates_directory(self, search_result):
        """Test that export creates parent directory if needed."""
        exporter = JSONExporter()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            filepath = Path(tmpdir) / "subdir" / "output.json"
            
            exporter.export(search_result, str(filepath))
            
            assert filepath.exists()
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert "papers" in data

    def test_export_large_dataset(self):
        """Test exporting large dataset."""
        exporter = JSONExporter()
        
        # Create a result with many papers
        result = SearchResult(query_info={}, databases_queried=["test"])
        for i in range(100):
            paper = Paper(
                doi=f"10.1234/paper{i}",
                title=f"Paper {i}",
                authors=[],
                source_database="test",
            )
            result.add_paper(paper)
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(result, filepath)
            
            # Verify all papers were exported
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            assert len(data["papers"]) == 100
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_paper_with_all_fields(self, sample_papers):
        """Test that all paper fields are correctly exported."""
        exporter = JSONExporter()
        result = SearchResult(query_info={}, databases_queried=["test"])
        result.add_paper(sample_papers[0])
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(result, filepath)
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            paper = data["papers"][0]
            assert paper["doi"] == "10.1234/paper1"
            assert paper["title"] == "First Paper"
            assert paper["year"] == 2023
            assert paper["journal"] == "Test Journal"
            assert len(paper["authors"]) == 1
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_jsonl(self, search_result):
        """Test exporting to JSONL format."""
        exporter = JSONExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export_jsonl(search_result, filepath)
            
            # Verify file was created
            assert Path(filepath).exists()
            
            # Read and verify JSONL content
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            assert len(lines) == 2  # Two papers
            
            # Each line should be valid JSON
            for line in lines:
                paper_data = json.loads(line)
                assert "title" in paper_data
                assert "doi" in paper_data
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_jsonl_with_raw(self, search_result):
        """Test JSONL export with raw data."""
        exporter = JSONExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export_jsonl(search_result, filepath, include_raw=True)
            
            with open(filepath, 'r') as f:
                lines = f.readlines()
            
            assert len(lines) == 2
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_metadata_fields(self, search_result):
        """Test that metadata fields are correctly exported."""
        exporter = JSONExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath)
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Check metadata
            assert "metadata" in data
            metadata = data["metadata"]
            assert "total_results" in metadata
            assert "databases_queried" in metadata
            assert metadata["databases_queried"] == ["crossref", "openalex"]
            assert "search_timestamp" in metadata
            assert "query_info" in metadata
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_field_statistics(self, search_result):
        """Test that field statistics are included."""
        exporter = JSONExporter()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            filepath = f.name
        
        try:
            exporter.export(search_result, filepath)
            
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Check field statistics
            assert "field_statistics" in data
            stats = data["field_statistics"]
            assert isinstance(stats, dict)
            
            # Should have statistics for various fields
            for field_name, field_stat in stats.items():
                assert "available" in field_stat
                assert "total" in field_stat
                assert "percentage" in field_stat
        finally:
            Path(filepath).unlink(missing_ok=True)

    def test_export_error_handling(self, search_result):
        """Test error handling during export."""
        from paperseek.core.exceptions import ExportError
        
        exporter = JSONExporter()
        
        # Try to export to invalid path
        with pytest.raises(ExportError):
            exporter.export(search_result, "/invalid/path/that/does/not/exist/file.json")

    def test_export_jsonl_error_handling(self, search_result):
        """Test error handling during JSONL export."""
        from paperseek.core.exceptions import ExportError
        
        exporter = JSONExporter()
        
        # Try to export to invalid path
        with pytest.raises(ExportError):
            exporter.export_jsonl(search_result, "/invalid/path/that/does/not/exist/file.jsonl")
