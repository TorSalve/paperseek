"""Shared HTTP session pool for efficient connection reuse.

This module provides a session pool that can be shared across database clients,
reducing memory usage and improving connection reuse efficiency. Instead of each
client creating its own requests.Session, they can request a shared session from
the pool.
"""

import requests
from requests.adapters import HTTPAdapter
from threading import Lock
from typing import Dict, Optional


class SessionPool:
    """
    Thread-safe HTTP session pool for database clients.

    This singleton class manages a pool of requests.Session objects, one per
    database. Sessions are configured with connection pooling and proper adapters.

    Benefits:
    - Reduced memory usage (one session per database, not per client instance)
    - Better connection reuse across multiple requests
    - Centralized session configuration
    - Thread-safe access

    Example:
        >>> session = SessionPool.get_session("arxiv")
        >>> response = session.get("https://export.arxiv.org/api/query")
    """

    _instance: Optional["SessionPool"] = None
    _lock: Lock = Lock()
    _sessions: Dict[str, requests.Session] = {}

    def __new__(cls) -> "SessionPool":
        """Ensure singleton pattern."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._sessions = {}
        return cls._instance

    @classmethod
    def get_session(
        cls,
        database: str,
        pool_connections: int = 10,
        pool_maxsize: int = 20,
        max_retries: int = 0,
    ) -> requests.Session:
        """
        Get or create a session for the specified database.

        Sessions are cached and reused for the same database name. Configuration
        parameters only apply when creating a new session; subsequent calls with
        the same database name will return the existing session regardless of
        parameter values.

        Args:
            database: Database identifier (e.g., "arxiv", "pubmed", "crossref")
            pool_connections: Number of connection pools to cache
            pool_maxsize: Maximum number of connections in each pool
            max_retries: Number of retries (0 = no retries, handled elsewhere)

        Returns:
            Configured requests.Session object

        Example:
            >>> session = SessionPool.get_session("semantic_scholar")
            >>> # Session is cached and reused for subsequent calls
            >>> same_session = SessionPool.get_session("semantic_scholar")
            >>> assert session is same_session
        """
        with cls._lock:
            if database not in cls._sessions:
                # Create new session with proper configuration
                session = requests.Session()

                # Configure HTTP adapter with connection pooling
                adapter = HTTPAdapter(
                    pool_connections=pool_connections,
                    pool_maxsize=pool_maxsize,
                    max_retries=max_retries,
                    pool_block=False,  # Don't block when pool is full
                )

                # Mount adapter for both HTTP and HTTPS
                session.mount("http://", adapter)
                session.mount("https://", adapter)

                # Store in pool
                cls._sessions[database] = session

            return cls._sessions[database]

    @classmethod
    def close_session(cls, database: str) -> None:
        """
        Close and remove a session from the pool.

        This is useful for cleanup or if a session needs to be recreated with
        different configuration.

        Args:
            database: Database identifier

        Example:
            >>> SessionPool.close_session("arxiv")
        """
        with cls._lock:
            if database in cls._sessions:
                session = cls._sessions.pop(database)
                session.close()

    @classmethod
    def close_all_sessions(cls) -> None:
        """
        Close all sessions in the pool.

        This should be called during application shutdown to properly clean up
        resources.

        Example:
            >>> # At application shutdown
            >>> SessionPool.close_all_sessions()
        """
        with cls._lock:
            for session in cls._sessions.values():
                session.close()
            cls._sessions.clear()

    @classmethod
    def get_pool_size(cls) -> int:
        """
        Get the number of sessions in the pool.

        Returns:
            Number of cached sessions

        Example:
            >>> size = SessionPool.get_pool_size()
            >>> print(f"Pool contains {size} sessions")
        """
        with cls._lock:
            return len(cls._sessions)

    @classmethod
    def get_database_names(cls) -> list[str]:
        """
        Get list of database names with active sessions.

        Returns:
            List of database identifiers

        Example:
            >>> databases = SessionPool.get_database_names()
            >>> print(f"Active sessions: {', '.join(databases)}")
        """
        with cls._lock:
            return list(cls._sessions.keys())

    @classmethod
    def reset(cls) -> None:
        """
        Reset the session pool (mainly for testing).

        Closes all sessions and clears the pool.

        Warning:
            This method should only be used in tests or during application
            restart. Don't call this during normal operation as it will close
            active connections.
        """
        cls.close_all_sessions()


# Convenience function for common usage
def get_session(database: str) -> requests.Session:
    """
    Convenience function to get a session from the pool.

    This is a shorthand for SessionPool.get_session(database).

    Args:
        database: Database identifier

    Returns:
        Configured requests.Session object

    Example:
        >>> from paperseek.utils.session_pool import get_session
        >>> session = get_session("crossref")
        >>> response = session.get("https://api.crossref.org/works")
    """
    return SessionPool.get_session(database)
