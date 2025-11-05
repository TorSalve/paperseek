"""Retry logic with exponential backoff."""

import time
import random
from typing import Any, Callable, Optional, Type, Tuple
from functools import wraps
import logging

from ..core.exceptions import RateLimitError, APIError, TimeoutError

logger = logging.getLogger(__name__)


def exponential_backoff_retry(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retry_on: Tuple[Type[Exception], ...] = (APIError, RateLimitError, TimeoutError),
) -> Callable:
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Add random jitter to delay
        retry_on: Tuple of exception types to retry on

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            retries = 0
            delay = initial_delay

            while True:
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    retries += 1

                    if retries > max_retries:
                        logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}")
                        raise

                    # Calculate delay with exponential backoff
                    current_delay = min(delay * (exponential_base ** (retries - 1)), max_delay)

                    # Add jitter
                    if jitter:
                        current_delay *= 0.5 + random.random()

                    # Check for rate limit retry-after header
                    if isinstance(e, RateLimitError) and e.retry_after:
                        current_delay = max(current_delay, e.retry_after)

                    logger.warning(
                        f"Retry {retries}/{max_retries} for {func.__name__} "
                        f"after {current_delay:.2f}s due to: {str(e)}"
                    )

                    time.sleep(current_delay)
                except Exception as e:
                    # Don't retry on other exceptions
                    logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                    raise

        return wrapper

    return decorator


class RetryHandler:
    """
    Class-based retry handler for more complex scenarios.
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
    ):
        """
        Initialize retry handler.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential calculation
            jitter: Add random jitter to delay
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.logger = logging.getLogger(__name__)

    def execute(
        self,
        func: Callable,
        *args: Any,
        retry_on: Tuple[Type[Exception], ...] = (APIError, RateLimitError, TimeoutError),
        **kwargs: Any,
    ) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            *args: Positional arguments for function
            retry_on: Tuple of exception types to retry on
            **kwargs: Keyword arguments for function

        Returns:
            Function result
        """
        retries = 0
        delay = self.initial_delay

        while True:
            try:
                return func(*args, **kwargs)
            except retry_on as e:
                retries += 1

                if retries > self.max_retries:
                    self.logger.error(
                        f"Max retries ({self.max_retries}) exceeded for {func.__name__}"
                    )
                    raise

                # Calculate delay
                current_delay = min(
                    delay * (self.exponential_base ** (retries - 1)), self.max_delay
                )

                if self.jitter:
                    current_delay *= 0.5 + random.random()

                if isinstance(e, RateLimitError) and e.retry_after:
                    current_delay = max(current_delay, e.retry_after)

                self.logger.warning(
                    f"Retry {retries}/{self.max_retries} for {func.__name__} "
                    f"after {current_delay:.2f}s due to: {str(e)}"
                )

                time.sleep(current_delay)
            except Exception as e:
                self.logger.error(f"Non-retryable error in {func.__name__}: {str(e)}")
                raise

    def calculate_delay(self, attempt: int, retry_after: Optional[int] = None) -> float:
        """
        Calculate delay for a given retry attempt.

        Args:
            attempt: Retry attempt number (1-indexed)
            retry_after: Optional retry-after value from API

        Returns:
            Delay in seconds
        """
        delay = min(self.initial_delay * (self.exponential_base ** (attempt - 1)), self.max_delay)

        if self.jitter:
            delay *= 0.5 + random.random()

        if retry_after:
            delay = max(delay, retry_after)

        return delay
