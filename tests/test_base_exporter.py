"""Tests for the base exporter module."""

import pytest
from pathlib import Path
from typing import Any
from paperseek.core.models import Paper, Author, SearchResult
from paperseek.exporters.base import BaseExporter, StreamingExporter
from paperseek.core.exceptions import ExportError
import tempfile
import os
import shutil


# Concrete implementations for testing
class MockExporter(BaseExporter):
    """Concrete implementation of BaseExporter for testing."""
    
    def __init__(self):
        super().__init__()
        self.exported_data = None
    
    def _do_export(self, results: SearchResult, filename: str, **kwargs: Any) -> None:
        """Test export implementation."""
        self.exported_data = {
            "filename": filename,
            "count": len(results),
            "kwargs": kwargs,
        }
        # Actually write a file for path testing
        with open(filename, "w") as f:
            f.write(f"Exported {len(results)} papers")


class FailingExporter(BaseExporter):
    """Exporter that fails for error testing."""
    
    def _do_export(self, results: SearchResult, filename: str, **kwargs) -> None:
        """Failing export implementation."""
        raise ValueError("Export failed intentionally")


class ConcreteStreamingExporter(StreamingExporter):
    """Concrete implementation of StreamingExporter for testing."""
    
    def __init__(self):
        super().__init__()
        self.papers_written = []
    
    def _do_open(self, filename: str, **kwargs: Any) -> None:
        """Test open implementation."""
        self._file_handle = open(filename, "w")  # type: ignore
    
    def _do_write_paper(self, paper: Paper) -> None:
        """Test write implementation."""
        self.papers_written.append(paper.title)
        if self._file_handle:
            self._file_handle.write(f"{paper.title}\n")  # type: ignore
    
    def _do_close(self) -> None:
        """Test close implementation."""
        if self._file_handle:
            self._file_handle.close()  # type: ignore


class TestBaseExporter:
    """Tests for BaseExporter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.exporter = MockExporter()
        
        # Create test data
        self.papers = [
            Paper(
                title="Test Paper 1",
                authors=[Author(name="John Doe")],
                year=2020,
                source_database="test_db",
            ),
            Paper(
                title="Test Paper 2",
                authors=[Author(name="Jane Smith")],
                year=2021,
                source_database="test_db",
            ),
        ]
        self.results = SearchResult(
            query_info={"test": "query"},
            databases_queried=["test_db"],
        )
        for paper in self.papers:
            self.results.add_paper(paper)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_export_success(self):
        """Test successful export."""
        output_file = Path(self.temp_dir) / "test_export.txt"
        self.exporter.export(self.results, str(output_file))
        
        assert self.exporter.exported_data is not None
        assert self.exporter.exported_data["count"] == 2
        assert output_file.exists()
    
    def test_export_creates_directory(self):
        """Test that export creates parent directories."""
        output_file = Path(self.temp_dir) / "subdir" / "nested" / "test.txt"
        self.exporter.export(self.results, str(output_file))
        
        assert output_file.parent.exists()
        assert output_file.exists()
    
    def test_export_with_kwargs(self):
        """Test export with additional keyword arguments."""
        output_file = Path(self.temp_dir) / "test.txt"
        self.exporter.export(
            self.results,
            str(output_file),
            custom_param="value",
            another_param=123,
        )
        
        assert self.exporter.exported_data is not None
        assert self.exporter.exported_data["kwargs"]["custom_param"] == "value"
        assert self.exporter.exported_data["kwargs"]["another_param"] == 123
    
    def test_export_validates_none_results(self):
        """Test that export validates None results."""
        output_file = Path(self.temp_dir) / "test.txt"
        
        with pytest.raises(ExportError, match="results object is None"):
            self.exporter.export(None, str(output_file))  # type: ignore
    
    def test_export_validates_empty_results(self):
        """Test that export validates empty results."""
        output_file = Path(self.temp_dir) / "test.txt"
        empty_results = SearchResult(
            query_info={"test": "query"},
            databases_queried=["test_db"],
        )
        
        # Empty SearchResult has no papers, should fail validation
        with pytest.raises(ExportError, match="Cannot export"):
            self.exporter.export(empty_results, str(output_file))
    
    def test_export_validates_result_type(self):
        """Test that export validates result type."""
        output_file = Path(self.temp_dir) / "test.txt"
        
        with pytest.raises(ExportError, match="Failed to export"):
            self.exporter.export("not a SearchResult", str(output_file))  # type: ignore
    
    def test_export_wraps_exceptions(self):
        """Test that export wraps exceptions from _do_export."""
        failing_exporter = FailingExporter()
        output_file = Path(self.temp_dir) / "test.txt"
        
        with pytest.raises(ExportError, match="Failed to export"):
            failing_exporter.export(self.results, str(output_file))
    
    def test_validate_results_success(self):
        """Test successful validation."""
        # Should not raise
        self.exporter._validate_results(self.results)
    
    def test_prepare_output_directory(self):
        """Test directory preparation."""
        nested_path = Path(self.temp_dir) / "a" / "b" / "c" / "file.txt"
        self.exporter._prepare_output_directory(str(nested_path))
        
        assert nested_path.parent.exists()
    
    def test_get_output_path(self):
        """Test getting output path."""
        filename = "/tmp/test.txt"
        path = self.exporter._get_output_path(filename)
        
        assert isinstance(path, Path)
        assert str(path) == filename
    
    def test_logger_exists(self):
        """Test that logger is initialized."""
        assert self.exporter.logger is not None
        assert "MockExporter" in self.exporter.logger.name


class TestStreamingExporter:
    """Tests for StreamingExporter."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.exporter = ConcreteStreamingExporter()
        
        # Create test papers
        self.papers = [
            Paper(
                title="Paper 1",
                authors=[Author(name="Author 1")],
                year=2020,
                source_database="test_db",
            ),
            Paper(
                title="Paper 2",
                authors=[Author(name="Author 2")],
                year=2021,
                source_database="test_db",
            ),
            Paper(
                title="Paper 3",
                authors=[Author(name="Author 3")],
                year=2022,
                source_database="test_db",
            ),
        ]
    
    def teardown_method(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_open_creates_file(self):
        """Test that open creates the file."""
        output_file = Path(self.temp_dir) / "streaming.txt"
        self.exporter.open(str(output_file))
        
        assert self.exporter._file_handle is not None
        assert self.exporter._filename == str(output_file)
        
        self.exporter.close()
    
    def test_open_creates_directory(self):
        """Test that open creates parent directories."""
        output_file = Path(self.temp_dir) / "subdir" / "nested" / "streaming.txt"
        self.exporter.open(str(output_file))
        
        assert output_file.parent.exists()
        
        self.exporter.close()
    
    def test_write_paper_success(self):
        """Test writing a single paper."""
        output_file = Path(self.temp_dir) / "streaming.txt"
        self.exporter.open(str(output_file))
        
        self.exporter.write_paper(self.papers[0])
        
        assert len(self.exporter.papers_written) == 1
        assert self.exporter.papers_written[0] == "Paper 1"
        assert self.exporter._count == 1
        
        self.exporter.close()
    
    def test_write_multiple_papers(self):
        """Test writing multiple papers."""
        output_file = Path(self.temp_dir) / "streaming.txt"
        self.exporter.open(str(output_file))
        
        for paper in self.papers:
            self.exporter.write_paper(paper)
        
        assert len(self.exporter.papers_written) == 3
        assert self.exporter._count == 3
        
        self.exporter.close()
    
    def test_write_paper_without_open_fails(self):
        """Test that writing without opening fails."""
        with pytest.raises(ExportError, match="file not opened"):
            self.exporter.write_paper(self.papers[0])
    
    def test_close_success(self):
        """Test closing successfully."""
        output_file = Path(self.temp_dir) / "streaming.txt"
        self.exporter.open(str(output_file))
        self.exporter.write_paper(self.papers[0])
        
        self.exporter.close()
        
        assert self.exporter._file_handle is None
        assert self.exporter._count == 0  # Reset after close
    
    def test_close_without_open(self):
        """Test that closing without opening is safe."""
        # Should not raise
        self.exporter.close()
    
    def test_context_manager(self):
        """Test using exporter as context manager."""
        output_file = Path(self.temp_dir) / "streaming.txt"
        
        with self.exporter as exp:
            exp.open(str(output_file))
            exp.write_paper(self.papers[0])
            exp.write_paper(self.papers[1])
        
        # File should be closed after context
        assert self.exporter._file_handle is None
        
        # File should exist and contain data
        assert output_file.exists()
        content = output_file.read_text()
        assert "Paper 1" in content
        assert "Paper 2" in content
    
    def test_context_manager_exception_handling(self):
        """Test that context manager closes on exception."""
        output_file = Path(self.temp_dir) / "streaming.txt"
        
        try:
            with self.exporter as exp:
                exp.open(str(output_file))
                exp.write_paper(self.papers[0])
                raise ValueError("Test exception")
        except ValueError:
            pass
        
        # File should still be closed
        assert self.exporter._file_handle is None
    
    def test_logger_exists(self):
        """Test that logger is initialized."""
        assert self.exporter.logger is not None
        assert "ConcreteStreamingExporter" in self.exporter.logger.name
    
    def test_count_resets_on_close(self):
        """Test that counter resets when closing."""
        output_file = Path(self.temp_dir) / "streaming.txt"
        
        self.exporter.open(str(output_file))
        self.exporter.write_paper(self.papers[0])
        self.exporter.write_paper(self.papers[1])
        assert self.exporter._count == 2
        
        self.exporter.close()
        assert self.exporter._count == 0
        
        # Can reopen and count starts fresh
        self.exporter.open(str(output_file))
        self.exporter.write_paper(self.papers[2])
        assert self.exporter._count == 1
        
        self.exporter.close()
    
    def test_write_paper_increments_count(self):
        """Test that write_paper increments counter correctly."""
        output_file = Path(self.temp_dir) / "streaming.txt"
        self.exporter.open(str(output_file))
        
        assert self.exporter._count == 0
        
        for i, paper in enumerate(self.papers, 1):
            self.exporter.write_paper(paper)
            assert self.exporter._count == i
        
        self.exporter.close()
    
    def test_multiple_open_close_cycles(self):
        """Test multiple open/close cycles."""
        output_file1 = Path(self.temp_dir) / "file1.txt"
        output_file2 = Path(self.temp_dir) / "file2.txt"
        
        # First cycle
        self.exporter.open(str(output_file1))
        self.exporter.write_paper(self.papers[0])
        self.exporter.close()
        
        # Second cycle
        self.exporter.open(str(output_file2))
        self.exporter.write_paper(self.papers[1])
        self.exporter.write_paper(self.papers[2])
        self.exporter.close()
        
        # Both files should exist
        assert output_file1.exists()
        assert output_file2.exists()
        
        # Check contents
        assert "Paper 1" in output_file1.read_text()
        assert "Paper 2" in output_file2.read_text()
        assert "Paper 3" in output_file2.read_text()
