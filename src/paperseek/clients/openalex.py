"""OpenAlex API client implementation."""

from typing import Any, Dict, List, Optional

from ..core.base import DatabaseClient
from ..core.models import Paper, Author, SearchFilters, SearchResult
from ..core.exceptions import APIError
from ..utils.normalization import (
    TextNormalizer,
    DateNormalizer,
    AuthorNormalizer,
    IdentifierNormalizer,
    URLNormalizer,
    VenueNormalizer,
)


class OpenAlexClient(DatabaseClient):
    """
    Client for OpenAlex API.

    OpenAlex is a fully open catalog of scholarly papers, authors, and institutions.
    API Documentation: https://docs.openalex.org

    Polite Pool:
    - Add email via mailto parameter or User-Agent header for better rate limits (~10 req/sec)
    - Premium users can use API key (passed as api_key parameter) for higher limits and special filters
    """

    BASE_URL = "https://api.openalex.org"

    @property
    def database_name(self) -> str:
        """Return database name."""
        return "openalex"

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
        Make an HTTP request with OpenAlex-specific polite pool support.

        Adds mailto parameter if email is provided for polite pool access.
        Adds api_key parameter if provided (for Premium users).

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

        # Add mailto parameter for polite pool if email is provided
        if self.email:
            params["mailto"] = self.email

        # Add API key parameter if provided (for Premium users)
        if self.config.api_key:
            params["api_key"] = self.config.api_key
            self.logger.debug("Using OpenAlex API key for Premium access")

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
        Search OpenAlex database.

        Args:
            filters: Search filters

        Returns:
            SearchResult object
        """
        self.logger.info(f"Searching OpenAlex with filters: {filters}")

        # Build filter string
        filter_parts = []

        if filters.doi:
            filter_parts.append(f"doi:{filters.doi}")
        if filters.title:
            filter_parts.append(f"title.search:{filters.title}")
        if filters.author:
            filter_parts.append(f"author.search:{filters.author}")

        # Year filters
        if filters.year:
            filter_parts.append(f"publication_year:{filters.year}")
        elif filters.year_start or filters.year_end:
            if filters.year_start:
                filter_parts.append(f"from_publication_date:{filters.year_start}-01-01")
            if filters.year_end:
                filter_parts.append(f"to_publication_date:{filters.year_end}-12-31")

        # Venue filters
        if filters.venue:
            filter_parts.append(f"host_venue.display_name.search:{filters.venue}")

        # Build params
        params: Dict[str, Any] = {
            "per-page": min(filters.max_results, 200),  # OpenAlex max per page
            "page": (filters.offset // 200) + 1,
        }

        if filter_parts:
            params["filter"] = ",".join(filter_parts)

        # Make request
        url = f"{self.BASE_URL}/works"
        response = self._make_request(url, params=params)

        data = response.json()

        # Parse results
        result = SearchResult(
            query_info={"filters": filters.model_dump()}, databases_queried=[self.database_name]
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
            # OpenAlex uses DOI URLs as IDs
            url = f"{self.BASE_URL}/works/https://doi.org/{doi}"
            response = self._make_request(url)
            data = response.json()
            return self._normalize_paper(data)
        except APIError:
            return None

    def get_by_identifier(self, identifier: str, id_type: str) -> Optional[Paper]:
        """Get paper by identifier."""
        if id_type.lower() == "doi":
            return self.get_by_doi(identifier)
        elif id_type.lower() == "openalex":
            try:
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
        Normalize OpenAlex data to Paper model.

        Args:
            raw_data: Raw OpenAlex API response

        Returns:
            Normalized Paper object
        """
        # Extract authors
        authors = []
        for authorship in raw_data.get("authorships", []):
            author_info = authorship.get("author", {})
            name = author_info.get("display_name", "Unknown")

            # Get affiliation
            institutions = authorship.get("institutions", [])
            affiliation = institutions[0].get("display_name") if institutions else None

            # Get ORCID
            orcid = author_info.get("orcid")
            if orcid:
                orcid = orcid.replace("https://orcid.org/", "")

            authors.append(Author(name=name, affiliation=affiliation, orcid=orcid))

        # Extract year
        year = raw_data.get("publication_year")

        # Extract venue information
        host_venue = raw_data.get("host_venue") or raw_data.get("primary_location", {}).get(
            "source", {}
        )
        venue = host_venue.get("display_name") if host_venue else None

        # Determine if conference or journal
        venue_type = host_venue.get("type") if host_venue else None
        conference = None
        journal = None
        if venue_type == "conference":
            conference = venue
        elif venue_type == "journal":
            journal = venue
        else:
            # Default to journal if unclear
            journal = venue

        # Extract abstract (inverted index format)
        abstract = None
        abstract_inverted = raw_data.get("abstract_inverted_index")
        if abstract_inverted:
            abstract = self._reconstruct_abstract(abstract_inverted)

        # Extract DOI
        doi = raw_data.get("doi")
        if doi:
            doi = doi.replace("https://doi.org/", "")

        # Get PDF URL
        pdf_url = None
        if raw_data.get("open_access", {}).get("oa_url"):
            pdf_url = raw_data["open_access"]["oa_url"]

        # Extract keywords (concepts)
        keywords = [
            concept.get("display_name")
            for concept in raw_data.get("concepts", [])
            if concept.get("score", 0) > 0.3  # Only high-confidence concepts
        ]

        return Paper(
            doi=doi,
            title=raw_data.get("display_name") or raw_data.get("title", "Unknown"),
            authors=authors,
            abstract=abstract,
            year=year,
            publication_date=raw_data.get("publication_date"),
            venue=venue,
            journal=journal,
            conference=conference,
            keywords=keywords,
            citation_count=raw_data.get("cited_by_count"),
            reference_count=len(raw_data.get("referenced_works", [])),
            url=raw_data.get("doi"),
            pdf_url=pdf_url,
            is_open_access=raw_data.get("open_access", {}).get("is_oa", False),
            source_database=self.database_name,
            source_id=raw_data.get("id"),
            extra_data={
                "openalex_id": raw_data.get("id"),
                "type": raw_data.get("type"),
                "biblio": raw_data.get("biblio"),
                "raw": raw_data,
            },
        )

    def _reconstruct_abstract(self, inverted_index: Dict[str, List[int]]) -> str:
        """
        Reconstruct abstract text from OpenAlex's inverted index format.

        Args:
            inverted_index: Dictionary mapping words to position indices

        Returns:
            Reconstructed abstract text
        """
        # Create list of (position, word) tuples
        word_positions = []
        for word, positions in inverted_index.items():
            for pos in positions:
                word_positions.append((pos, word))

        # Sort by position and join
        word_positions.sort(key=lambda x: x[0])
        return " ".join(word for _, word in word_positions)

    def get_supported_fields(self) -> List[str]:
        """Get fields typically provided by OpenAlex."""
        return [
            "doi",
            "title",
            "authors",
            "abstract",
            "year",
            "publication_date",
            "venue",
            "journal",
            "conference",
            "keywords",
            "citation_count",
            "reference_count",
            "url",
            "pdf_url",
            "is_open_access",
        ]
