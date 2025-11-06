"""CSV exporter for search results."""

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from ..core.models import SearchResult, Paper
from ..core.exceptions import ExportError
from ..utils.logging import get_logger


class CSVExporter:
    """Export search results to CSV format."""

    def __init__(self):
        """Initialize CSV exporter."""
        self.logger = get_logger(self.__class__.__name__)

    def export(
        self,
        results: SearchResult,
        filename: str,
        columns: Optional[List[str]] = None,
        include_metadata: bool = True,
    ) -> None:
        """
        Export search results to CSV file.

        Args:
            results: SearchResult object
            filename: Output CSV file path
            columns: List of columns to include (None = all available)
            include_metadata: Include metadata row at top

        Raises:
            ExportError: If export fails
        """
        try:
            self.logger.info(f"Exporting {len(results)} results to {filename}")

            # Create output directory if needed
            Path(filename).parent.mkdir(parents=True, exist_ok=True)

            # Determine columns
            if columns is None:
                columns = self._get_default_columns(results)

            with open(filename, "w", newline="", encoding="utf-8") as f:
                # Write metadata if requested
                if include_metadata:
                    self._write_metadata(f, results)

                # Write CSV data
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()

                for paper in results.papers:
                    row = self._paper_to_row(paper, columns)
                    writer.writerow(row)

            self.logger.info(f"Successfully exported to {filename}")

        except Exception as e:
            raise ExportError(f"Failed to export to CSV: {e}") from e

    def export_field_statistics(self, results: SearchResult, filename: str) -> None:
        """
        Export field availability statistics to CSV.

        Args:
            results: SearchResult object
            filename: Output CSV file path
        """
        try:
            self.logger.info(f"Exporting field statistics to {filename}")

            Path(filename).parent.mkdir(parents=True, exist_ok=True)

            stats = results.field_statistics()

            with open(filename, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Field", "Available", "Total", "Percentage"])

                for field_name in sorted(stats.keys()):
                    stat = stats[field_name]
                    writer.writerow(
                        [
                            stat.field_name,
                            stat.available_count,
                            stat.total_count,
                            f"{stat.percentage:.2f}%",
                        ]
                    )

            self.logger.info(f"Successfully exported field statistics to {filename}")

        except Exception as e:
            raise ExportError(f"Failed to export field statistics: {e}") from e

    def _write_metadata(self, file_obj, results: SearchResult) -> None:
        """Write metadata row."""
        writer = csv.writer(file_obj)
        writer.writerow(["# Academic Search Results Metadata"])
        writer.writerow(["# Export Date:", datetime.now().isoformat()])
        writer.writerow(["# Total Results:", len(results)])
        writer.writerow(["# Databases:", ", ".join(results.databases_queried)])
        writer.writerow(["# Search Timestamp:", results.search_timestamp.isoformat()])
        writer.writerow([])  # Empty row separator

    def _get_default_columns(self, results: SearchResult) -> List[str]:
        """Determine default columns based on available data."""
        columns = [
            "title",
            "authors",
            "year",
            "venue",
            "journal",
            "conference",
            "doi",
            "abstract",
            "citation_count",
            "keywords",
            "url",
            "source_database",
        ]
        return columns

    def _paper_to_row(self, paper: Paper, columns: List[str]) -> dict:
        """Convert Paper object to CSV row dictionary."""
        row = {}

        for col in columns:
            if col == "authors":
                # Format authors as "Name1; Name2; Name3"
                row[col] = "; ".join(author.name for author in paper.authors)
            elif col == "keywords":
                # Format keywords as comma-separated
                row[col] = ", ".join(paper.keywords) if paper.keywords else ""
            elif hasattr(paper, col):
                value = getattr(paper, col)
                # Convert None to empty string
                row[col] = value if value is not None else ""
            else:
                row[col] = ""

        return row


class StreamingCSVExporter:
    """
    Streaming CSV exporter for large result sets.

    Writes results incrementally to handle datasets that don't fit in memory.
    """

    def __init__(self, filename: str, columns: Optional[List[str]] = None):
        """
        Initialize streaming exporter.

        Args:
            filename: Output CSV file path
            columns: List of columns to include
        """
        self.filename = filename
        self.columns = columns or self._get_default_columns()
        self.logger = get_logger(self.__class__.__name__)

        # Create output directory
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        # Open file and write header
        self.file = open(filename, "w", newline="", encoding="utf-8")
        self.writer = csv.DictWriter(self.file, fieldnames=self.columns)
        self.writer.writeheader()

        self.count = 0

    def _get_default_columns(self) -> List[str]:
        """Get default column list."""
        return [
            "title",
            "authors",
            "year",
            "venue",
            "journal",
            "conference",
            "doi",
            "abstract",
            "citation_count",
            "keywords",
            "url",
            "source_database",
        ]

    def write_paper(self, paper: Paper) -> None:
        """
        Write a single paper to the CSV.

        Args:
            paper: Paper object to write
        """
        row = {}
        for col in self.columns:
            if col == "authors":
                row[col] = "; ".join(author.name for author in paper.authors)
            elif col == "keywords":
                row[col] = ", ".join(paper.keywords) if paper.keywords else ""
            elif hasattr(paper, col):
                value = getattr(paper, col)
                row[col] = value if value is not None else ""
            else:
                row[col] = ""

        self.writer.writerow(row)
        self.count += 1

    def write_papers(self, papers: List[Paper]) -> None:
        """Write multiple papers."""
        for paper in papers:
            self.write_paper(paper)

    def close(self) -> None:
        """Close the CSV file."""
        if self.file:
            self.file.close()
            self.logger.info(f"Wrote {self.count} papers to {self.filename}")

    def __enter__(self) -> "StreamingCSVExporter":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
