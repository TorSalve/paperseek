"""CORE API client implementation."""

from typing import Any, Dict, List, Optional

from ..core.base import DatabaseClient
from ..core.models import Paper, Author, SearchFilters, SearchResult
from ..core.config import DatabaseConfig
from ..core.exceptions import APIError


class COREClient(DatabaseClient):
    """
    Client for CORE API v3.

    CORE is the world's largest collection of open access research papers,
    aggregating millions of articles from repositories and journals worldwide.

    API Documentation: https://core.ac.uk/documentation/api

    Note: API key required. Free tier: 10,000 requests/day.
    Register at: https://core.ac.uk/services/api
    """

    BASE_URL = "https://api.core.ac.uk/v3"

    @property
    def database_name(self) -> str:
        """Return database name."""
        return "core"

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ):
        """
        Make an HTTP request with CORE-specific authentication.

        API key is passed as Bearer token in Authorization header.

        Args:
            url: Request URL
            method: HTTP method
            params: Query parameters
            headers: Additional headers
            json_data: JSON data for POST requests
            timeout: Request timeout

        Returns:
            Response object
        """
        headers = headers or {}

        # Add API key to headers
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        else:
            raise APIError("CORE API key is required", database=self.database_name)

        # Call parent's _make_request
        return super()._make_request(
            url=url,
            method=method,
            params=params,
            headers=headers,
            json_data=json_data,
            timeout=timeout,
        )

    def search(self, filters: SearchFilters) -> SearchResult:
        """
        Search CORE database.

        Args:
            filters: Search filters

        Returns:
            SearchResult object
        """
        self.logger.info(f"Searching CORE with filters: {filters}")

        # Build search query
        query_parts = []

        if filters.doi:
            query_parts.append(f'doi:"{filters.doi}"')
        if filters.title:
            query_parts.append(f'title:"{filters.title}"')
        if filters.author:
            query_parts.append(f'authors:"{filters.author}"')

        # Year filters
        if filters.year:
            query_parts.append(f"yearPublished:{filters.year}")
        elif filters.year_start or filters.year_end:
            if filters.year_start and filters.year_end:
                query_parts.append(f"yearPublished:[{filters.year_start} TO {filters.year_end}]")
            elif filters.year_start:
                query_parts.append(f"yearPublished:[{filters.year_start} TO *]")
            else:
                query_parts.append(f"yearPublished:[* TO {filters.year_end}]")

        if not query_parts:
            query_parts.append("*")  # Match all

        query = " AND ".join(query_parts)

        # Build request body (CORE uses POST for search)
        request_body = {
            "q": query,
            "limit": min(filters.max_results, 100),  # Max 100 per request
            "offset": filters.offset,
        }

        # Make request
        url = f"{self.BASE_URL}/search/works"
        response = self._make_request(url, method="POST", json_data=request_body)

        data = response.json()

        # Parse results
        result = SearchResult(
            query_info={"filters": filters.model_dump(), "query": query},
            databases_queried=[self.database_name],
        )

        results = data.get("results", [])
        for item in results:
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
            filters = SearchFilters(doi=doi, max_results=1)
            result = self.search(filters)
            return result.papers[0] if result.papers else None
        except Exception as e:
            self.logger.warning(f"Failed to get paper by DOI: {e}")
            return None

    def get_by_identifier(self, identifier: str, id_type: str) -> Optional[Paper]:
        """Get paper by identifier."""
        if id_type.lower() == "doi":
            return self.get_by_doi(identifier)
        elif id_type.lower() == "core":
            try:
                # Get by CORE ID
                url = f"{self.BASE_URL}/works/{identifier}"
                response = self._make_request(url)
                data = response.json()
                return self._normalize_paper(data)
            except APIError:
                return None
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

    def _normalize_paper(self, raw_data: Dict[str, Any]) -> Paper:
        """
        Normalize CORE data to Paper model.

        Args:
            raw_data: Raw CORE API response

        Returns:
            Normalized Paper object
        """
        # Extract authors
        authors = []
        for author_data in raw_data.get("authors", []):
            if isinstance(author_data, dict):
                name = author_data.get("name", "Unknown")
            else:
                name = str(author_data)
            authors.append(Author(name=name))

        # Extract year
        year = raw_data.get("yearPublished")
        if year:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None

        # Extract DOI
        doi = raw_data.get("doi")

        # Extract abstract
        abstract = raw_data.get("abstract")

        # Extract download URL (PDF)
        pdf_url = raw_data.get("downloadUrl")

        # Extract publisher/journal
        publisher = raw_data.get("publisher")
        journal = raw_data.get("journals", [])
        if journal and isinstance(journal, list):
            journal = journal[0] if journal else None

        # Extract subjects/topics as keywords
        keywords = raw_data.get("topics", [])
        if not keywords:
            keywords = raw_data.get("subjects", [])

        return Paper(
            doi=doi,
            title=raw_data.get("title", "Unknown"),
            authors=authors,
            abstract=abstract,
            year=year,
            publication_date=raw_data.get("publishedDate"),
            venue=journal or publisher,
            journal=journal,
            keywords=keywords,
            url=raw_data.get("links", [{}])[0].get("url") if raw_data.get("links") else None,
            pdf_url=pdf_url,
            is_open_access=True,  # CORE only indexes open access content
            source_database=self.database_name,
            source_id=str(raw_data.get("id")),
            extra_data={
                "core_id": raw_data.get("id"),
                "publisher": publisher,
                "language": raw_data.get("language"),
                "raw": raw_data,
            },
        )

    def get_supported_fields(self) -> List[str]:
        """Get fields typically provided by CORE."""
        return [
            "doi",
            "title",
            "authors",
            "abstract",
            "year",
            "publication_date",
            "venue",
            "journal",
            "keywords",
            "url",
            "pdf_url",
            "is_open_access",
        ]
