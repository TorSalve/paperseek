"""PubMed API client implementation using E-utilities."""

from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from ..core.base import DatabaseClient
from ..core.models import Paper, Author, SearchFilters, SearchResult
from ..core.exceptions import APIError
from ..utils.normalization import (
    TextNormalizer,
    DateNormalizer,
    AuthorNormalizer,
    IdentifierNormalizer,
    URLNormalizer,
)


class PubMedClient(DatabaseClient):
    """
    Client for PubMed E-utilities API.

    PubMed comprises more than 36 million citations for biomedical literature from MEDLINE,
    life science journals, and online books.

    API Documentation: https://www.ncbi.nlm.nih.gov/books/NBK25501/

    Note: NCBI requests users provide an email address and API key for better rate limits.
    - Without API key: 3 requests/second
    - With API key: 10 requests/second
    """

    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    @property
    def database_name(self) -> str:
        """Return database name."""
        return "pubmed"

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
        Make an HTTP request with PubMed-specific parameters.

        Adds email and api_key parameters for better rate limits.

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

        # Add email parameter if provided
        if self.email:
            params["email"] = self.email

        # Add API key parameter if provided (for 10 req/sec limit)
        if self.config.api_key:
            params["api_key"] = self.config.api_key
            self.logger.debug("Using PubMed API key for enhanced rate limits")

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
        Search PubMed database.

        Args:
            filters: Search filters

        Returns:
            SearchResult object
        """
        self.logger.info(f"Searching PubMed with filters: {filters}")

        # Build search query
        query_parts = []

        if filters.doi:
            query_parts.append(f'"{filters.doi}"[DOI]')
        if filters.title:
            query_parts.append(f'"{filters.title}"[Title]')
        if filters.author:
            query_parts.append(f'"{filters.author}"[Author]')

        # Year filters
        if filters.year:
            query_parts.append(f"{filters.year}[Publication Date]")
        elif filters.year_start or filters.year_end:
            year_start = filters.year_start or 1800
            year_end = filters.year_end or 2100
            query_parts.append(f"{year_start}:{year_end}[Publication Date]")

        # Venue/journal filters
        if filters.venue:
            query_parts.append(f'"{filters.venue}"[Journal]')

        if not query_parts:
            raise ValueError("At least one search criterion must be provided")

        query = " AND ".join(query_parts)

        # Step 1: Search for PMIDs
        search_params = {
            "db": "pubmed",
            "term": query,
            "retmax": min(filters.max_results, 10000),  # PubMed max
            "retstart": filters.offset,
            "retmode": "json",
        }

        search_url = f"{self.BASE_URL}/esearch.fcgi"
        search_response = self._make_request(search_url, params=search_params)
        search_data = search_response.json()

        pmids = search_data.get("esearchresult", {}).get("idlist", [])

        if not pmids:
            return SearchResult(
                query_info={"filters": filters.model_dump(), "query": query},
                databases_queried=[self.database_name],
            )

        # Step 2: Fetch details for PMIDs
        result = SearchResult(
            query_info={"filters": filters.model_dump(), "query": query, "pmids": pmids},
            databases_queried=[self.database_name],
        )

        # Fetch in batches of 200 (PubMed recommendation)
        batch_size = 200
        for i in range(0, len(pmids), batch_size):
            batch_pmids = pmids[i : i + batch_size]
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(batch_pmids),
                "retmode": "xml",
            }

            fetch_url = f"{self.BASE_URL}/efetch.fcgi"
            fetch_response = self._make_request(fetch_url, params=fetch_params)

            # Parse XML response
            try:
                root = ET.fromstring(fetch_response.text)
                for article_elem in root.findall(".//PubmedArticle"):
                    try:
                        paper = self._normalize_paper_from_xml(article_elem)
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
        elif id_type.lower() in ["pmid", "pubmed"]:
            try:
                fetch_params = {
                    "db": "pubmed",
                    "id": identifier,
                    "retmode": "xml",
                }

                fetch_url = f"{self.BASE_URL}/efetch.fcgi"
                fetch_response = self._make_request(fetch_url, params=fetch_params)

                # Parse XML response
                root = ET.fromstring(fetch_response.text)
                article_elem = root.find(".//PubmedArticle")
                if article_elem is not None:
                    return self._normalize_paper_from_xml(article_elem)
                return None
            except Exception as e:
                self.logger.warning(f"Failed to get paper by PMID: {e}")
                return None
        return None

    def batch_lookup(self, identifiers: List[str], id_type: str) -> SearchResult:
        """Look up multiple papers."""
        result = SearchResult(
            query_info={"identifiers": identifiers, "id_type": id_type},
            databases_queried=[self.database_name],
        )

        if id_type.lower() in ["pmid", "pubmed"]:
            # Can fetch multiple PMIDs at once
            fetch_params = {
                "db": "pubmed",
                "id": ",".join(identifiers),
                "retmode": "xml",
            }

            fetch_url = f"{self.BASE_URL}/efetch.fcgi"
            try:
                fetch_response = self._make_request(fetch_url, params=fetch_params)
                root = ET.fromstring(fetch_response.text)
                for article_elem in root.findall(".//PubmedArticle"):
                    try:
                        paper = self._normalize_paper_from_xml(article_elem)
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
        Normalize PubMed data to Paper model.

        Note: This is for JSON data. XML parsing uses _normalize_paper_from_xml.
        """
        # PubMed primarily returns XML, so this method is less commonly used
        raise NotImplementedError("Use _normalize_paper_from_xml for PubMed data")

    def _normalize_paper_from_xml(self, article_elem: ET.Element) -> Paper:
        """
        Normalize PubMed XML data to Paper model.

        Args:
            article_elem: PubmedArticle XML element

        Returns:
            Normalized Paper object
        """
        medline_citation = article_elem.find("MedlineCitation")
        if medline_citation is None:
            raise ValueError("Invalid PubMed article: missing MedlineCitation")

        article = medline_citation.find("Article")
        if article is None:
            raise ValueError("Invalid PubMed article: missing Article")

        # Extract PMID
        pmid_elem = medline_citation.find("PMID")
        pmid = IdentifierNormalizer.extract_pmid(
            pmid_elem.text if pmid_elem is not None else None
        )

        # Extract title with text normalization
        title_elem = article.find("ArticleTitle")
        title = TextNormalizer.clean_text(
            title_elem.text if title_elem is not None else None
        ) or "Unknown"

        # Extract authors using AuthorNormalizer
        authors = []
        author_list = article.find("AuthorList")
        if author_list is not None:
            for author_elem in author_list.findall("Author"):
                last_name = author_elem.findtext("LastName", "")
                fore_name = author_elem.findtext("ForeName", "")
                
                # Get affiliation
                affiliation_elem = author_elem.find(".//Affiliation")
                affiliation = TextNormalizer.clean_text(
                    affiliation_elem.text if affiliation_elem is not None else None
                )

                author = AuthorNormalizer.create_author(
                    given=fore_name,
                    family=last_name,
                    affiliation=affiliation
                )
                authors.append(author)

        # Extract abstract with text normalization
        abstract_elem = article.find("Abstract/AbstractText")
        abstract = TextNormalizer.clean_text(
            abstract_elem.text if abstract_elem is not None else None
        )

        # Extract year using DateNormalizer
        year = None
        pub_date = article.find(".//PubDate")
        if pub_date is not None:
            year_elem = pub_date.find("Year")
            year = DateNormalizer.extract_year(
                year_elem.text if year_elem is not None else None
            )

        # Extract journal with text normalization
        journal_elem = article.find(".//Journal/Title")
        journal = TextNormalizer.clean_text(
            journal_elem.text if journal_elem is not None else None
        )

        # Extract DOI
        doi = None
        article_id_list = article_elem.find(".//PubmedData/ArticleIdList")
        if article_id_list is not None:
            for article_id in article_id_list.findall("ArticleId"):
                if article_id.get("IdType") == "doi":
                    doi = IdentifierNormalizer.clean_doi(article_id.text)
                    break

        # Extract keywords with text normalization
        keywords = []
        keyword_list = medline_citation.find("KeywordList")
        if keyword_list is not None:
            for keyword_elem in keyword_list.findall(".//Keyword"):
                if keyword_elem.text:
                    cleaned_keyword = TextNormalizer.clean_text(keyword_elem.text)
                    if cleaned_keyword:
                        keywords.append(cleaned_keyword)

        # Construct URL
        url = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/" if pmid else None
        url = URLNormalizer.clean_url(url)

        return Paper(
            doi=doi,
            title=title,
            authors=authors,
            abstract=abstract,
            year=year,
            venue=journal,
            journal=journal,
            keywords=keywords,
            url=url,
            source_database=self.database_name,
            source_id=pmid,
            extra_data={
                "pmid": pmid,
            },
        )

    def get_supported_fields(self) -> List[str]:
        """Get fields typically provided by PubMed."""
        return [
            "doi",
            "title",
            "authors",
            "abstract",
            "year",
            "journal",
            "keywords",
            "url",
        ]
