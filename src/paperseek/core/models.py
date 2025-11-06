"""Data models for academic search results."""

from datetime import datetime
from typing import Any, Dict, List, Optional, overload
from pydantic import BaseModel, Field, ConfigDict


class Author(BaseModel):
    """Represents a paper author."""

    name: str
    affiliation: Optional[str] = None
    orcid: Optional[str] = None

    model_config = ConfigDict(frozen=True)

    def __str__(self) -> str:
        """Return the author's name as string representation."""
        return self.name


class Paper(BaseModel):
    """
    Normalized paper metadata across different databases.

    This model represents the unified schema for academic papers,
    with fields mapped from various database-specific formats.
    """

    # Core identifiers
    doi: Optional[str] = None
    pmid: Optional[str] = None
    arxiv_id: Optional[str] = None

    # Basic metadata
    title: str
    authors: List[Author] = Field(default_factory=list)
    abstract: Optional[str] = None
    year: Optional[int] = None
    publication_date: Optional[str] = None

    # Publication details
    venue: Optional[str] = None  # Conference or journal name
    journal: Optional[str] = None
    conference: Optional[str] = None
    volume: Optional[str] = None
    issue: Optional[str] = None
    pages: Optional[str] = None
    publisher: Optional[str] = None

    # Content
    keywords: List[str] = Field(default_factory=list)

    # Metrics
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None

    # URLs and access
    url: Optional[str] = None
    pdf_url: Optional[str] = None
    is_open_access: Optional[bool] = None

    # Source tracking
    source_database: str = Field(description="Database this paper was retrieved from")
    source_id: Optional[str] = Field(default=None, description="Database-specific ID")

    # Additional database-specific data
    extra_data: Dict[str, Any] = Field(
        default_factory=dict, description="Database-specific fields not in the unified schema"
    )

    # Metadata
    retrieved_at: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(frozen=False)

    def get_primary_id(self) -> Optional[str]:
        """Get the primary identifier for this paper (DOI preferred)."""
        return self.doi or self.pmid or self.arxiv_id or self.source_id

    def get_available_fields(self) -> List[str]:
        """Get list of fields that have non-None values."""
        available = []
        for field_name, field_value in self.model_dump().items():
            if field_name in ["extra_data", "retrieved_at", "source_database"]:
                continue
            if field_value is not None:
                if isinstance(field_value, (list, dict)):
                    if field_value:  # Not empty
                        available.append(field_name)
                else:
                    available.append(field_name)
        return available


class SearchFilters(BaseModel):
    """Search filter parameters."""

    # Identifier-based search
    doi: Optional[str] = None
    pmid: Optional[str] = None
    arxiv_id: Optional[str] = None

    # Text-based search
    title: Optional[str] = None
    title_exact: bool = False
    author: Optional[str] = None
    keywords: Optional[List[str]] = None
    abstract: Optional[str] = None

    # Publication venue
    venue: Optional[str] = None
    journal: Optional[str] = None
    conference: Optional[str] = None

    # Date range
    year: Optional[int] = None
    year_start: Optional[int] = None
    year_end: Optional[int] = None

    # Required fields
    required_fields: Optional[List[str]] = Field(
        default=None, description="Fields that must be present in results"
    )

    # Result limits
    max_results: int = Field(default=100, ge=1, le=10000)
    offset: int = Field(default=0, ge=0)

    # Logic
    combine_filters_with_and: bool = Field(
        default=True, description="If True, combine filters with AND logic; otherwise OR"
    )

    model_config = ConfigDict(frozen=False)

    def has_identifier_filter(self) -> bool:
        """Check if any identifier filter is set."""
        return any([self.doi, self.pmid, self.arxiv_id])

    def get_year_range(self) -> Optional[tuple]:
        """Get the year range as a tuple."""
        if self.year:
            return (self.year, self.year)
        if self.year_start or self.year_end:
            return (self.year_start, self.year_end)
        return None


class FieldStatistics(BaseModel):
    """Statistics about field availability in search results."""

    field_name: str
    available_count: int
    total_count: int
    percentage: float

    def __str__(self) -> str:
        return (
            f"{self.field_name}: {self.available_count}/{self.total_count} ({self.percentage:.1f}%)"
        )

    model_config = ConfigDict(frozen=True)


class SearchResult(BaseModel):
    """Container for search results with metadata and statistics."""

    papers: List[Paper] = Field(default_factory=list)
    total_results: int = 0
    query_info: Dict[str, Any] = Field(default_factory=dict)
    databases_queried: List[str] = Field(default_factory=list)
    search_timestamp: datetime = Field(default_factory=datetime.now)

    model_config = ConfigDict(frozen=False)

    def __len__(self) -> int:
        """Return the number of papers in the results."""
        return len(self.papers)

    @overload
    def __getitem__(self, index: int) -> Paper: ...

    @overload
    def __getitem__(self, index: slice) -> List[Paper]: ...

    def __getitem__(self, index: int | slice) -> Paper | List[Paper]:
        """Get a paper by index or a slice of papers."""
        return self.papers[index]

    def add_paper(self, paper: Paper) -> None:
        """Add a paper to the results."""
        self.papers.append(paper)
        self.total_results = len(self.papers)

    def extend(self, papers: List[Paper]) -> None:
        """Add multiple papers to the results."""
        self.papers.extend(papers)
        self.total_results = len(self.papers)

    def filter_by_required_fields(self, required_fields: List[str]) -> "SearchResult":
        """Filter results to only include papers with all required fields."""
        filtered_papers = []
        for paper in self.papers:
            available = paper.get_available_fields()
            if all(field in available for field in required_fields):
                filtered_papers.append(paper)

        result = SearchResult(
            papers=filtered_papers,
            total_results=len(filtered_papers),
            query_info=self.query_info,
            databases_queried=self.databases_queried,
            search_timestamp=self.search_timestamp,
        )
        return result

    def field_statistics(self) -> Dict[str, FieldStatistics]:
        """
        Calculate statistics about field availability across all papers.

        Returns:
            Dictionary mapping field names to FieldStatistics objects
        """
        if not self.papers:
            return {}

        # Count field availability
        field_counts: Dict[str, int] = {}
        all_fields = set()

        for paper in self.papers:
            available_fields = paper.get_available_fields()
            all_fields.update(available_fields)
            for field in available_fields:
                field_counts[field] = field_counts.get(field, 0) + 1

        total = len(self.papers)

        # Create statistics objects
        stats = {}
        for field in sorted(all_fields):
            count = field_counts.get(field, 0)
            stats[field] = FieldStatistics(
                field_name=field,
                available_count=count,
                total_count=total,
                percentage=(count / total * 100) if total > 0 else 0.0,
            )

        return stats

    def get_field_coverage_report(self) -> str:
        """Generate a human-readable field coverage report."""
        stats = self.field_statistics()
        if not stats:
            return "No results to analyze."

        lines = [f"Field Coverage Report ({len(self.papers)} papers):"]
        lines.append("-" * 60)

        for field_name in sorted(stats.keys()):
            stat = stats[field_name]
            lines.append(str(stat))

        return "\n".join(lines)

    def to_csv(
        self, filename: str, columns: Optional[List[str]] = None, include_field_stats: bool = False
    ) -> None:
        """
        Export results to CSV file.

        Args:
            filename: Path to output CSV file
            columns: List of columns to include (None = all available)
            include_field_stats: If True, create a separate stats CSV
        """
        from ..exporters.csv_exporter import CSVExporter

        exporter = CSVExporter()
        exporter.export(self, filename, columns=columns)

        if include_field_stats:
            stats_filename = filename.replace(".csv", "_field_stats.csv")
            exporter.export_field_statistics(self, stats_filename)

    def to_json(self, filename: str, pretty: bool = True) -> None:
        """Export results to JSON file."""
        from ..exporters.json_exporter import JSONExporter

        exporter = JSONExporter()
        exporter.export(self, filename, pretty=pretty)

    def to_jsonl(self, filename: str) -> None:
        """Export results to JSONL file (one JSON object per line)."""
        from ..exporters.json_exporter import JSONExporter

        exporter = JSONExporter()
        exporter.export_jsonl(self, filename)

    def to_bibtex(self, filename: str) -> None:
        """Export results to BibTeX file."""
        from ..exporters.bibtex_exporter import BibTeXExporter

        exporter = BibTeXExporter()
        exporter.export(self, filename)
