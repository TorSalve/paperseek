"""Unified client for searching across multiple databases."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional

from .base import DatabaseClient
from .models import SearchFilters, SearchResult, Paper
from .config import AcademicSearchConfig, load_config
from .exceptions import SearchError, ConfigurationError
from ..clients.crossref import CrossRefClient
from ..clients.openalex import OpenAlexClient
from ..clients.semantic_scholar import SemanticScholarClient
from ..clients.doi import DOIClient
from ..clients.pubmed import PubMedClient
from ..clients.arxiv import ArXivClient
from ..clients.core import COREClient
from ..clients.unpaywall import UnpaywallClient
from ..clients.dblp import DBLPClient
from ..utils.logging import get_logger


class UnifiedSearchClient:
    """
    Unified client for searching across multiple academic databases.

    This client orchestrates searches across CrossRef, OpenAlex,
    Semantic Scholar, and DOI.org with fallback support and result merging.

    Examples:
        Basic usage with default configuration:

        >>> from paperseek import UnifiedSearchClient, SearchFilters
        >>> client = UnifiedSearchClient()
        >>> filters = SearchFilters(title="machine learning", max_results=10)
        >>> results = client.search(filters)
        >>> print(f"Found {len(results)} papers")

        Searching specific databases in parallel:

        >>> client = UnifiedSearchClient(
        ...     databases=["arxiv", "semantic_scholar"],
        ...     fallback_mode="parallel"
        ... )
        >>> filters = SearchFilters(author="LeCun", year=2020)
        >>> results = client.search(filters, databases=["arxiv", "pubmed"])

        Using custom configuration:

        >>> config_dict = {
        ...     "email": "researcher@university.edu",
        ...     "semantic_scholar": {"api_key": "your-api-key"}
        ... }
        >>> client = UnifiedSearchClient(config_dict=config_dict)

        Sequential search with fallback:

        >>> client = UnifiedSearchClient(fallback_mode="sequential")
        >>> results = client.search(filters)  # Tries databases in order
    """

    def __init__(
        self,
        databases: Optional[List[str]] = None,
        fallback_mode: str = "sequential",
        config_file: Optional[str] = None,
        config_dict: Optional[Dict] = None,
        config: Optional[AcademicSearchConfig] = None,
    ):
        """
        Initialize unified search client.

        Args:
            databases: List of databases to use (default: all enabled)
            fallback_mode: How to handle multiple databases:
                - 'sequential': Try databases in order until success
                - 'parallel': Query all databases in parallel and merge
                - 'first': Use only the first database
            config_file: Path to configuration file
            config_dict: Configuration dictionary
            config: Pre-configured AcademicSearchConfig object
        """
        self.logger = get_logger(self.__class__.__name__)

        # Load configuration
        if config:
            self.config = config
        else:
            self.config = load_config(
                config_file=config_file, config_dict=config_dict, use_env=True
            )

        # Set fallback mode
        self.fallback_mode = fallback_mode or self.config.fallback_mode

        # Initialize database clients
        self.clients: Dict[str, DatabaseClient] = {}
        self._init_clients(databases)

        if not self.clients:
            raise ConfigurationError("No database clients are enabled")

    def _init_clients(self, databases: Optional[List[str]] = None) -> None:
        """Initialize database clients based on configuration."""
        available_clients = {
            "crossref": CrossRefClient,
            "openalex": OpenAlexClient,
            "semantic_scholar": SemanticScholarClient,
            "doi": DOIClient,
            "pubmed": PubMedClient,
            "arxiv": ArXivClient,
            "core": COREClient,
            "unpaywall": UnpaywallClient,
            "dblp": DBLPClient,
        }

        # Determine which databases to use
        if databases:
            db_list = [db.lower() for db in databases]
        else:
            # Use all enabled databases
            db_list = [
                name
                for name in available_clients.keys()
                if self.config.get_database_config(name).enabled
            ]

        # Initialize clients
        for db_name in db_list:
            if db_name not in available_clients:
                self.logger.warning(f"Unknown database: {db_name}")
                continue

            db_config = self.config.get_database_config(db_name)
            if not db_config.enabled:
                self.logger.info(f"Database {db_name} is disabled in config")
                continue

            try:
                client_class = available_clients[db_name]
                self.clients[db_name] = client_class(
                    config=db_config, email=self.config.email, user_agent=self.config.user_agent
                )
                self.logger.info(f"Initialized {db_name} client")
            except Exception as e:
                self.logger.error(f"Failed to initialize {db_name} client: {e}")

    def search(
        self,
        filters: Optional[SearchFilters] = None,
        venue: Optional[str] = None,
        year: Optional[int] = None,
        year_range: Optional[tuple] = None,
        title: Optional[str] = None,
        author: Optional[str] = None,
        doi: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        required_fields: Optional[List[str]] = None,
        max_results: int = 100,
        mode: Optional[str] = None,
        **kwargs,
    ) -> SearchResult:
        """
        Search across configured databases.

        Args:
            filters: SearchFilters object (if provided, other filter args are ignored)
            venue: Conference or journal name
            year: Publication year
            year_range: Tuple of (start_year, end_year)
            title: Paper title
            author: Author name
            doi: Digital Object Identifier
            keywords: List of keywords
            required_fields: Fields that must be present in results
            max_results: Maximum number of results
            mode: Search mode ('sequential' or 'parallel'). Overrides client default if provided.
            **kwargs: Additional search parameters

        Returns:
            SearchResult object with combined results

        Examples:
            Search by title:

            >>> client = UnifiedSearchClient()
            >>> results = client.search(title="attention is all you need")
            >>> print(f"Found {len(results)} papers")

            Search by author and year:

            >>> results = client.search(author="Hinton", year=2020)
            >>> for paper in results.papers:
            ...     print(f"{paper.title} ({paper.year})")

            Search with multiple criteria:

            >>> results = client.search(
            ...     venue="NeurIPS",
            ...     year_range=(2018, 2022),
            ...     keywords=["deep learning", "transformers"],
            ...     max_results=50
            ... )

            Search by DOI:

            >>> results = client.search(doi="10.1038/nature14539")
            >>> if results.papers:
            ...     paper = results.papers[0]
            ...     print(f"Title: {paper.title}")
            
            Search with filters object:

            >>> filters = SearchFilters(venue="CHI", year=2025, max_results=100)
            >>> results = client.search(filters=filters)
        """
        # If filters object provided, use it directly
        if filters is not None:
            search_filters = filters
        else:
            # Build search filters from individual parameters
            search_filters = SearchFilters(
                venue=venue,
                year=year,
                title=title,
                author=author,
                doi=doi,
                keywords=keywords,
                required_fields=required_fields,
                max_results=max_results,
            )

            # Handle year range
            if year_range:
                search_filters.year_start = year_range[0]
                search_filters.year_end = year_range[1]

            # Additional kwargs
            for key, value in kwargs.items():
                if hasattr(search_filters, key):
                    setattr(search_filters, key, value)
        
        # Handle mode override
        original_mode = self.fallback_mode
        if mode is not None:
            self.fallback_mode = mode
        
        try:
            return self.search_with_filters(search_filters)
        finally:
            # Restore original mode
            if mode is not None:
                self.fallback_mode = original_mode

    def search_with_filters(self, filters: SearchFilters) -> SearchResult:
        """
        Search with a SearchFilters object.

        Args:
            filters: SearchFilters object

        Returns:
            SearchResult object
        """
        self.logger.info(
            f"Searching with mode '{self.fallback_mode}' " f"across {len(self.clients)} databases"
        )

        if self.fallback_mode == "parallel":
            return self._search_parallel(filters)
        elif self.fallback_mode == "sequential":
            return self._search_sequential(filters)
        elif self.fallback_mode == "first":
            return self._search_first(filters)
        else:
            raise ConfigurationError(f"Invalid fallback_mode: {self.fallback_mode}")

    def _search_parallel(self, filters: SearchFilters) -> SearchResult:
        """Search all databases in parallel and merge results."""
        results = SearchResult(query_info={"filters": filters.model_dump()}, databases_queried=[])

        # Execute searches in parallel
        with ThreadPoolExecutor(max_workers=len(self.clients)) as executor:
            future_to_db = {
                executor.submit(client.search, filters): db_name
                for db_name, client in self.clients.items()
            }

            for future in as_completed(future_to_db):
                db_name = future_to_db[future]
                try:
                    db_result = future.result()
                    results.databases_queried.append(db_name)
                    results.extend(db_result.papers)
                    self.logger.info(f"Got {len(db_result.papers)} results from {db_name}")
                except Exception as e:
                    self.logger.error(f"Search failed for {db_name}: {e}")
                    if self.config.fail_fast:
                        raise SearchError(f"Search failed for {db_name}: {e}")

        # Deduplicate by DOI
        results = self._deduplicate_results(results)

        # Filter by required fields if specified
        if filters.required_fields:
            results = results.filter_by_required_fields(filters.required_fields)

        return results

    def _search_sequential(self, filters: SearchFilters) -> SearchResult:
        """Search databases sequentially with fallback."""
        results = SearchResult(query_info={"filters": filters.model_dump()}, databases_queried=[])

        for db_name, client in self.clients.items():
            try:
                self.logger.info(f"Searching {db_name}...")
                db_result = client.search(filters)
                results.databases_queried.append(db_name)
                results.extend(db_result.papers)

                self.logger.info(f"Got {len(db_result.papers)} results from {db_name}")

                # If we got results and not in fallback mode, we're done
                if db_result.papers and not self.config.fail_fast:
                    break

            except Exception as e:
                self.logger.error(f"Search failed for {db_name}: {e}")
                if self.config.fail_fast:
                    raise SearchError(f"Search failed for {db_name}: {e}")
                # Continue to next database

        # Deduplicate
        results = self._deduplicate_results(results)

        # Filter by required fields
        if filters.required_fields:
            results = results.filter_by_required_fields(filters.required_fields)

        return results

    def _search_first(self, filters: SearchFilters) -> SearchResult:
        """Search only the first database."""
        if not self.clients:
            raise SearchError("No databases configured")

        db_name = list(self.clients.keys())[0]
        client = self.clients[db_name]

        try:
            self.logger.info(f"Searching {db_name}...")
            results = client.search(filters)
            results.databases_queried = [db_name]

            # Filter by required fields
            if filters.required_fields:
                results = results.filter_by_required_fields(filters.required_fields)

            return results
        except Exception as e:
            raise SearchError(f"Search failed for {db_name}: {e}")

    def _deduplicate_results(self, results: SearchResult) -> SearchResult:
        """
        Deduplicate papers by DOI and other identifiers.

        Args:
            results: SearchResult with potentially duplicate papers

        Returns:
            Deduplicated SearchResult
        """
        seen_ids = set()
        unique_papers = []

        for paper in results.papers:
            # Create identifier tuple
            paper_id = (
                paper.doi or "",
                paper.pmid or "",
                paper.arxiv_id or "",
                paper.title.lower() if paper.title else "",
            )

            # Check if we've seen this paper
            if paper_id not in seen_ids and any(paper_id):
                seen_ids.add(paper_id)
                unique_papers.append(paper)

        results.papers = unique_papers
        results.total_results = len(unique_papers)

        self.logger.info(
            f"Deduplicated {len(results.papers)} papers " f"from {len(seen_ids)} unique identifiers"
        )

        return results

    def get_by_doi(self, doi: str, databases: Optional[List[str]] = None) -> Optional[Paper]:
        """
        Get a paper by DOI from specified databases.

        Args:
            doi: Digital Object Identifier
            databases: List of databases to try (default: all)

        Returns:
            Paper object or None
        """
        db_list = databases or list(self.clients.keys())

        for db_name in db_list:
            if db_name not in self.clients:
                continue

            try:
                paper = self.clients[db_name].get_by_doi(doi)
                if paper:
                    self.logger.info(f"Found paper with DOI {doi} in {db_name}")
                    return paper
            except Exception as e:
                self.logger.warning(f"Failed to get DOI {doi} from {db_name}: {e}")

        return None

    def batch_lookup(
        self, identifiers: List[str], id_type: str = "doi", databases: Optional[List[str]] = None
    ) -> SearchResult:
        """
        Look up multiple papers by identifier.

        Args:
            identifiers: List of identifiers
            id_type: Type of identifier (doi, pmid, arxiv, etc.)
            databases: List of databases to use (default: all)

        Returns:
            SearchResult with found papers
        """
        db_list = databases or list(self.clients.keys())

        results = SearchResult(
            query_info={"identifiers": identifiers, "id_type": id_type}, databases_queried=[]
        )

        for db_name in db_list:
            if db_name not in self.clients:
                continue

            try:
                db_result = self.clients[db_name].batch_lookup(identifiers, id_type)
                results.databases_queried.append(db_name)
                results.extend(db_result.papers)
                self.logger.info(f"Got {len(db_result.papers)} results from {db_name}")
            except Exception as e:
                self.logger.error(f"Batch lookup failed for {db_name}: {e}")

        # Deduplicate
        results = self._deduplicate_results(results)

        return results

    def get_client(self, database: str) -> Optional[DatabaseClient]:
        """
        Get a specific database client.

        Args:
            database: Database name

        Returns:
            DatabaseClient instance or None
        """
        return self.clients.get(database.lower())

    def close(self) -> None:
        """Close all database client sessions."""
        for client in self.clients.values():
            try:
                client.close()
            except Exception as e:
                self.logger.error(f"Error closing client: {e}")

    def __enter__(self) -> "UnifiedSearchClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
