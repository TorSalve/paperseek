"""Unpaywall API client implementation."""

from typing import Any, Dict, List, Optional

from ..core.base import DatabaseClient
from ..core.models import Paper, Author, SearchFilters, SearchResult
from ..core.config import DatabaseConfig
from ..core.exceptions import APIError


class UnpaywallClient(DatabaseClient):
    """
    Client for Unpaywall API.

    Unpaywall is a database of free scholarly articles. It harvests Open Access content
    from over 50,000 publishers and repositories, and makes it easy to find, track, and
    use.

    API Documentation: https://unpaywall.org/products/api

    Note: Email address required. No API key needed. Free for non-commercial use.
    Rate limit: 100,000 requests per day.
    """

    BASE_URL = "https://api.unpaywall.org/v2"

    @property
    def database_name(self) -> str:
        """Return database name."""
        return "unpaywall"

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
        Make an HTTP request with Unpaywall-specific email parameter.

        Email is required by Unpaywall API.

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
        params = params or {}

        # Add email parameter (required)
        if self.email:
            params["email"] = self.email
        else:
            raise APIError(
                "Email address is required for Unpaywall API", database=self.database_name
            )

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
        Search Unpaywall database.

        Note: Unpaywall primarily supports DOI lookup, not full-text search.
        This method will only work if a DOI is provided in filters.

        Args:
            filters: Search filters

        Returns:
            SearchResult object
        """
        self.logger.info(f"Searching Unpaywall with filters: {filters}")

        result = SearchResult(
            query_info={"filters": filters.model_dump()}, databases_queried=[self.database_name]
        )

        # Unpaywall only supports DOI lookup
        if filters.doi:
            paper = self.get_by_doi(filters.doi)
            if paper:
                result.add_paper(paper)
        else:
            self.logger.warning("Unpaywall only supports DOI-based lookup")

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
            # Clean DOI
            doi = doi.strip().replace("https://doi.org/", "").replace("http://dx.doi.org/", "")

            url = f"{self.BASE_URL}/{doi}"
            response = self._make_request(url)

            data = response.json()
            return self._normalize_paper(data)

        except APIError as e:
            if e.status_code == 404:
                self.logger.debug(f"DOI not found in Unpaywall: {doi}")
                return None
            raise

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

        if id_type.lower() == "doi":
            for doi in identifiers:
                paper = self.get_by_doi(doi)
                if paper:
                    result.add_paper(paper)
        else:
            self.logger.warning(f"Unpaywall only supports DOI lookup, not {id_type}")

        return result

    def _normalize_paper(self, raw_data: Dict[str, Any]) -> Paper:
        """
        Normalize Unpaywall data to Paper model.

        Args:
            raw_data: Raw Unpaywall API response

        Returns:
            Normalized Paper object
        """
        # Extract authors from z_authors field
        authors = []
        z_authors = raw_data.get("z_authors", [])
        if z_authors:
            for author_data in z_authors:
                if isinstance(author_data, dict):
                    name = author_data.get("family", "")
                    given = author_data.get("given", "")
                    full_name = f"{given} {name}".strip() or "Unknown"
                    authors.append(Author(name=full_name))
                else:
                    authors.append(Author(name=str(author_data)))

        # Extract year
        year = raw_data.get("year")
        if year:
            try:
                year = int(year)
            except (ValueError, TypeError):
                year = None

        # Extract DOI
        doi = raw_data.get("doi")

        # Extract best OA location
        best_oa_location = raw_data.get("best_oa_location", {})
        pdf_url = best_oa_location.get("url_for_pdf") if best_oa_location else None
        landing_page_url = best_oa_location.get("url") if best_oa_location else None

        # Determine if open access
        is_oa = raw_data.get("is_oa", False)

        # Extract journal
        journal = raw_data.get("journal_name")

        # Extract publisher
        publisher = raw_data.get("publisher")

        # Extract title
        title = raw_data.get("title", "Unknown")

        # Get OA status
        oa_status = raw_data.get("oa_status")

        return Paper(
            doi=doi,
            title=title,
            authors=authors,
            year=year,
            venue=journal,
            journal=journal,
            url=landing_page_url or f"https://doi.org/{doi}" if doi else None,
            pdf_url=pdf_url,
            is_open_access=is_oa,
            source_database=self.database_name,
            source_id=doi,
            extra_data={
                "oa_status": oa_status,
                "publisher": publisher,
                "genre": raw_data.get("genre"),
                "best_oa_location": best_oa_location,
                "oa_locations": raw_data.get("oa_locations", []),
                "raw": raw_data,
            },
        )

    def get_supported_fields(self) -> List[str]:
        """Get fields typically provided by Unpaywall."""
        return [
            "doi",
            "title",
            "authors",
            "year",
            "journal",
            "url",
            "pdf_url",
            "is_open_access",
        ]
