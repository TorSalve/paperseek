"""arXiv API client implementation."""

from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET
from datetime import datetime

from ..core.base import DatabaseClient
from ..core.models import Paper, Author, SearchFilters, SearchResult
from ..core.config import DatabaseConfig
from ..core.exceptions import APIError


class ArXivClient(DatabaseClient):
    """
    Client for arXiv API.

    arXiv is a free distribution service and an open-access archive for scholarly articles
    in physics, mathematics, computer science, quantitative biology, quantitative finance,
    statistics, electrical engineering and systems science, and economics.

    API Documentation: https://info.arxiv.org/help/api/index.html

    Note: No API key required. Rate limiting: 1 request per 3 seconds recommended.
    """

    BASE_URL = "http://export.arxiv.org/api/query"

    # Namespace for XML parsing
    ATOM_NS = {"atom": "http://www.w3.org/2005/Atom"}

    @property
    def database_name(self) -> str:
        """Return database name."""
        return "arxiv"

    def search(self, filters: SearchFilters) -> SearchResult:
        """
        Search arXiv database.

        Args:
            filters: Search filters

        Returns:
            SearchResult object
        """
        self.logger.info(f"Searching arXiv with filters: {filters}")

        # Build search query using arXiv query format
        query_parts = []

        if filters.doi:
            # arXiv doesn't support DOI search directly, but we can try to extract arXiv ID
            arxiv_id = self._extract_arxiv_id_from_doi(filters.doi)
            if arxiv_id:
                query_parts.append(f"id:{arxiv_id}")
            else:
                # Fallback to all search
                query_parts.append(f'all:"{filters.doi}"')

        if filters.title:
            query_parts.append(f'ti:"{filters.title}"')

        if filters.author:
            query_parts.append(f'au:"{filters.author}"')

        if not query_parts:
            query_parts.append("all:*")  # Search all if no specific criteria

        query = " AND ".join(query_parts)

        # Build params
        params = {
            "search_query": query,
            "start": filters.offset,
            "max_results": min(filters.max_results, 2000),  # arXiv recommended max
            "sortBy": "relevance",
            "sortOrder": "descending",
        }

        # Make request
        response = self._make_request(self.BASE_URL, params=params)

        # Parse XML response
        result = SearchResult(
            query_info={"filters": filters.model_dump(), "query": query},
            databases_queried=[self.database_name],
        )

        try:
            root = ET.fromstring(response.text)

            for entry in root.findall("atom:entry", self.ATOM_NS):
                try:
                    paper = self._normalize_paper_from_xml(entry)

                    # Apply year filter (arXiv API doesn't support date filtering in query)
                    if filters.year and paper.year != filters.year:
                        continue
                    if filters.year_start and paper.year and paper.year < filters.year_start:
                        continue
                    if filters.year_end and paper.year and paper.year > filters.year_end:
                        continue

                    result.add_paper(paper)
                except Exception as e:
                    self.logger.warning(f"Failed to normalize paper: {e}")
                    continue

        except ET.ParseError as e:
            self.logger.error(f"Failed to parse XML response: {e}")
            raise APIError(f"Invalid XML response: {e}", database=self.database_name)

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
        elif id_type.lower() == "arxiv":
            try:
                # Clean arXiv ID (remove version if present for search)
                arxiv_id = identifier.replace("arXiv:", "").split("v")[0]

                params = {
                    "id_list": arxiv_id,
                    "max_results": 1,
                }

                response = self._make_request(self.BASE_URL, params=params)
                root = ET.fromstring(response.text)

                entry = root.find("atom:entry", self.ATOM_NS)
                if entry is not None:
                    return self._normalize_paper_from_xml(entry)
                return None
            except Exception as e:
                self.logger.warning(f"Failed to get paper by arXiv ID: {e}")
                return None
        return None

    def batch_lookup(self, identifiers: List[str], id_type: str) -> SearchResult:
        """Look up multiple papers."""
        result = SearchResult(
            query_info={"identifiers": identifiers, "id_type": id_type},
            databases_queried=[self.database_name],
        )

        if id_type.lower() == "arxiv":
            # Can fetch multiple arXiv IDs at once
            # Clean IDs
            clean_ids = [id.replace("arXiv:", "").split("v")[0] for id in identifiers]

            params = {
                "id_list": ",".join(clean_ids),
                "max_results": len(clean_ids),
            }

            try:
                response = self._make_request(self.BASE_URL, params=params)
                root = ET.fromstring(response.text)

                for entry in root.findall("atom:entry", self.ATOM_NS):
                    try:
                        paper = self._normalize_paper_from_xml(entry)
                        result.add_paper(paper)
                    except Exception as e:
                        self.logger.warning(f"Failed to normalize paper: {e}")
                        continue
            except Exception as e:
                self.logger.error(f"Failed to batch lookup: {e}")
        else:
            # Fetch individually for other identifier types
            for identifier in identifiers:
                paper = self.get_by_identifier(identifier, id_type)
                if paper:
                    result.add_paper(paper)

        return result

    def _normalize_paper(self, raw_data: Dict[str, Any]) -> Paper:
        """
        Normalize arXiv data to Paper model.

        Note: arXiv returns XML, so this method uses _normalize_paper_from_xml.
        """
        raise NotImplementedError("Use _normalize_paper_from_xml for arXiv data")

    def _normalize_paper_from_xml(self, entry: ET.Element) -> Paper:
        """
        Normalize arXiv XML entry to Paper model.

        Args:
            entry: Atom entry XML element

        Returns:
            Normalized Paper object
        """
        # Extract arXiv ID
        id_elem = entry.find("atom:id", self.ATOM_NS)
        arxiv_url = id_elem.text if id_elem is not None else None
        arxiv_id = arxiv_url.split("/abs/")[-1] if arxiv_url else None

        # Extract title
        title_elem = entry.find("atom:title", self.ATOM_NS)
        title = title_elem.text.strip() if title_elem is not None and title_elem.text else "Unknown"

        # Extract authors
        authors = []
        for author_elem in entry.findall("atom:author", self.ATOM_NS):
            name_elem = author_elem.find("atom:name", self.ATOM_NS)
            if name_elem is not None and name_elem.text:
                authors.append(Author(name=name_elem.text.strip()))

        # Extract abstract
        summary_elem = entry.find("atom:summary", self.ATOM_NS)
        abstract = (
            summary_elem.text.strip() if summary_elem is not None and summary_elem.text else None
        )

        # Extract publication date
        published_elem = entry.find("atom:published", self.ATOM_NS)
        year = None
        publication_date = None
        if published_elem is not None and published_elem.text:
            publication_date = published_elem.text
            try:
                date_obj = datetime.fromisoformat(publication_date.replace("Z", "+00:00"))
                year = date_obj.year
            except (ValueError, AttributeError):
                pass

        # Extract categories (used as keywords)
        keywords = []
        for category_elem in entry.findall("atom:category", self.ATOM_NS):
            term = category_elem.get("term")
            if term:
                keywords.append(term)

        # Extract DOI if available
        doi = None
        for link_elem in entry.findall("atom:link", self.ATOM_NS):
            if link_elem.get("title") == "doi":
                doi_url = link_elem.get("href", "")
                if doi_url:
                    doi = doi_url.replace("http://dx.doi.org/", "").replace("https://doi.org/", "")

        # Extract PDF URL
        pdf_url = None
        for link_elem in entry.findall("atom:link", self.ATOM_NS):
            if link_elem.get("title") == "pdf":
                pdf_url = link_elem.get("href")
                break

        # Extract primary category (venue)
        primary_category = entry.find(
            "arxiv:primary_category", {"arxiv": "http://arxiv.org/schemas/atom"}
        )
        venue = primary_category.get("term") if primary_category is not None else None

        # Construct comment field
        comment_elem = entry.find("arxiv:comment", {"arxiv": "http://arxiv.org/schemas/atom"})
        comment = comment_elem.text if comment_elem is not None else None

        return Paper(
            doi=doi,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            publication_date=publication_date,
            venue=venue,
            keywords=keywords,
            url=arxiv_url,
            pdf_url=pdf_url,
            is_open_access=True,  # All arXiv papers are open access
            source_database=self.database_name,
            source_id=arxiv_id,
            extra_data={
                "arxiv_id": arxiv_id,
                "comment": comment,
                "primary_category": venue,
            },
        )

    def _extract_arxiv_id_from_doi(self, doi: str) -> Optional[str]:
        """
        Try to extract arXiv ID from DOI if it's an arXiv DOI.

        Args:
            doi: DOI string

        Returns:
            arXiv ID or None
        """
        # arXiv DOIs typically look like: 10.48550/arXiv.YYMM.NNNNN
        if "arxiv" in doi.lower():
            parts = doi.split("arxiv.")
            if len(parts) > 1:
                return parts[1]
        return None

    def get_supported_fields(self) -> List[str]:
        """Get fields typically provided by arXiv."""
        return [
            "doi",
            "title",
            "authors",
            "abstract",
            "year",
            "publication_date",
            "venue",
            "keywords",
            "url",
            "pdf_url",
            "is_open_access",
        ]
