"""DOI.org API client implementation."""

from typing import Any, Dict, List, Optional

from ..core.base import DatabaseClient
from ..core.models import Paper, Author, SearchFilters, SearchResult
from ..core.config import DatabaseConfig
from ..core.exceptions import APIError


class DOIClient(DatabaseClient):
    """
    Client for DOI.org resolution service.

    This client resolves DOIs to their metadata using content negotiation.
    API Documentation: https://www.doi.org/the-identifier/resources/factsheets/doi-resolution-documentation
    """

    BASE_URL = "https://doi.org"

    @property
    def database_name(self) -> str:
        """Return database name."""
        return "doi"

    def search(self, filters: SearchFilters) -> SearchResult:
        """
        Search DOI database (only supports DOI lookup).

        Args:
            filters: Search filters

        Returns:
            SearchResult object
        """
        self.logger.info(f"Searching DOI.org with filters: {filters}")

        result = SearchResult(
            query_info={"filters": filters.model_dump()}, databases_queried=[self.database_name]
        )

        if filters.doi:
            paper = self.get_by_doi(filters.doi)
            if paper:
                result.add_paper(paper)
        else:
            self.logger.warning("DOI client only supports DOI-based lookups")

        return result

    def get_by_doi(self, doi: str) -> Optional[Paper]:
        """
        Get paper by DOI using content negotiation.

        Args:
            doi: Digital Object Identifier

        Returns:
            Paper object or None
        """
        try:
            url = f"{self.BASE_URL}/{doi}"

            # Request JSON-LD format
            headers = {"Accept": "application/vnd.citationstyles.csl+json"}

            response = self._make_request(url, headers=headers)
            data = response.json()

            return self._normalize_paper(data)
        except APIError as e:
            self.logger.warning(f"Failed to resolve DOI {doi}: {e}")
            return None

    def get_by_identifier(self, identifier: str, id_type: str) -> Optional[Paper]:
        """Get paper by identifier (only DOI supported)."""
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

        return result

    def _normalize_paper(self, raw_data: Dict[str, Any]) -> Paper:
        """
        Normalize DOI.org CSL JSON data to Paper model.

        Args:
            raw_data: Raw CSL JSON response

        Returns:
            Normalized Paper object
        """
        # Extract authors
        authors = []
        for author_data in raw_data.get("author", []):
            # CSL format uses "family" and "given" names
            name_parts = []
            if "given" in author_data:
                name_parts.append(author_data["given"])
            if "family" in author_data:
                name_parts.append(author_data["family"])

            if not name_parts and "literal" in author_data:
                name_parts.append(author_data["literal"])

            name = " ".join(name_parts) if name_parts else "Unknown"

            authors.append(
                Author(
                    name=name,
                    affiliation=(
                        author_data.get("affiliation", [{}])[0].get("name")
                        if author_data.get("affiliation")
                        else None
                    ),
                    orcid=None,
                )
            )

        # Extract year
        year = None
        issued = raw_data.get("issued", {})
        if "date-parts" in issued and issued["date-parts"]:
            date_parts = issued["date-parts"][0]
            if date_parts:
                year = date_parts[0]

        # Extract venue
        venue = raw_data.get("container-title")
        if isinstance(venue, list):
            venue = venue[0] if venue else None

        # Determine type
        paper_type = raw_data.get("type", "")
        conference = None
        journal = None

        if "proceedings" in paper_type or "paper-conference" in paper_type:
            conference = venue
        else:
            journal = venue

        # Extract DOI
        doi = raw_data.get("DOI")

        # Extract URL
        url = raw_data.get("URL") or (f"https://doi.org/{doi}" if doi else None)

        # Extract title (DOI API returns title as a list)
        title = raw_data.get("title", "Unknown")
        if isinstance(title, list):
            title = title[0] if title else "Unknown"

        return Paper(
            doi=doi,
            title=title,
            authors=authors,
            abstract=raw_data.get("abstract"),
            year=year,
            venue=venue,
            journal=journal,
            conference=conference,
            volume=raw_data.get("volume"),
            issue=raw_data.get("issue"),
            pages=raw_data.get("page"),
            publisher=raw_data.get("publisher"),
            url=url,
            source_database=self.database_name,
            source_id=doi,
            extra_data={
                "type": raw_data.get("type"),
                "issn": raw_data.get("ISSN"),
                "isbn": raw_data.get("ISBN"),
                "raw": raw_data,
            },
        )

    def get_supported_fields(self) -> List[str]:
        """Get fields typically provided by DOI.org."""
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
            "url",
        ]
