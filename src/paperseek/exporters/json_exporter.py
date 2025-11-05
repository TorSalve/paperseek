"""JSON exporter for search results."""

import json
from pathlib import Path
from typing import Any, Dict

from ..core.models import SearchResult, Paper
from ..core.exceptions import ExportError
from ..utils.logging import get_logger


class JSONExporter:
    """Export search results to JSON format."""

    def __init__(self):
        """Initialize JSON exporter."""
        self.logger = get_logger(self.__class__.__name__)

    def export(
        self, results: SearchResult, filename: str, pretty: bool = True, include_raw: bool = False
    ) -> None:
        """
        Export search results to JSON file.

        Args:
            results: SearchResult object
            filename: Output JSON file path
            pretty: Pretty-print JSON with indentation
            include_raw: Include raw API data in extra_data

        Raises:
            ExportError: If export fails
        """
        try:
            self.logger.info(f"Exporting {len(results)} results to {filename}")

            # Create output directory if needed
            Path(filename).parent.mkdir(parents=True, exist_ok=True)

            # Convert to dictionary
            data = self._results_to_dict(results, include_raw=include_raw)

            # Write to file
            with open(filename, "w", encoding="utf-8") as f:
                if pretty:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                else:
                    json.dump(data, f, ensure_ascii=False)

            self.logger.info(f"Successfully exported to {filename}")

        except Exception as e:
            raise ExportError(f"Failed to export to JSON: {e}") from e

    def export_jsonl(self, results: SearchResult, filename: str, include_raw: bool = False) -> None:
        """
        Export search results to JSONL format (one JSON object per line).

        Args:
            results: SearchResult object
            filename: Output JSONL file path
            include_raw: Include raw API data

        Raises:
            ExportError: If export fails
        """
        try:
            self.logger.info(f"Exporting {len(results)} results to JSONL: {filename}")

            Path(filename).parent.mkdir(parents=True, exist_ok=True)

            with open(filename, "w", encoding="utf-8") as f:
                for paper in results.papers:
                    paper_dict = self._paper_to_dict(paper, include_raw=include_raw)
                    f.write(json.dumps(paper_dict, ensure_ascii=False) + "\n")

            self.logger.info(f"Successfully exported to {filename}")

        except Exception as e:
            raise ExportError(f"Failed to export to JSONL: {e}") from e

    def _results_to_dict(self, results: SearchResult, include_raw: bool = False) -> Dict[str, Any]:
        """Convert SearchResult to dictionary."""
        return {
            "metadata": {
                "total_results": results.total_results,
                "databases_queried": results.databases_queried,
                "search_timestamp": results.search_timestamp.isoformat(),
                "query_info": results.query_info,
            },
            "field_statistics": {
                name: {
                    "available": stat.available_count,
                    "total": stat.total_count,
                    "percentage": stat.percentage,
                }
                for name, stat in results.field_statistics().items()
            },
            "papers": [
                self._paper_to_dict(paper, include_raw=include_raw) for paper in results.papers
            ],
        }

    def _paper_to_dict(self, paper: Paper, include_raw: bool = False) -> Dict[str, Any]:
        """Convert Paper to dictionary."""
        data = {
            "doi": paper.doi,
            "pmid": paper.pmid,
            "arxiv_id": paper.arxiv_id,
            "title": paper.title,
            "authors": [
                {"name": author.name, "affiliation": author.affiliation, "orcid": author.orcid}
                for author in paper.authors
            ],
            "abstract": paper.abstract,
            "year": paper.year,
            "publication_date": paper.publication_date,
            "venue": paper.venue,
            "journal": paper.journal,
            "conference": paper.conference,
            "volume": paper.volume,
            "issue": paper.issue,
            "pages": paper.pages,
            "publisher": paper.publisher,
            "keywords": paper.keywords,
            "citation_count": paper.citation_count,
            "reference_count": paper.reference_count,
            "url": paper.url,
            "pdf_url": paper.pdf_url,
            "is_open_access": paper.is_open_access,
            "source_database": paper.source_database,
            "source_id": paper.source_id,
            "retrieved_at": paper.retrieved_at.isoformat(),
        }

        # Add extra data if requested
        if include_raw and paper.extra_data:
            # Filter out the 'raw' field unless explicitly requested
            extra = {k: v for k, v in paper.extra_data.items() if k != "raw" or include_raw}
            data["extra_data"] = extra

        return data


class StreamingJSONLExporter:
    """
    Streaming JSONL exporter for large result sets.

    Writes results incrementally as JSONL (one JSON object per line).
    """

    def __init__(self, filename: str):
        """
        Initialize streaming exporter.

        Args:
            filename: Output JSONL file path
        """
        self.filename = filename
        self.logger = get_logger(self.__class__.__name__)

        # Create output directory
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        # Open file
        self.file = open(filename, "w", encoding="utf-8")
        self.count = 0

    def write_paper(self, paper: Paper, include_raw: bool = False) -> None:
        """
        Write a single paper to the JSONL file.

        Args:
            paper: Paper object to write
            include_raw: Include raw API data
        """
        exporter = JSONExporter()
        paper_dict = exporter._paper_to_dict(paper, include_raw=include_raw)
        self.file.write(json.dumps(paper_dict, ensure_ascii=False) + "\n")
        self.count += 1

    def write_papers(self, papers: list, include_raw: bool = False) -> None:
        """Write multiple papers."""
        for paper in papers:
            self.write_paper(paper, include_raw=include_raw)

    def close(self) -> None:
        """Close the JSONL file."""
        if self.file:
            self.file.close()
            self.logger.info(f"Wrote {self.count} papers to {self.filename}")

    def __enter__(self) -> "StreamingJSONLExporter":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
