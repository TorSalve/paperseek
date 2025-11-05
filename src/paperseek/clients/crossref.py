"""CrossRef API client implementation."""

from typing import Any, Dict, List, Optional
from urllib.parse import quote

from ..core.base import DatabaseClient
from ..core.models import Paper, Author, SearchFilters, SearchResult
from ..core.config import DatabaseConfig
from ..core.exceptions import APIError


class CrossRefClient(DatabaseClient):
    """
    Client for CrossRef API.

    CrossRef provides metadata for scholarly works with DOIs.
    API Documentation: https://api.crossref.org
    """

    BASE_URL = "https://api.crossref.org"

    def __init__(
        self,
        config: DatabaseConfig,
        email: Optional[str] = None,
        user_agent: str = "AcademicSearchUnified/0.1.0",
    ):
        """Initialize CrossRef client."""
        super().__init__(config, email, user_agent)

        # Add email to requests if provided (polite pool access)
        if email:
            self.session.params = {"mailto": email}  # type: ignore

    @property
    def database_name(self) -> str:
        """Return database name."""
        return "crossref"

    def search(self, filters: SearchFilters) -> SearchResult:
        """
        Search CrossRef database.

        Args:
            filters: Search filters

        Returns:
            SearchResult object
        """
        self.logger.info(f"Searching CrossRef with filters: {filters}")

        # Build query
        query_parts = []

        if filters.title:
            query_parts.append(f"title:{filters.title}")
        if filters.author:
            query_parts.append(f"author:{filters.author}")
        if filters.doi:
            return self._search_by_doi(filters.doi, filters)

        query = " ".join(query_parts) if query_parts else None

        # Build request params
        params: Dict[str, Any] = {
            "rows": min(filters.max_results, 1000),  # CrossRef max
            "offset": filters.offset,
        }

        if query:
            params["query"] = query

        # Add filters
        filter_parts = []

        if filters.year:
            filter_parts.append(f"from-pub-date:{filters.year}")
            filter_parts.append(f"until-pub-date:{filters.year}")
        elif filters.year_start or filters.year_end:
            if filters.year_start:
                filter_parts.append(f"from-pub-date:{filters.year_start}")
            if filters.year_end:
                filter_parts.append(f"until-pub-date:{filters.year_end}")

        if filter_parts:
            params["filter"] = ",".join(filter_parts)

        # Make request
        url = f"{self.BASE_URL}/works"
        response = self._make_request(url, params=params)

        data = response.json()

        # Parse results
        result = SearchResult(
            query_info={"filters": filters.model_dump(), "query": query},
            databases_queried=[self.database_name],
        )

        items = data.get("message", {}).get("items", [])
        for item in items:
            try:
                paper = self._normalize_paper(item)
                result.add_paper(paper)
            except Exception as e:
                self.logger.warning(f"Failed to normalize paper: {e}")
                continue

        return result

    def get_by_doi(self, doi: str) -> Optional[Paper]:
        """
        Get paper by DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Paper object or None
        """
        try:
            url = f"{self.BASE_URL}/works/{quote(doi, safe='')}"
            response = self._make_request(url)
            data = response.json()
            return self._normalize_paper(data.get("message", {}))
        except APIError:
            return None

    def get_by_identifier(self, identifier: str, id_type: str) -> Optional[Paper]:
        """Get paper by identifier."""
        if id_type.lower() == "doi":
            return self.get_by_doi(identifier)
        return None

    def batch_lookup(self, identifiers: List[str], id_type: str) -> SearchResult:
        """Look up multiple papers."""
        result = SearchResult(
            query_info={"identifiers": identifiers, "id_type": id_type},
            databases_queried=[self.database_name],
        )

        for identifier in identifiers:
            paper = self.get_by_identifier(identifier, id_type)
            if paper:
                result.add_paper(paper)

        return result

    def _search_by_doi(self, doi: str, filters: SearchFilters) -> SearchResult:
        """Search by DOI specifically."""
        result = SearchResult(query_info={"doi": doi}, databases_queried=[self.database_name])

        paper = self.get_by_doi(doi)
        if paper:
            result.add_paper(paper)

        return result

    def _normalize_paper(self, raw_data: Dict[str, Any]) -> Paper:
        """
        Normalize CrossRef data to Paper model.

        Args:
            raw_data: Raw CrossRef API response

        Returns:
            Normalized Paper object
        """
        # Extract authors
        authors = []
        for author_data in raw_data.get("author", []):
            name_parts = []
            if "given" in author_data:
                name_parts.append(author_data["given"])
            if "family" in author_data:
                name_parts.append(author_data["family"])

            name = " ".join(name_parts) if name_parts else "Unknown"

            authors.append(
                Author(
                    name=name,
                    affiliation=(
                        author_data.get("affiliation", [{}])[0].get("name")
                        if author_data.get("affiliation")
                        else None
                    ),
                    orcid=author_data.get("ORCID"),
                )
            )

        # Extract year
        year = None
        pub_date = raw_data.get("published-print") or raw_data.get("published-online")
        if pub_date and "date-parts" in pub_date:
            date_parts = pub_date["date-parts"][0]
            if date_parts:
                year = date_parts[0]

        # Extract venue/journal
        container_titles = raw_data.get("container-title", [])
        venue = container_titles[0] if container_titles else None

        # Determine if conference or journal
        conference = None
        journal = None
        paper_type = raw_data.get("type", "")
        if "proceedings" in paper_type:
            conference = venue
        else:
            journal = venue

        # Extract abstract
        abstract = raw_data.get("abstract")

        return Paper(
            doi=raw_data.get("DOI"),
            title=raw_data.get("title", ["Unknown"])[0],
            authors=authors,
            abstract=abstract,
            year=year,
            venue=venue,
            journal=journal,
            conference=conference,
            volume=raw_data.get("volume"),
            issue=raw_data.get("issue"),
            pages=raw_data.get("page"),
            publisher=raw_data.get("publisher"),
            citation_count=raw_data.get("is-referenced-by-count"),
            reference_count=raw_data.get("references-count"),
            url=raw_data.get("URL"),
            is_open_access=any(
                link.get("content-type") == "application/pdf" for link in raw_data.get("link", [])
            ),
            source_database=self.database_name,
            source_id=raw_data.get("DOI"),
            extra_data={
                "type": raw_data.get("type"),
                "issn": raw_data.get("ISSN"),
                "subject": raw_data.get("subject"),
                "raw": raw_data,
            },
        )

    def get_supported_fields(self) -> List[str]:
        """Get fields typically provided by CrossRef."""
        return [
            "doi",
            "title",
            "authors",
            "year",
            "venue",
            "journal",
            "conference",
            "volume",
            "issue",
            "pages",
            "publisher",
            "citation_count",
            "reference_count",
            "url",
            "is_open_access",
        ]
