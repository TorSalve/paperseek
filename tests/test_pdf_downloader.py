"""Unit tests for PDFDownloader."""

import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, mock_open
import tempfile
import shutil

from paperseek.utils.pdf_downloader import PDFDownloader
from paperseek.core.models import Paper, SearchResult, Author


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    # Cleanup
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_paper():
    """Create a sample paper for testing."""
    return Paper(
        title="Test Paper",
        authors=[Author(name="Author One"), Author(name="Author Two")],
        year=2023,
        source_database="test_db",
        source_id="test123",
        doi="10.1234/test.2023",
        pdf_url="https://example.com/paper.pdf",
        is_open_access=True,
    )


@pytest.fixture
def sample_paper_no_pdf():
    """Create a sample paper without PDF URL."""
    return Paper(
        title="Test Paper No PDF",
        authors=[Author(name="Author One")],
        year=2023,
        source_database="test_db",
        source_id="test456",
        doi="10.1234/test.2023.nopdf",
    )


@pytest.fixture
def mock_response():
    """Create a mock response object."""
    response = Mock()
    response.status_code = 200
    response.headers = {
        "Content-Type": "application/pdf",
        "Content-Length": "1024",
    }
    response.iter_content = lambda chunk_size: [b"%PDF-1.4 mock content"]
    response.raise_for_status = Mock()
    return response


class TestPDFDownloaderInit:
    """Test PDFDownloader initialization."""

    def test_init_defaults(self, temp_dir):
        """Test initialization with default parameters."""
        downloader = PDFDownloader(download_dir=temp_dir)
        
        assert downloader.download_dir == Path(temp_dir)
        assert downloader.rate_limit_seconds == 3.0
        assert downloader.timeout == 60
        assert downloader.max_file_size_bytes == 50 * 1024 * 1024
        assert downloader.overwrite is False
        assert downloader.verify_ssl is True
        assert "AcademicSearchUnified-PDFDownloader" in downloader.user_agent

    def test_init_custom_parameters(self, temp_dir):
        """Test initialization with custom parameters."""
        downloader = PDFDownloader(
            download_dir=temp_dir,
            rate_limit_seconds=5.0,
            timeout=120,
            max_file_size_mb=100,
            user_agent="CustomBot/1.0",
            email="test@example.com",
            overwrite=True,
            verify_ssl=False,
        )
        
        assert downloader.rate_limit_seconds == 5.0
        assert downloader.timeout == 120
        assert downloader.max_file_size_bytes == 100 * 1024 * 1024
        assert downloader.overwrite is True
        assert downloader.verify_ssl is False
        assert "test@example.com" in downloader.user_agent

    def test_init_creates_directory(self, temp_dir):
        """Test that initialization creates download directory."""
        download_path = Path(temp_dir) / "downloads" / "pdfs"
        downloader = PDFDownloader(download_dir=str(download_path))
        
        assert download_path.exists()
        assert download_path.is_dir()

    def test_init_statistics(self, temp_dir):
        """Test that statistics are initialized."""
        downloader = PDFDownloader(download_dir=temp_dir)
        
        assert downloader.stats["attempted"] == 0
        assert downloader.stats["successful"] == 0
        assert downloader.stats["failed"] == 0
        assert downloader.stats["skipped"] == 0
        assert downloader.stats["total_bytes"] == 0


class TestPDFDownloaderSession:
    """Test session creation and management."""

    def test_create_session(self, temp_dir):
        """Test session creation with retry strategy."""
        downloader = PDFDownloader(download_dir=temp_dir)
        
        assert downloader.session is not None
        assert "User-Agent" in downloader.session.headers
        assert "Accept" in downloader.session.headers

    def test_context_manager(self, temp_dir):
        """Test using downloader as context manager."""
        with PDFDownloader(download_dir=temp_dir) as downloader:
            assert downloader.session is not None
        
        # Session should be closed after context
        # Note: We can't directly test if closed, but we verify __exit__ was called

    def test_close_method(self, temp_dir):
        """Test close method."""
        downloader = PDFDownloader(download_dir=temp_dir)
        session = downloader.session
        
        with patch.object(session, 'close') as mock_close:
            downloader.close()
            mock_close.assert_called_once()


class TestFilenameGeneration:
    """Test filename generation."""

    def test_generate_filename_with_doi(self, temp_dir, sample_paper):
        """Test filename generation using DOI."""
        downloader = PDFDownloader(download_dir=temp_dir)
        filename = downloader._generate_filename(sample_paper, sample_paper.pdf_url)
        
        assert filename == "10.1234_test.2023.pdf"
        assert "/" not in filename
        assert "\\" not in filename

    def test_generate_filename_with_source_id(self, temp_dir):
        """Test filename generation using source ID when no DOI."""
        paper = Paper(
            title="Test",
            source_database="arxiv",
            source_id="2301.00001",
            pdf_url="https://example.com/paper.pdf",
        )
        downloader = PDFDownloader(download_dir=temp_dir)
        filename = downloader._generate_filename(paper, "https://example.com/paper.pdf")
        
        assert filename == "arxiv_2301.00001.pdf"

    def test_generate_filename_with_url_hash(self, temp_dir):
        """Test filename generation using URL hash as fallback."""
        paper = Paper(
            title="Test",
            source_database="test",
            pdf_url="https://example.com/paper.pdf",
        )
        downloader = PDFDownloader(download_dir=temp_dir)
        filename = downloader._generate_filename(paper, "https://example.com/paper.pdf")
        
        assert filename.startswith("paper_")
        assert filename.endswith(".pdf")
        assert len(filename) == 22  # "paper_" + 12 char hash + ".pdf"


class TestFileOperations:
    """Test file operations."""

    def test_check_existing_file_not_exists(self, temp_dir):
        """Test checking for non-existent file."""
        downloader = PDFDownloader(download_dir=temp_dir)
        filepath = Path(temp_dir) / "nonexistent.pdf"
        
        assert downloader._check_existing_file(filepath) is False

    def test_check_existing_file_exists_no_overwrite(self, temp_dir):
        """Test checking existing file without overwrite."""
        downloader = PDFDownloader(download_dir=temp_dir, overwrite=False)
        filepath = Path(temp_dir) / "existing.pdf"
        
        # Create a non-empty file
        filepath.write_text("content")
        
        assert downloader._check_existing_file(filepath) is True

    def test_check_existing_file_exists_with_overwrite(self, temp_dir):
        """Test checking existing file with overwrite enabled."""
        downloader = PDFDownloader(download_dir=temp_dir, overwrite=True)
        filepath = Path(temp_dir) / "existing.pdf"
        
        # Create a file
        filepath.write_text("content")
        
        assert downloader._check_existing_file(filepath) is False

    def test_check_existing_file_empty(self, temp_dir):
        """Test checking empty file (should be removed)."""
        downloader = PDFDownloader(download_dir=temp_dir)
        filepath = Path(temp_dir) / "empty.pdf"
        
        # Create an empty file
        filepath.touch()
        
        assert downloader._check_existing_file(filepath) is False
        assert not filepath.exists()  # Should be deleted


class TestPDFVerification:
    """Test PDF content verification."""

    def test_verify_pdf_content_valid(self, temp_dir):
        """Test verification of valid PDF content."""
        downloader = PDFDownloader(download_dir=temp_dir)
        content = b"%PDF-1.4\n%some content"
        
        assert downloader._verify_pdf_content(content) is True

    def test_verify_pdf_content_html_doctype(self, temp_dir):
        """Test rejection of HTML content with DOCTYPE."""
        downloader = PDFDownloader(download_dir=temp_dir)
        content = b"<!DOCTYPE html><html><body>Error</body></html>"
        
        assert downloader._verify_pdf_content(content) is False

    def test_verify_pdf_content_html_tag(self, temp_dir):
        """Test rejection of HTML content with html tag."""
        downloader = PDFDownloader(download_dir=temp_dir)
        content = b"<html><body>Error page</body></html>"
        
        assert downloader._verify_pdf_content(content) is False

    def test_verify_pdf_content_unknown_format(self, temp_dir):
        """Test unknown content format (not PDF, not HTML)."""
        downloader = PDFDownloader(download_dir=temp_dir)
        content = b"Some random binary content"
        
        # Should return False for non-PDF content
        assert downloader._verify_pdf_content(content) is False


class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_wait_for_rate_limit_first_request(self, temp_dir):
        """Test no waiting on first request."""
        downloader = PDFDownloader(download_dir=temp_dir, rate_limit_seconds=1.0)
        
        start_time = time.time()
        downloader._wait_for_rate_limit()
        elapsed = time.time() - start_time
        
        # Should not wait on first request
        assert elapsed < 0.1

    def test_wait_for_rate_limit_subsequent_request(self, temp_dir):
        """Test waiting on subsequent requests."""
        downloader = PDFDownloader(download_dir=temp_dir, rate_limit_seconds=0.5)
        
        # Simulate a previous download
        downloader.last_download_time = time.time()
        
        start_time = time.time()
        downloader._wait_for_rate_limit()
        elapsed = time.time() - start_time
        
        # Should wait approximately rate_limit_seconds
        assert elapsed >= 0.4  # Allow small tolerance

    def test_wait_for_rate_limit_after_delay(self, temp_dir):
        """Test no waiting if enough time has passed."""
        downloader = PDFDownloader(download_dir=temp_dir, rate_limit_seconds=0.2)
        
        # Simulate a previous download long ago
        downloader.last_download_time = time.time() - 1.0
        
        start_time = time.time()
        downloader._wait_for_rate_limit()
        elapsed = time.time() - start_time
        
        # Should not wait if enough time has passed
        assert elapsed < 0.1


class TestDownloadPaper:
    """Test downloading single papers."""

    @patch('paperseek.utils.pdf_downloader.requests.Session')
    def test_download_paper_success(self, mock_session_class, temp_dir, sample_paper, mock_response):
        """Test successful paper download."""
        # Setup mock session
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response
        
        downloader = PDFDownloader(download_dir=temp_dir, rate_limit_seconds=0)
        
        with patch.object(downloader, '_wait_for_rate_limit'):
            filepath = downloader.download_paper(sample_paper)
        
        assert filepath is not None
        assert filepath.name == "10.1234_test.2023.pdf"
        assert downloader.stats["successful"] == 1
        assert downloader.stats["attempted"] == 1

    def test_download_paper_no_pdf_url(self, temp_dir, sample_paper_no_pdf):
        """Test download when paper has no PDF URL."""
        downloader = PDFDownloader(download_dir=temp_dir)
        filepath = downloader.download_paper(sample_paper_no_pdf)
        
        assert filepath is None
        assert downloader.stats["skipped"] == 1
        assert downloader.stats["attempted"] == 1

    @patch('paperseek.utils.pdf_downloader.requests.Session')
    def test_download_paper_existing_file(self, mock_session_class, temp_dir, sample_paper):
        """Test skipping download when file exists."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        downloader = PDFDownloader(download_dir=temp_dir, overwrite=False)
        
        # Create existing file
        existing_file = Path(temp_dir) / "10.1234_test.2023.pdf"
        existing_file.write_text("%PDF content")
        
        filepath = downloader.download_paper(sample_paper)
        
        assert filepath == existing_file
        assert downloader.stats["skipped"] == 1
        # Session should not be called
        mock_session.head.assert_not_called()

    @patch('paperseek.utils.pdf_downloader.requests.Session')
    def test_download_paper_custom_filename(self, mock_session_class, temp_dir, sample_paper, mock_response):
        """Test download with custom filename."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response
        
        downloader = PDFDownloader(download_dir=temp_dir, rate_limit_seconds=0)
        
        with patch.object(downloader, '_wait_for_rate_limit'):
            filepath = downloader.download_paper(sample_paper, filename="custom_name.pdf")
        
        assert filepath is not None
        assert filepath.name == "custom_name.pdf"

    @patch('paperseek.utils.pdf_downloader.requests.Session')
    def test_download_paper_subdirectory(self, mock_session_class, temp_dir, sample_paper, mock_response):
        """Test download to subdirectory."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        mock_session.head.return_value = mock_response
        mock_session.get.return_value = mock_response
        
        downloader = PDFDownloader(download_dir=temp_dir, rate_limit_seconds=0)
        
        with patch.object(downloader, '_wait_for_rate_limit'):
            filepath = downloader.download_paper(sample_paper, subdirectory="subdir")
        
        assert filepath is not None
        assert "subdir" in str(filepath)
        assert filepath.parent.name == "subdir"

    @patch('paperseek.utils.pdf_downloader.requests.Session')
    def test_download_paper_file_too_large(self, mock_session_class, temp_dir, sample_paper):
        """Test rejection of file that's too large."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock response with large file size
        mock_head = Mock()
        mock_head.headers = {
            "Content-Type": "application/pdf",
            "Content-Length": str(100 * 1024 * 1024),  # 100 MB
        }
        mock_session.head.return_value = mock_head
        
        downloader = PDFDownloader(download_dir=temp_dir, max_file_size_mb=50)
        
        with patch.object(downloader, '_wait_for_rate_limit'):
            filepath = downloader.download_paper(sample_paper)
        
        assert filepath is None
        assert downloader.stats["failed"] == 1

    @patch('paperseek.utils.pdf_downloader.requests.Session')
    def test_download_paper_invalid_content(self, mock_session_class, temp_dir, sample_paper):
        """Test rejection of non-PDF content."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock response with HTML content
        mock_head = Mock()
        mock_head.headers = {"Content-Type": "text/html", "Content-Length": "1024"}
        
        mock_get = Mock()
        mock_get.headers = {"Content-Type": "text/html"}
        mock_get.iter_content = lambda chunk_size: [b"<html><body>Error</body></html>"]
        mock_get.raise_for_status = Mock()
        
        mock_session.head.return_value = mock_head
        mock_session.get.return_value = mock_get
        
        downloader = PDFDownloader(download_dir=temp_dir, rate_limit_seconds=0)
        
        with patch.object(downloader, '_wait_for_rate_limit'):
            filepath = downloader.download_paper(sample_paper)
        
        assert filepath is None
        assert downloader.stats["failed"] == 1

    @patch('paperseek.utils.pdf_downloader.requests.Session')
    def test_download_paper_http_error(self, mock_session_class, temp_dir, sample_paper):
        """Test handling of HTTP errors."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        # Mock 404 error
        import requests
        mock_session.head.side_effect = requests.exceptions.HTTPError("404 Not Found")
        
        downloader = PDFDownloader(download_dir=temp_dir)
        
        with patch.object(downloader, '_wait_for_rate_limit'):
            filepath = downloader.download_paper(sample_paper)
        
        assert filepath is None
        assert downloader.stats["failed"] == 1

    @patch('paperseek.utils.pdf_downloader.requests.Session')
    def test_download_paper_timeout(self, mock_session_class, temp_dir, sample_paper):
        """Test handling of timeout errors."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        import requests
        mock_session.head.side_effect = requests.exceptions.Timeout("Timeout")
        
        downloader = PDFDownloader(download_dir=temp_dir)
        
        with patch.object(downloader, '_wait_for_rate_limit'):
            filepath = downloader.download_paper(sample_paper)
        
        assert filepath is None
        assert downloader.stats["failed"] == 1

    @patch('paperseek.utils.pdf_downloader.requests.Session')
    def test_download_paper_request_exception(self, mock_session_class, temp_dir, sample_paper):
        """Test handling of general request exceptions."""
        mock_session = Mock()
        mock_session_class.return_value = mock_session
        
        import requests
        mock_session.head.side_effect = requests.exceptions.RequestException("Connection error")
        
        downloader = PDFDownloader(download_dir=temp_dir)
        
        with patch.object(downloader, '_wait_for_rate_limit'):
            filepath = downloader.download_paper(sample_paper)
        
        assert filepath is None
        assert downloader.stats["failed"] == 1


class TestDownloadMultiplePapers:
    """Test downloading multiple papers."""

    @patch('paperseek.utils.pdf_downloader.PDFDownloader.download_paper')
    def test_download_papers_success(self, mock_download, temp_dir):
        """Test downloading multiple papers."""
        mock_download.return_value = Path(temp_dir) / "paper.pdf"
        
        # Create papers with different titles to avoid dictionary key collisions
        paper1 = Paper(title="Paper 1", source_database="test", pdf_url="https://example.com/1.pdf")
        paper2 = Paper(title="Paper 2", source_database="test", pdf_url="https://example.com/2.pdf")
        paper3 = Paper(title="Paper 3", source_database="test", pdf_url="https://example.com/3.pdf")
        papers = [paper1, paper2, paper3]
        
        downloader = PDFDownloader(download_dir=temp_dir)
        results = downloader.download_papers(papers)
        
        assert len(results) == 3
        assert mock_download.call_count == 3

    @patch('paperseek.utils.pdf_downloader.PDFDownloader.download_paper')
    def test_download_papers_max_limit(self, mock_download, temp_dir):
        """Test max_downloads limit."""
        mock_download.return_value = Path(temp_dir) / "paper.pdf"
        
        # Create papers with unique titles
        papers = [
            Paper(title=f"Paper {i}", source_database="test", pdf_url=f"https://example.com/{i}.pdf")
            for i in range(10)
        ]
        downloader = PDFDownloader(download_dir=temp_dir)
        
        results = downloader.download_papers(papers, max_downloads=3)
        
        assert len(results) == 3
        assert mock_download.call_count == 3

    @patch('paperseek.utils.pdf_downloader.PDFDownloader.download_paper')
    def test_download_papers_with_failures(self, mock_download, temp_dir):
        """Test downloading papers with some failures."""
        # Create papers with unique titles
        paper1 = Paper(title="Paper 1", source_database="test", pdf_url="https://example.com/1.pdf")
        paper2 = Paper(title="Paper 2", source_database="test", pdf_url="https://example.com/2.pdf")
        paper3 = Paper(title="Paper 3", source_database="test", pdf_url="https://example.com/3.pdf")
        
        # First succeeds, second fails, third succeeds
        mock_download.side_effect = [
            Path(temp_dir) / "paper1.pdf",
            None,
            Path(temp_dir) / "paper3.pdf",
        ]
        
        papers = [paper1, paper2, paper3]
        downloader = PDFDownloader(download_dir=temp_dir)
        
        results = downloader.download_papers(papers)
        
        assert len(results) == 2  # Only successful downloads


class TestDownloadSearchResults:
    """Test downloading from search results."""

    @patch('paperseek.utils.pdf_downloader.PDFDownloader.download_papers')
    def test_download_search_results_all(self, mock_download, temp_dir, sample_paper):
        """Test downloading all papers from search results."""
        mock_download.return_value = {}
        
        search_result = SearchResult(
            papers=[sample_paper, sample_paper],
            total_results=2,
        )
        
        downloader = PDFDownloader(download_dir=temp_dir)
        downloader.download_search_results(search_result, only_open_access=False)
        
        mock_download.assert_called_once()
        call_papers = mock_download.call_args[0][0]
        assert len(call_papers) == 2

    @patch('paperseek.utils.pdf_downloader.PDFDownloader.download_papers')
    def test_download_search_results_open_access_only(self, mock_download, temp_dir):
        """Test filtering for open access papers only."""
        mock_download.return_value = {}
        
        open_paper = Paper(
            title="Open Access",
            source_database="test",
            pdf_url="https://example.com/open.pdf",
            is_open_access=True,
        )
        closed_paper = Paper(
            title="Closed Access",
            source_database="test",
            pdf_url="https://example.com/closed.pdf",
            is_open_access=False,
        )
        
        search_result = SearchResult(
            papers=[open_paper, closed_paper],
            total_results=2,
        )
        
        downloader = PDFDownloader(download_dir=temp_dir)
        downloader.download_search_results(search_result, only_open_access=True)
        
        call_papers = mock_download.call_args[0][0]
        assert len(call_papers) == 1
        assert call_papers[0].title == "Open Access"

    @patch('paperseek.utils.pdf_downloader.PDFDownloader.download_papers')
    def test_download_search_results_no_pdf_urls(self, mock_download, temp_dir, sample_paper_no_pdf):
        """Test filtering papers without PDF URLs."""
        mock_download.return_value = {}
        
        search_result = SearchResult(
            papers=[sample_paper_no_pdf, sample_paper_no_pdf],
            total_results=2,
        )
        
        downloader = PDFDownloader(download_dir=temp_dir)
        downloader.download_search_results(search_result)
        
        call_papers = mock_download.call_args[0][0]
        assert len(call_papers) == 0  # No papers with PDF URLs


class TestStatistics:
    """Test statistics tracking."""

    def test_get_statistics_initial(self, temp_dir):
        """Test initial statistics."""
        downloader = PDFDownloader(download_dir=temp_dir)
        stats = downloader.get_statistics()
        
        assert stats["attempted"] == 0.0
        assert stats["successful"] == 0.0
        assert stats["failed"] == 0.0
        assert stats["skipped"] == 0.0
        assert stats["total_bytes"] == 0.0
        assert stats["success_rate"] == 0.0
        assert stats["total_mb"] == 0.0

    def test_get_statistics_with_data(self, temp_dir):
        """Test statistics with data."""
        downloader = PDFDownloader(download_dir=temp_dir)
        
        # Manually set statistics
        downloader.stats["attempted"] = 10
        downloader.stats["successful"] = 7
        downloader.stats["failed"] = 2
        downloader.stats["skipped"] = 1
        downloader.stats["total_bytes"] = 1024 * 1024  # 1 MB
        
        stats = downloader.get_statistics()
        
        assert stats["attempted"] == 10.0
        assert stats["successful"] == 7.0
        assert stats["failed"] == 2.0
        assert stats["skipped"] == 1.0
        assert stats["success_rate"] == 70.0
        assert stats["total_mb"] == 1.0

    def test_print_statistics(self, temp_dir, capsys):
        """Test printing statistics."""
        downloader = PDFDownloader(download_dir=temp_dir)
        downloader.stats["attempted"] = 5
        downloader.stats["successful"] = 3
        
        downloader.print_statistics()
        
        captured = capsys.readouterr()
        assert "PDF Download Statistics" in captured.out
        assert "Attempted:" in captured.out
        assert "Successful:" in captured.out
