"""Custom exception classes for the academic search package."""

from typing import Optional


class AcademicSearchError(Exception):
    """Base exception class for all academic search errors."""

    pass


class ConfigurationError(AcademicSearchError):
    """Raised when there is an error in configuration."""

    pass


class DatabaseError(AcademicSearchError):
    """Base exception for database-related errors."""

    def __init__(self, message: str, database: str) -> None:
        self.database = database
        super().__init__(f"[{database}] {message}")


class RateLimitError(DatabaseError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str, database: str, retry_after: Optional[int] = None) -> None:
        self.retry_after = retry_after
        super().__init__(message, database)


class APIError(DatabaseError):
    """Raised when an API request fails."""

    def __init__(self, message: str, database: str, status_code: Optional[int] = None) -> None:
        self.status_code = status_code
        super().__init__(message, database)


class AuthenticationError(DatabaseError):
    """Raised when authentication fails."""

    pass


class ValidationError(AcademicSearchError):
    """Raised when input validation fails."""

    pass


class ExportError(AcademicSearchError):
    """Raised when export operation fails."""

    pass


class SearchError(AcademicSearchError):
    """Raised when a search operation fails."""

    pass


class TimeoutError(DatabaseError):
    """Raised when a request times out."""

    pass
