"""Base exporter class with shared functionality."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from ..core.models import SearchResult, Paper
from ..core.exceptions import ExportError
from ..utils.logging import get_logger


class BaseExporter(ABC):
    """
    Abstract base class for all exporters.

    Provides common functionality like validation, directory creation,
    and logging. Subclasses implement the actual export logic.
    """

    def __init__(self) -> None:
        """Initialize base exporter."""
        self.logger = get_logger(self.__class__.__name__)

    def export(self, results: SearchResult, filename: str, **kwargs) -> None:
        """
        Template method for export process.

        This method orchestrates the export process:
        1. Validates input
        2. Prepares output directory
        3. Calls subclass-specific export logic
        4. Logs success

        Args:
            results: SearchResult object to export
            filename: Output file path
            **kwargs: Additional parameters for specific exporters

        Raises:
            ExportError: If export fails
        """
        try:
            # Validate results
            self._validate_results(results)

            # Log start
            self.logger.info(
                f"Exporting {len(results)} results to {filename} "
                f"({self.__class__.__name__})"
            )

            # Prepare output directory
            self._prepare_output_directory(filename)

            # Subclass-specific export logic
            self._do_export(results, filename, **kwargs)

            # Log success
            self._log_success(filename, len(results))

        except ExportError:
            # Re-raise ExportError as-is
            raise
        except Exception as e:
            # Wrap other exceptions
            raise ExportError(
                f"Failed to export with {self.__class__.__name__}: {e}"
            ) from e

    @abstractmethod
    def _do_export(self, results: SearchResult, filename: str, **kwargs: Any) -> None:
        """
        Perform the actual export operation.

        Subclasses must implement this method with their specific export logic.

        Args:
            results: SearchResult object to export
            filename: Output file path
            **kwargs: Additional parameters
        """
        pass

    def _validate_results(self, results: SearchResult) -> None:
        """
        Validate search results before export.

        Args:
            results: SearchResult object to validate

        Raises:
            ExportError: If validation fails
        """
        if not results:
            raise ExportError("Cannot export: results object is None")

        if not results.papers:
            raise ExportError("Cannot export: no papers found in results")

        if not isinstance(results, SearchResult):
            raise ExportError(
                f"Invalid results type: expected SearchResult, got {type(results)}"
            )

    def _prepare_output_directory(self, filename: str) -> None:
        """
        Create output directory if it doesn't exist.

        Args:
            filename: Output file path
        """
        output_path = Path(filename)
        output_path.parent.mkdir(parents=True, exist_ok=True)

    def _log_success(self, filename: str, count: int) -> None:
        """
        Log successful export.

        Args:
            filename: Output file path
            count: Number of papers exported
        """
        self.logger.info(
            f"Successfully exported {count} papers to {filename}"
        )

    def _get_output_path(self, filename: str) -> Path:
        """
        Get Path object for output file.

        Args:
            filename: Output file path

        Returns:
            Path object
        """
        return Path(filename)


class StreamingExporter(ABC):
    """
    Abstract base class for streaming exporters.

    Streaming exporters write results incrementally, which is useful
    for large result sets that don't fit in memory.
    """

    def __init__(self) -> None:
        """Initialize streaming exporter."""
        self.logger = get_logger(self.__class__.__name__)
        self._file_handle: Optional[Any] = None
        self._filename: Optional[str] = None
        self._count: int = 0

    def __enter__(self) -> "StreamingExporter":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Context manager exit."""
        self.close()

    def open(self, filename: str, **kwargs: Any) -> None:
        """
        Open output file for streaming export.

        Args:
            filename: Output file path
            **kwargs: Additional parameters for specific exporters

        Raises:
            ExportError: If file cannot be opened
        """
        try:
            self.logger.info(
                f"Opening {filename} for streaming export ({self.__class__.__name__})"
            )

            # Prepare directory
            Path(filename).parent.mkdir(parents=True, exist_ok=True)

            # Store filename
            self._filename = filename

            # Subclass-specific open logic
            self._do_open(filename, **kwargs)

        except Exception as e:
            raise ExportError(
                f"Failed to open file for streaming export: {e}"
            ) from e

    def write_paper(self, paper: Paper) -> None:
        """
        Write a single paper to the output file.

        Args:
            paper: Paper object to write

        Raises:
            ExportError: If write fails
        """
        if not self._file_handle:
            raise ExportError("Cannot write: file not opened. Call open() first.")

        try:
            self._do_write_paper(paper)
            self._count += 1
        except Exception as e:
            raise ExportError(f"Failed to write paper: {e}") from e

    def close(self) -> None:
        """
        Close the output file.

        Raises:
            ExportError: If close fails
        """
        if self._file_handle:
            try:
                self._do_close()
                self.logger.info(
                    f"Successfully exported {self._count} papers to {self._filename}"
                )
            except Exception as e:
                raise ExportError(f"Failed to close file: {e}") from e
            finally:
                self._file_handle = None
                self._count = 0

    @abstractmethod
    def _do_open(self, filename: str, **kwargs: Any) -> None:
        """
        Subclass-specific file opening logic.

        Args:
            filename: Output file path
            **kwargs: Additional parameters
        """
        pass

    @abstractmethod
    def _do_write_paper(self, paper: Paper) -> None:
        """
        Subclass-specific paper writing logic.

        Args:
            paper: Paper object to write
        """
        pass

    @abstractmethod
    def _do_close(self) -> None:
        """Subclass-specific file closing logic."""
        pass
