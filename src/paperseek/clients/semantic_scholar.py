"""Semantic Scholar API client implementation."""

from typing import Any, Dict, List, Optional

from ..core.base import DatabaseClient
from ..core.models import Paper, Author, SearchFilters, SearchResult
from ..core.config import DatabaseConfig
from ..core.exceptions import APIError
from ..utils.normalization import (
    TextNormalizer,
    DateNormalizer,
    AuthorNormalizer,
    IdentifierNormalizer,
    URLNormalizer,
)


class SemanticScholarClient(DatabaseClient):
    """
    Client for Semantic Scholar API.

    Semantic Scholar is a free, AI-powered research tool for scientific literature.
    API Documentation: https://api.semanticscholar.org
    """

    BASE_URL = "https://api.semanticscholar.org/graph/v1"

    def __init__(
        self,
        config: DatabaseConfig,
        email: Optional[str] = None,
        user_agent: str = "AcademicSearchUnified/0.1.0",
    ):
        """Initialize Semantic Scholar client."""
        super().__init__(config, email, user_agent)

        # Add API key if available
        if config.api_key:
            self.session.headers.update({"x-api-key": config.api_key})

    @property
    def database_name(self) -> str:
        """Return database name."""
        return "semantic_scholar"

    def search(self, filters: SearchFilters) -> SearchResult:
        """
        Search Semantic Scholar database.

        Args:
            filters: Search filters

        Returns:
            SearchResult object
        """
        self.logger.info(f"Searching Semantic Scholar with filters: {filters}")

        # Build query
        query = filters.title or filters.author or ""

        # Check if we should use bulk search endpoint
        # Bulk search works better for venue/year-only searches
        use_bulk = not query and (filters.venue or filters.year or filters.year_start or filters.year_end)
        
        self.logger.info(f"Query: '{query}', use_bulk: {use_bulk}, venue: {filters.venue}, year: {filters.year}")

        if not query and not filters.doi and not use_bulk:
            self.logger.warning("No search query provided")
            return SearchResult(
                query_info={"filters": filters.model_dump()}, databases_queried=[self.database_name]
            )

        if filters.doi:
            return self._search_by_doi(filters.doi, filters)

        # Build params
        params: Dict[str, Any] = {
            "limit": min(filters.max_results, 100),  # S2 default max
            "offset": filters.offset,
            "fields": self._get_fields_param(),
        }

        # Add query if present
        if query:
            params["query"] = query

        # Add year filter if specified
        if filters.year:
            params["year"] = f"{filters.year}"
        elif filters.year_start or filters.year_end:
            year_range = f"{filters.year_start or ''}-{filters.year_end or ''}"
            params["year"] = year_range

        # Add venue filter
        if filters.venue:
            params["venue"] = filters.venue

        # Make request - use bulk endpoint if no query but has filters
        if use_bulk:
            url = f"{self.BASE_URL}/paper/search/bulk"
            self.logger.info(f"Using bulk search endpoint with params: {params}")
        else:
            url = f"{self.BASE_URL}/paper/search"
        
        response = self._make_request(url, params=params)

        data = response.json()

        # Parse results
        result = SearchResult(
            query_info={"filters": filters.model_dump(), "query": query},
            databases_queried=[self.database_name],
        )

        papers = data.get("data", [])
        for item in papers:
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
            url = f"{self.BASE_URL}/paper/DOI:{doi}"
            params = {"fields": self._get_fields_param()}
            response = self._make_request(url, params=params)
            data = response.json()
            return self._normalize_paper(data)
        except APIError:
            return None

    def get_by_identifier(self, identifier: str, id_type: str) -> Optional[Paper]:
        """Get paper by identifier."""
        try:
            id_type_lower = id_type.lower()

            if id_type_lower == "doi":
                return self.get_by_doi(identifier)
            elif id_type_lower in ["arxiv", "arxiv_id"]:
                url = f"{self.BASE_URL}/paper/ARXIV:{identifier}"
            elif id_type_lower == "pmid":
                url = f"{self.BASE_URL}/paper/PMID:{identifier}"
            elif id_type_lower in ["s2", "semantic_scholar"]:
                url = f"{self.BASE_URL}/paper/{identifier}"
            else:
                return None

            params = {"fields": self._get_fields_param()}
            response = self._make_request(url, params=params)
            data = response.json()
            return self._normalize_paper(data)
        except APIError:
            return None

    def batch_lookup(self, identifiers: List[str], id_type: str) -> SearchResult:
        """
        Look up multiple papers (supports batch API).

        Args:
            identifiers: List of identifiers
            id_type: Type of identifier

        Returns:
            SearchResult with found papers
        """
        result = SearchResult(
            query_info={"identifiers": identifiers, "id_type": id_type},
            databases_queried=[self.database_name],
        )

        # S2 supports batch lookup via POST
        if len(identifiers) <= 500:  # Batch limit
            try:
                url = f"{self.BASE_URL}/paper/batch"

                # Format IDs based on type
                id_type_lower = id_type.lower()
                if id_type_lower == "doi":
                    formatted_ids = [f"DOI:{id}" for id in identifiers]
                elif id_type_lower in ["arxiv", "arxiv_id"]:
                    formatted_ids = [f"ARXIV:{id}" for id in identifiers]
                elif id_type_lower == "pmid":
                    formatted_ids = [f"PMID:{id}" for id in identifiers]
                else:
                    formatted_ids = identifiers

                params = {"fields": self._get_fields_param()}
                json_data = {"ids": formatted_ids}

                response = self._make_request(
                    url, method="POST", params=params, json_data=json_data
                )
                data = response.json()

                for item in data:
                    if item:  # Some may be None if not found
                        try:
                            paper = self._normalize_paper(item)
                            result.add_paper(paper)
                        except Exception as e:
                            self.logger.warning(f"Failed to normalize paper: {e}")
            except Exception as e:
                self.logger.warning(f"Batch lookup failed, falling back to individual: {e}")
                # Fallback to individual lookups
                for identifier in identifiers:
                    paper = self.get_by_identifier(identifier, id_type)
                    if paper:
                        result.add_paper(paper)
        else:
            # Too many for batch, do individual lookups
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

    def _get_fields_param(self) -> str:
        """Get the fields parameter for API requests."""
        fields = [
            "paperId",
            "externalIds",
            "title",
            "abstract",
            "year",
            "authors",
            "venue",
            "publicationDate",
            "citationCount",
            "referenceCount",
            "isOpenAccess",
            "openAccessPdf",
            "fieldsOfStudy",
            "s2FieldsOfStudy",
            "publicationTypes",
        ]
        return ",".join(fields)

    def _normalize_paper(self, raw_data: Dict[str, Any]) -> Paper:
        """
        Normalize Semantic Scholar data to Paper model.

        Args:
            raw_data: Raw Semantic Scholar API response

        Returns:
            Normalized Paper object
        """
        # Extract external IDs using normalizers
        external_ids = raw_data.get("externalIds", {})
        doi = IdentifierNormalizer.clean_doi(external_ids.get("DOI"))
        pmid = IdentifierNormalizer.extract_pmid(external_ids.get("PubMed"))
        arxiv_id = IdentifierNormalizer.extract_arxiv_id(external_ids.get("ArXiv"))

        # Extract authors using AuthorNormalizer
        authors = []
        for author_data in raw_data.get("authors") or []:
            author = AuthorNormalizer.create_author(
                name=author_data.get("name"),
                # S2 doesn't provide affiliation in basic API
            )
            authors.append(author)

        # Extract venue with text normalization
        venue = TextNormalizer.clean_text(raw_data.get("venue"))

        # Determine type - S2 provides publication types
        pub_types = raw_data.get("publicationTypes") or []
        conference = None
        journal = None

        if "Conference" in pub_types:
            conference = venue
        elif "JournalArticle" in pub_types:
            journal = venue
        else:
            # Default to journal
            journal = venue

        # Extract keywords from fields of study with text normalization
        keywords = []
        for field in raw_data.get("s2FieldsOfStudy") or []:
            if field.get("category"):
                cleaned_keyword = TextNormalizer.clean_text(field["category"])
                if cleaned_keyword:
                    keywords.append(cleaned_keyword)

        # Get PDF URL using URLNormalizer
        pdf_url = None
        oa_pdf = raw_data.get("openAccessPdf")
        if oa_pdf:
            pdf_url = URLNormalizer.clean_url(oa_pdf.get("url"))

        # Extract year using DateNormalizer
        year = DateNormalizer.extract_year(raw_data.get("year"))
        
        # Clean text fields
        title = TextNormalizer.clean_text(raw_data.get("title")) or "Unknown"
        abstract = TextNormalizer.clean_text(raw_data.get("abstract"))
        publication_date = raw_data.get("publicationDate")
        
        # Construct and clean URL
        paper_id = raw_data.get("paperId")
        url = None
        if paper_id:
            url = URLNormalizer.clean_url(
                f"https://www.semanticscholar.org/paper/{paper_id}"
            )

        return Paper(
            doi=doi,
            pmid=pmid,
            arxiv_id=arxiv_id,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            publication_date=publication_date,
            venue=venue,
            journal=journal,
            conference=conference,
            keywords=keywords,
            citation_count=raw_data.get("citationCount"),
            reference_count=raw_data.get("referenceCount"),
            url=url,
            pdf_url=pdf_url,
            is_open_access=raw_data.get("isOpenAccess"),
            source_database=self.database_name,
            source_id=paper_id,
            extra_data={
                "s2_paper_id": paper_id,
                "publication_types": pub_types,
                "fields_of_study": raw_data.get("fieldsOfStudy"),
            },
        )

    def get_supported_fields(self) -> List[str]:
        """Get fields typically provided by Semantic Scholar."""
        return [
            "doi",
            "pmid",
            "arxiv_id",
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
