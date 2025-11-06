"""
PDF downloader utility for open access papers.

This module provides functionality to download PDFs from academic papers
with polite, conservative rate limiting and proper error handling.
"""

import time
import hashlib
from pathlib import Path
from typing import Optional, List, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..core.models import Paper, SearchResult
from ..utils.logging import get_logger


class PDFDownloader:
    """
    Polite PDF downloader for academic papers.

    Features:
    - Conservative rate limiting (1 download per 3 seconds by default)
    - Respects HTTP headers and content types
    - Proper User-Agent headers
    - Timeout handling
    - File size limits
    - Resume capability
    - Progress tracking
    - Duplicate detection
    """

    def __init__(
        self,
        download_dir: str = "./downloads",
        rate_limit_seconds: float = 3.0,
        timeout: int = 60,
        max_file_size_mb: int = 50,
        user_agent: str = "AcademicSearchUnified-PDFDownloader/0.1.0",
        email: Optional[str] = None,
        overwrite: bool = False,
        verify_ssl: bool = True,
    ):
        """
        Initialize PDF downloader.

        Args:
            download_dir: Directory to save PDFs
            rate_limit_seconds: Minimum seconds between downloads (default: 3.0)
            timeout: Request timeout in seconds
            max_file_size_mb: Maximum file size to download in MB
            user_agent: User-Agent string
            email: Email for polite requests
            overwrite: Whether to overwrite existing files
            verify_ssl: Whether to verify SSL certificates
        """
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)

        self.rate_limit_seconds = rate_limit_seconds
        self.timeout = timeout
        self.max_file_size_bytes = max_file_size_mb * 1024 * 1024
        self.overwrite = overwrite
        self.verify_ssl = verify_ssl

        self.logger = get_logger(self.__class__.__name__)

        # Build User-Agent with email if provided
        if email:
            self.user_agent = f"{user_agent} (mailto:{email})"
        else:
            self.user_agent = user_agent

        # Track last download time for rate limiting
        self.last_download_time = 0.0

        # Initialize session with retry logic
        self.session = self._create_session()

        # Statistics
        self.stats = {
            "attempted": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_bytes": 0,
        }

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry configuration."""
        session = requests.Session()

        # Configure retries for connection errors only (not for 404, etc.)
        retry_strategy = Retry(
            total=3,
            backoff_factor=2,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "application/pdf,application/octet-stream,*/*",
            }
        )

        return session

    def _wait_for_rate_limit(self) -> None:
        """Wait if needed to respect rate limiting."""
        if self.last_download_time > 0:
            elapsed = time.time() - self.last_download_time
            if elapsed < self.rate_limit_seconds:
                wait_time = self.rate_limit_seconds - elapsed
                self.logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)

    def _generate_filename(self, paper: Paper, url: str) -> str:
        """
        Generate a safe filename for the PDF.

        Args:
            paper: Paper object
            url: PDF URL

        Returns:
            Safe filename
        """
        # Try to use DOI as primary identifier
        if paper.doi:
            # Replace / with _ for filesystem compatibility
            safe_doi = paper.doi.replace("/", "_").replace("\\", "_")
            return f"{safe_doi}.pdf"

        # Fallback to paper ID
        if paper.source_id:
            safe_id = str(paper.source_id).replace("/", "_").replace("\\", "_")
            return f"{paper.source_database}_{safe_id}.pdf"

        # Fallback to hash of URL
        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        return f"paper_{url_hash}.pdf"

    def _check_existing_file(self, filepath: Path) -> bool:
        """
        Check if file already exists and is valid.

        Args:
            filepath: Path to check

        Returns:
            True if file exists and is valid
        """
        if not filepath.exists():
            return False

        if self.overwrite:
            return False

        # Check if file is not empty
        if filepath.stat().st_size == 0:
            self.logger.warning(f"Removing empty file: {filepath}")
            filepath.unlink()
            return False

        return True

    def _verify_pdf_content(self, content: bytes) -> bool:
        """
        Verify that content is actually a PDF.

        Args:
            content: File content

        Returns:
            True if content appears to be a PDF
        """
        # Check PDF magic number
        if content.startswith(b"%PDF"):
            return True

        # Check for common non-PDF responses
        if content.startswith(b"<!DOCTYPE") or content.startswith(b"<html"):
            self.logger.warning("Response is HTML, not PDF")
            return False

        return False

    def download_paper(
        self,
        paper: Paper,
        filename: Optional[str] = None,
        subdirectory: Optional[str] = None,
    ) -> Optional[Path]:
        """
        Download PDF for a single paper.

        Args:
            paper: Paper object with pdf_url
            filename: Optional custom filename
            subdirectory: Optional subdirectory within download_dir

        Returns:
            Path to downloaded file, or None if download failed
        """
        self.stats["attempted"] += 1

        # Check if paper has PDF URL
        if not paper.pdf_url:
            self.logger.debug(f"No PDF URL for paper: {paper.title[:50]}")
            self.stats["skipped"] += 1
            return None

        # Determine output directory
        output_dir = self.download_dir
        if subdirectory:
            output_dir = output_dir / subdirectory
            output_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        if not filename:
            filename = self._generate_filename(paper, paper.pdf_url)

        filepath = output_dir / filename

        # Check if file already exists
        if self._check_existing_file(filepath):
            self.logger.info(f"File already exists: {filepath}")
            self.stats["skipped"] += 1
            return filepath

        # Wait for rate limiting
        self._wait_for_rate_limit()

        try:
            self.logger.info(f"Downloading PDF: {paper.title[:50]}...")
            self.logger.debug(f"URL: {paper.pdf_url}")

            # First, do a HEAD request to check file size and content type
            head_response = self.session.head(
                paper.pdf_url,
                timeout=self.timeout,
                allow_redirects=True,
                verify=self.verify_ssl,
            )

            # Check content type
            content_type = head_response.headers.get("Content-Type", "")
            if "pdf" not in content_type.lower() and "octet-stream" not in content_type.lower():
                self.logger.warning(f"Unexpected content type: {content_type} for {paper.pdf_url}")
                # Continue anyway - some servers don't set correct content type

            # Check file size
            content_length = head_response.headers.get("Content-Length")
            if content_length:
                file_size = int(content_length)
                if file_size > self.max_file_size_bytes:
                    self.logger.warning(
                        f"File too large: {file_size / 1024 / 1024:.2f} MB "
                        f"(max: {self.max_file_size_bytes / 1024 / 1024:.2f} MB)"
                    )
                    self.stats["failed"] += 1
                    return None

            # Now download the actual file
            response = self.session.get(
                paper.pdf_url,
                timeout=self.timeout,
                stream=True,
                verify=self.verify_ssl,
            )
            response.raise_for_status()

            # Download with progress tracking
            downloaded_size = 0
            chunk_size = 8192  # 8KB chunks

            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # Check size limit during download
                        if downloaded_size > self.max_file_size_bytes:
                            self.logger.warning(
                                f"File exceeds size limit during download, stopping"
                            )
                            filepath.unlink()  # Remove partial file
                            self.stats["failed"] += 1
                            return None

            # Verify PDF content
            with open(filepath, "rb") as f:
                content_start = f.read(1024)  # Read first 1KB
                if not self._verify_pdf_content(content_start):
                    self.logger.warning(f"Downloaded file is not a valid PDF")
                    filepath.unlink()  # Remove invalid file
                    self.stats["failed"] += 1
                    return None

            # Success
            self.stats["successful"] += 1
            self.stats["total_bytes"] += downloaded_size
            self.last_download_time = time.time()

            self.logger.info(
                f"Successfully downloaded: {filepath.name} " f"({downloaded_size / 1024:.2f} KB)"
            )

            return filepath

        except requests.exceptions.HTTPError as e:
            self.logger.warning(f"HTTP error downloading {paper.pdf_url}: {e}")
            self.stats["failed"] += 1
            return None
        except requests.exceptions.Timeout:
            self.logger.warning(f"Timeout downloading {paper.pdf_url}")
            self.stats["failed"] += 1
            return None
        except requests.exceptions.RequestException as e:
            self.logger.warning(f"Error downloading {paper.pdf_url}: {e}")
            self.stats["failed"] += 1
            return None
        except Exception as e:
            self.logger.error(f"Unexpected error downloading {paper.pdf_url}: {e}")
            self.stats["failed"] += 1
            return None

    def download_papers(
        self,
        papers: List[Paper],
        subdirectory: Optional[str] = None,
        max_downloads: Optional[int] = None,
    ) -> Dict[str, Path]:
        """
        Download PDFs for multiple papers.

        Args:
            papers: List of Paper objects
            subdirectory: Optional subdirectory within download_dir
            max_downloads: Maximum number of PDFs to download

        Returns:
            Dictionary mapping paper titles to downloaded file paths
        """
        results = {}
        downloaded_count = 0

        for i, paper in enumerate(papers, 1):
            # Check max downloads limit
            if max_downloads and downloaded_count >= max_downloads:
                self.logger.info(f"Reached maximum download limit: {max_downloads}")
                break

            self.logger.info(f"Processing paper {i}/{len(papers)}")

            filepath = self.download_paper(paper, subdirectory=subdirectory)

            if filepath:
                results[paper.title] = filepath
                downloaded_count += 1

        return results

    def download_search_results(
        self,
        search_result: SearchResult,
        subdirectory: Optional[str] = None,
        max_downloads: Optional[int] = None,
        only_open_access: bool = True,
    ) -> Dict[str, Path]:
        """
        Download PDFs from search results.

        Args:
            search_result: SearchResult object
            subdirectory: Optional subdirectory within download_dir
            max_downloads: Maximum number of PDFs to download
            only_open_access: Only download papers marked as open access

        Returns:
            Dictionary mapping paper titles to downloaded file paths
        """
        # Filter papers
        papers_to_download = []

        for paper in search_result.papers:
            # Check if has PDF URL
            if not paper.pdf_url:
                continue

            # Check open access filter
            if only_open_access and not paper.is_open_access:
                continue

            papers_to_download.append(paper)

        self.logger.info(
            f"Found {len(papers_to_download)} papers with PDF URLs "
            f"out of {len(search_result.papers)} total papers"
        )

        return self.download_papers(
            papers_to_download,
            subdirectory=subdirectory,
            max_downloads=max_downloads,
        )

    def get_statistics(self) -> Dict[str, float]:
        """
        Get download statistics.

        Returns:
            Dictionary with download statistics
        """
        stats_dict: Dict[str, float] = {
            "attempted": float(self.stats["attempted"]),
            "successful": float(self.stats["successful"]),
            "failed": float(self.stats["failed"]),
            "skipped": float(self.stats["skipped"]),
            "total_bytes": float(self.stats["total_bytes"]),
        }
        stats_dict["success_rate"] = (
            stats_dict["successful"] / stats_dict["attempted"] * 100
            if stats_dict["attempted"] > 0
            else 0.0
        )
        stats_dict["total_mb"] = stats_dict["total_bytes"] / 1024 / 1024
        return stats_dict

    def print_statistics(self) -> None:
        """Print download statistics."""
        stats = self.get_statistics()

        print("\n" + "=" * 60)
        print("PDF Download Statistics")
        print("=" * 60)
        print(f"Attempted:   {stats['attempted']}")
        print(f"Successful:  {stats['successful']}")
        print(f"Failed:      {stats['failed']}")
        print(f"Skipped:     {stats['skipped']}")
        print(f"Success Rate: {stats['success_rate']:.1f}%")
        print(f"Total Size:  {stats['total_mb']:.2f} MB")
        print("=" * 60)

    def close(self) -> None:
        """Close the downloader session."""
        if self.session:
            self.session.close()

    def __enter__(self) -> "PDFDownloader":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
