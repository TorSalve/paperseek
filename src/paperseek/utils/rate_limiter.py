"""Rate limiting utilities for API requests."""

import time
from collections import deque
from threading import Lock
from typing import Dict, Optional

# Try to import pyrate_limiter, but fall back to simple implementation if issues
try:
    from pyrate_limiter import Duration, Limiter, Rate
    PYRATE_LIMITER_AVAILABLE = True
except (ImportError, AttributeError):
    PYRATE_LIMITER_AVAILABLE = False


class RateLimiter:
    """
    Thread-safe rate limiter for API requests.

    Supports both per-second and per-minute rate limits.
    Uses SimpleRateLimiter implementation due to pyrate_limiter compatibility issues.
    """

    def __init__(
        self,
        requests_per_second: Optional[float] = None,
        requests_per_minute: Optional[float] = None,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_second: Maximum requests per second
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_second = requests_per_second
        self.requests_per_minute = requests_per_minute

        # Use SimpleRateLimiter implementation directly
        self._simple_limiter = SimpleRateLimiter(
            requests_per_second=requests_per_second,
            requests_per_minute=requests_per_minute
        )

    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        self._simple_limiter.wait_if_needed()


class DatabaseRateLimiter:
    """
    Manages rate limiters for multiple databases.
    """

    def __init__(self):
        """Initialize database rate limiter manager."""
        self._limiters: Dict[str, RateLimiter] = {}
        self._lock = Lock()

    def add_database(
        self,
        database: str,
        requests_per_second: Optional[float] = None,
        requests_per_minute: Optional[float] = None,
    ) -> None:
        """
        Add or update rate limiter for a database.

        Args:
            database: Database name
            requests_per_second: Maximum requests per second
            requests_per_minute: Maximum requests per minute
        """
        with self._lock:
            self._limiters[database] = RateLimiter(
                requests_per_second=requests_per_second, requests_per_minute=requests_per_minute
            )

    def wait_if_needed(self, database: str) -> None:
        """
        Wait if rate limit would be exceeded for the database.

        Args:
            database: Database name
        """
        with self._lock:
            limiter = self._limiters.get(database)

        if limiter:
            limiter.wait_if_needed()

    def get_limiter(self, database: str) -> Optional[RateLimiter]:
        """Get rate limiter for a database."""
        with self._lock:
            return self._limiters.get(database)


class SimpleRateLimiter:
    """
    Simple rate limiter using sliding window algorithm.

    This is now the PRIMARY implementation used by RateLimiter due to
    compatibility issues with pyrate-limiter in Python 3.13+.

    Uses a simple sliding window approach without external dependencies.
    Tracks request timestamps in deques and enforces limits by checking
    window sizes before allowing new requests.
    """

    def __init__(
        self,
        requests_per_second: Optional[float] = None,
        requests_per_minute: Optional[float] = None,
    ):
        """
        Initialize simple rate limiter.

        Args:
            requests_per_second: Maximum requests per second
            requests_per_minute: Maximum requests per minute
        """
        self.requests_per_second = requests_per_second
        self.requests_per_minute = requests_per_minute

        self._second_window: deque = deque()
        self._minute_window: deque = deque()
        self._lock = Lock()

    def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        with self._lock:
            now = time.time()

            # Clean old entries
            if self.requests_per_second:
                self._clean_window(self._second_window, now, 1.0)
            if self.requests_per_minute:
                self._clean_window(self._minute_window, now, 60.0)

            # Check limits and wait if needed
            wait_time = 0.0

            if self.requests_per_second:
                if len(self._second_window) >= self.requests_per_second:
                    oldest = self._second_window[0]
                    wait_time = max(wait_time, 1.0 - (now - oldest))

            if self.requests_per_minute:
                if len(self._minute_window) >= self.requests_per_minute:
                    oldest = self._minute_window[0]
                    wait_time = max(wait_time, 60.0 - (now - oldest))

            if wait_time > 0:
                time.sleep(wait_time)
                now = time.time()

            # Record this request
            if self.requests_per_second:
                self._second_window.append(now)
            if self.requests_per_minute:
                self._minute_window.append(now)

    def _clean_window(self, window: deque, now: float, window_size: float) -> None:
        """Remove old entries from window."""
        while window and (now - window[0]) > window_size:
            window.popleft()
