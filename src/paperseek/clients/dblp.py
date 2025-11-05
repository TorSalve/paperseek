"""DBLP API client implementation."""

from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from ..core.base import DatabaseClient
from ..core.models import Paper, Author, SearchFilters, SearchResult
from ..core.config import DatabaseConfig
from ..core.exceptions import APIError


class DBLPClient(DatabaseClient):
    """
    Client for DBLP (Computer Science Bibliography) API.

    DBLP is a comprehensive computer science bibliography providing bibliographic
    information on major computer science journals and proceedings.
    
    API Documentation: https://dblp.org/faq/How+to+use+the+dblp+search+API.html
    
    Note: No API key required. Free to use.
    Rate limiting: Be respectful, no official limit but throttle recommended.
    """

    BASE_URL = "https://dblp.org/search/publ/api"

    @property
    def database_name(self) -> str:
        """Return database name."""
        return "dblp"

    def search(self, filters: SearchFilters) -> SearchResult:
        """
        Search DBLP database.

        Args:
            filters: Search filters

        Returns:
            SearchResult object
        """
        self.logger.info(f"Searching DBLP with filters: {filters}")

        # Build search query
        query_parts = []

        if filters.doi:
            query_parts.append(f'doi:"{filters.doi}"')
        if filters.title:
            query_parts.append(filters.title)
        if filters.author:
            query_parts.append(f"{filters.author}$")  # $ suffix for author search

        # Venue filters
        if filters.venue:
            query_parts.append(f'venue:"{filters.venue}"')

        if not query_parts:
            raise ValueError("At least one search criterion must be provided")

        query = " ".join(query_parts)

        # Build params
        params = {
            "q": query,
            "h": min(filters.max_results, 1000),  # Max results per request
            "f": filters.offset,  # First hit to return
            "format": "xml",
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

            # Check for hits
            hits_elem = root.find(".//hits")
            if hits_elem is None:
                return result

            for hit_elem in hits_elem.findall("hit"):
                info_elem = hit_elem.find("info")
                if info_elem is not None:
                    try:
                        paper = self._normalize_paper_from_xml(info_elem)

                        # Apply year filter (DBLP doesn't support year filtering in query)
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
        elif id_type.lower() == "dblp":
            try:
                # DBLP key format: journals/cacm/Knuth74
                # Can fetch directly via publication API
                url = f"https://dblp.org/rec/{identifier}.xml"
                response = self._make_request(url)

                root = ET.fromstring(response.text)
                # Find first publication entry
                for pub_type in ["article", "inproceedings", "proceedings", "book", "incollection", "phdthesis", "mastersthesis"]:
                    pub_elem = root.find(f".//{pub_type}")
                    if pub_elem is not None:
                        return self._normalize_paper_from_xml(pub_elem)
                return None
            except Exception as e:
                self.logger.warning(f"Failed to get paper by DBLP key: {e}")
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
        Normalize DBLP data to Paper model.
        
        Note: DBLP returns XML, so this method uses _normalize_paper_from_xml.
        """
        raise NotImplementedError("Use _normalize_paper_from_xml for DBLP data")

    def _normalize_paper_from_xml(self, info_elem: ET.Element) -> Paper:
        """
        Normalize DBLP XML info element to Paper model.

        Args:
            info_elem: Info XML element from DBLP response

        Returns:
            Normalized Paper object
        """
        # Extract title
        title_elem = info_elem.find("title")
        title = title_elem.text if title_elem is not None else "Unknown"

        # Extract authors
        authors = []
        for author_elem in info_elem.findall("author"):
            if author_elem.text:
                authors.append(Author(name=author_elem.text))

        # Extract venue information
        venue_elem = info_elem.find("venue")
        venue = venue_elem.text if venue_elem is not None else None

        # Determine if journal or conference
        pub_type = info_elem.find("type")
        pub_type_str = pub_type.text if pub_type is not None else None

        journal = None
        conference = None
        if pub_type_str in ["Journal Articles", "Informal Publications"]:
            journal = venue
        elif pub_type_str in ["Conference and Workshop Papers"]:
            conference = venue
        else:
            # Default to conference for computer science
            conference = venue

        # Extract year
        year = None
        year_elem = info_elem.find("year")
        if year_elem is not None and year_elem.text:
            try:
                year = int(year_elem.text)
            except (ValueError, TypeError):
                pass

        # Extract DOI
        doi_elem = info_elem.find("doi")
        doi = doi_elem.text if doi_elem is not None else None

        # Extract URL (DBLP page)
        url_elem = info_elem.find("url")
        url = url_elem.text if url_elem is not None else None

        # Extract electronic edition (ee) - often links to PDF or publisher page
        ee_elem = info_elem.find("ee")
        ee_url = ee_elem.text if ee_elem is not None else None

        # Extract DBLP key
        key_elem = info_elem.find("key")
        dblp_key = key_elem.text if key_elem is not None else None

        # Determine PDF URL
        pdf_url = None
        if ee_url and any(domain in ee_url for domain in ["arxiv.org", "pdf"]):
            pdf_url = ee_url

        return Paper(
            doi=doi,
            title=title,
            authors=authors,
            year=year,
            venue=venue,
            journal=journal,
            conference=conference,
            url=url,
            pdf_url=pdf_url,
            source_database=self.database_name,
            source_id=dblp_key,
            extra_data={
                "dblp_key": dblp_key,
                "type": pub_type_str,
                "ee": ee_url,
            },
        )

    def get_supported_fields(self) -> List[str]:
        """Get fields typically provided by DBLP."""
        return [
            "doi",
            "title",
            "authors",
            "year",
            "venue",
            "journal",
            "conference",
            "url",
        ]
