"""Base class for database clients."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import Paper, SearchFilters, SearchResult
from .config import DatabaseConfig
from .exceptions import APIError, RateLimitError, TimeoutError, AuthenticationError
from ..utils.rate_limiter import RateLimiter
from ..utils.logging import get_logger
from ..utils.session_pool import SessionPool


class DatabaseClient(ABC):
    """
    Abstract base class for database-specific clients.

    All database clients must implement the abstract methods.
    """

    def __init__(
        self,
        config: DatabaseConfig,
        email: Optional[str] = None,
        user_agent: str = "AcademicSearchUnified/0.1.0",
    ):
        """
        Initialize database client.

        Args:
            config: Database-specific configuration
            email: Email for polite API requests
            user_agent: User agent string
        """
        self.config = config
        self.email = email
        self.user_agent = user_agent
        self.logger = get_logger(self.__class__.__name__)

        # Set up rate limiter
        self.rate_limiter = RateLimiter(
            requests_per_second=config.rate_limit_per_second,
            requests_per_minute=config.rate_limit_per_minute,
        )

        # Get shared session from pool
        self.session = self._get_or_create_session()

    def _get_or_create_session(self) -> requests.Session:
        """
        Get session from pool or create a new one with retry configuration.
        
        Uses SessionPool for better connection reuse and memory efficiency.
        """
        # Get shared session from pool
        session = SessionPool.get_session(
            database=self.database_name,
            pool_connections=10,
            pool_maxsize=20,
            max_retries=0,  # We handle retries via HTTPAdapter below
        )

        # Configure retry strategy if not already configured
        # Check if session already has our retry adapter
        if not hasattr(session, '_retry_configured'):
            retry_strategy = Retry(
                total=self.config.max_retries,
                backoff_factor=self.config.retry_delay,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "POST", "HEAD"],
            )

            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)
            
            # Mark as configured to avoid reconfiguration
            session._retry_configured = True  # type: ignore

        # Update headers (this is safe to do multiple times)
        session.headers.update({"User-Agent": self._get_user_agent()})

        return session

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry configuration.
        
        Deprecated: Use _get_or_create_session() instead.
        This method is kept for backward compatibility.
        """
        session = requests.Session()

        # Configure retries for connection errors
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=self.config.retry_delay,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "HEAD"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Set default headers
        headers = {"User-Agent": self._get_user_agent()}
        session.headers.update(headers)

        return session

    def _get_user_agent(self) -> str:
        """Get user agent string with email if available."""
        if self.email:
            return f"{self.user_agent} (mailto:{self.email})"
        return self.user_agent

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """
        Make an HTTP request with rate limiting and error handling.

        Args:
            url: Request URL
            method: HTTP method
            params: Query parameters
            headers: Additional headers
            json_data: JSON data for POST requests
            timeout: Request timeout

        Returns:
            Response object

        Raises:
            APIError: On API errors
            RateLimitError: On rate limit errors
            TimeoutError: On timeout
            AuthenticationError: On authentication errors
        """
        # Wait for rate limiter
        self.rate_limiter.wait_if_needed()

        # Prepare request
        timeout = timeout or self.config.timeout
        headers = headers or {}

        try:
            self.logger.debug(f"Making {method} request to {url}")

            response = self.session.request(
                method=method,
                url=url,
                params=params,
                headers=headers,
                json=json_data,
                timeout=timeout,
            )

            # Handle response
            self._check_response(response)

            return response

        except requests.exceptions.Timeout as e:
            raise TimeoutError(
                f"Request timed out after {timeout}s", database=self.database_name
            ) from e
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {str(e)}", database=self.database_name) from e

    def _check_response(self, response: requests.Response) -> None:
        """
        Check response for errors.

        Args:
            response: Response object

        Raises:
            RateLimitError: On rate limit (429)
            AuthenticationError: On auth errors (401, 403)
            APIError: On other errors
        """
        if response.status_code == 429:
            retry_after = response.headers.get("Retry-After")
            retry_after_int = int(retry_after) if retry_after else None
            raise RateLimitError(
                "Rate limit exceeded", database=self.database_name, retry_after=retry_after_int
            )

        if response.status_code in [401, 403]:
            raise AuthenticationError(
                f"Authentication failed: {response.text}", database=self.database_name
            )

        if not response.ok:
            raise APIError(
                f"API request failed: {response.status_code} - {response.text}",
                database=self.database_name,
                status_code=response.status_code,
            )

    @property
    @abstractmethod
    def database_name(self) -> str:
        """Return the name of the database."""
        pass

    @abstractmethod
    def search(self, filters: SearchFilters) -> SearchResult:
        """
        Search the database with given filters.

        Args:
            filters: Search filters

        Returns:
            SearchResult object
        """
        pass

    @abstractmethod
    def get_by_doi(self, doi: str) -> Optional[Paper]:
        """
        Get a paper by DOI.

        Args:
            doi: Digital Object Identifier

        Returns:
            Paper object or None if not found
        """
        pass

    @abstractmethod
    def get_by_identifier(self, identifier: str, id_type: str) -> Optional[Paper]:
        """
        Get a paper by identifier.

        Args:
            identifier: The identifier value
            id_type: Type of identifier (doi, pmid, arxiv, etc.)

        Returns:
            Paper object or None if not found
        """
        pass

    @abstractmethod
    def batch_lookup(self, identifiers: List[str], id_type: str) -> SearchResult:
        """
        Look up multiple papers by identifier.

        Args:
            identifiers: List of identifiers
            id_type: Type of identifier

        Returns:
            SearchResult with found papers
        """
        pass

    @abstractmethod
    def _normalize_paper(self, raw_data: Dict[str, Any]) -> Paper:
        """
        Normalize raw API response to Paper model.

        Args:
            raw_data: Raw data from API

        Returns:
            Normalized Paper object
        """
        pass

    def supports_field(self, field_name: str) -> bool:
        """
        Check if this database typically provides a specific field.

        Args:
            field_name: Name of the field

        Returns:
            True if field is typically available
        """
        # Default implementation - can be overridden by subclasses
        return True

    def get_supported_fields(self) -> List[str]:
        """
        Get list of fields typically provided by this database.

        Returns:
            List of field names
        """
        # Default implementation - can be overridden by subclasses
        return [
            "title",
            "authors",
            "abstract",
            "year",
            "doi",
            "venue",
            "journal",
            "conference",
            "citation_count",
        ]

    def close(self) -> None:
        """
        Close the client session.
        
        Note: Since we use SessionPool, we don't actually close the session
        as it's shared. The session will be closed when SessionPool.close_all_sessions()
        is called during application shutdown.
        """
        # Don't close the session as it's shared via SessionPool
        pass

    def __enter__(self) -> "DatabaseClient":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
