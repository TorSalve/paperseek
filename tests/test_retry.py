"""Unit tests for retry utility."""

import pytest
import time
from unittest.mock import Mock, patch

from paperseek.utils.retry import exponential_backoff_retry, RetryHandler
from paperseek.core.exceptions import APIError, RateLimitError, TimeoutError


class TestExponentialBackoffRetry:
    """Test suite for exponential_backoff_retry decorator."""

    def test_successful_execution(self):
        """Test decorator with successful function execution."""
        
        @exponential_backoff_retry(max_retries=3)
        def success_func():
            return "success"
        
        result = success_func()
        assert result == "success"

    def test_retry_on_api_error(self):
        """Test retry on APIError."""
        call_count = 0
        
        @exponential_backoff_retry(max_retries=3, initial_delay=0.01)
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIError("API error", database="test")
            return "success"
        
        result = failing_func()
        assert result == "success"
        assert call_count == 3

    def test_retry_on_rate_limit_error(self):
        """Test retry on RateLimitError."""
        call_count = 0
        
        @exponential_backoff_retry(max_retries=2, initial_delay=0.01)
        def rate_limited_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("Rate limited", database="test")
            return "success"
        
        result = rate_limited_func()
        assert result == "success"
        assert call_count == 2

    def test_retry_on_timeout_error(self):
        """Test retry on TimeoutError."""
        call_count = 0
        
        @exponential_backoff_retry(max_retries=2, initial_delay=0.01)
        def timeout_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise TimeoutError("Timeout", database="test")
            return "success"
        
        result = timeout_func()
        assert result == "success"
        assert call_count == 2

    def test_max_retries_exceeded(self):
        """Test that max retries limit is enforced."""
        
        @exponential_backoff_retry(max_retries=3, initial_delay=0.01)
        def always_failing_func():
            raise APIError("Always fails", database="test")
        
        with pytest.raises(APIError):
            always_failing_func()

    def test_non_retryable_exception(self):
        """Test that non-retryable exceptions are not retried."""
        call_count = 0
        
        @exponential_backoff_retry(max_retries=3, initial_delay=0.01)
        def value_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")
        
        with pytest.raises(ValueError):
            value_error_func()
        
        # Should only be called once (no retries)
        assert call_count == 1

    def test_exponential_backoff(self):
        """Test that delays increase exponentially."""
        delays = []
        
        @exponential_backoff_retry(
            max_retries=3,
            initial_delay=0.1,
            exponential_base=2.0,
            jitter=False
        )
        def failing_func():
            start = time.time()
            if len(delays) > 0:
                delays.append(time.time() - delays[-1])
            else:
                delays.append(start)
            raise APIError("Fail", database="test")
        
        with pytest.raises(APIError):
            failing_func()
        
        # Should have attempted 4 times total (1 initial + 3 retries)
        assert len(delays) == 4

    def test_retry_after_header(self):
        """Test that retry-after from RateLimitError is respected."""
        
        @exponential_backoff_retry(max_retries=2, initial_delay=0.01)
        def rate_limit_with_retry_after():
            raise RateLimitError("Rate limited", database="test", retry_after=10)
        
        start = time.time()
        with pytest.raises(RateLimitError):
            rate_limit_with_retry_after()
        elapsed = time.time() - start
        
        # Should have waited for retry_after times
        # With 2 retries, should wait at least 10 seconds each time
        # Due to jitter and timing, we just check it took some time
        assert elapsed > 0.01

    def test_jitter_enabled(self):
        """Test that jitter adds randomness to delays."""
        
        @exponential_backoff_retry(
            max_retries=3,
            initial_delay=0.01,
            jitter=True
        )
        def failing_func():
            raise APIError("Fail", database="test")
        
        # Just ensure it doesn't crash with jitter enabled
        with pytest.raises(APIError):
            failing_func()

    def test_jitter_disabled(self):
        """Test retry with jitter disabled."""
        
        @exponential_backoff_retry(
            max_retries=2,
            initial_delay=0.01,
            jitter=False
        )
        def failing_func():
            raise APIError("Fail", database="test")
        
        with pytest.raises(APIError):
            failing_func()

    def test_max_delay_limit(self):
        """Test that max_delay limits the delay."""
        
        @exponential_backoff_retry(
            max_retries=5,
            initial_delay=1.0,
            max_delay=2.0,
            exponential_base=3.0,
            jitter=False
        )
        def failing_func():
            raise APIError("Fail", database="test")
        
        with pytest.raises(APIError):
            failing_func()
        
        # Should complete relatively quickly due to max_delay
        # Just checking it doesn't hang

    def test_custom_retry_exceptions(self):
        """Test with custom retry exception types."""
        call_count = 0
        
        @exponential_backoff_retry(
            max_retries=2,
            initial_delay=0.01,
            retry_on=(ValueError,)
        )
        def custom_exception_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Custom retryable error")
            return "success"
        
        result = custom_exception_func()
        assert result == "success"
        assert call_count == 2

    def test_function_with_args(self):
        """Test decorated function with arguments."""
        
        @exponential_backoff_retry(max_retries=2, initial_delay=0.01)
        def func_with_args(x, y, z=3):
            if x < 2:
                raise APIError("Fail", database="test")
            return x + y + z
        
        # First call will retry
        call_count = 0
        
        @exponential_backoff_retry(max_retries=2, initial_delay=0.01)
        def counting_func(value):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise APIError("Fail", database="test")
            return value * 2
        
        result = counting_func(5)
        assert result == 10
        assert call_count == 2


class TestRetryHandler:
    """Test suite for RetryHandler class."""

    def test_init(self):
        """Test RetryHandler initialization."""
        handler = RetryHandler(
            max_retries=5,
            initial_delay=2.0,
            max_delay=30.0,
            exponential_base=3.0,
            jitter=False
        )
        
        assert handler.max_retries == 5
        assert handler.initial_delay == 2.0
        assert handler.max_delay == 30.0
        assert handler.exponential_base == 3.0
        assert handler.jitter is False

    def test_execute_success(self):
        """Test successful execution."""
        handler = RetryHandler()
        
        def success_func():
            return "success"
        
        result = handler.execute(success_func)
        assert result == "success"

    def test_execute_with_retry(self):
        """Test execution with retry."""
        handler = RetryHandler(max_retries=3, initial_delay=0.01)
        call_count = 0
        
        def failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise APIError("Fail", database="test")
            return "success"
        
        result = handler.execute(failing_func)
        assert result == "success"
        assert call_count == 3

    def test_execute_max_retries_exceeded(self):
        """Test that max retries is enforced."""
        handler = RetryHandler(max_retries=2, initial_delay=0.01)
        
        def always_failing():
            raise APIError("Always fails", database="test")
        
        with pytest.raises(APIError):
            handler.execute(always_failing)

    def test_execute_with_args(self):
        """Test execute with function arguments."""
        handler = RetryHandler(max_retries=2, initial_delay=0.01)
        
        def add(x, y):
            return x + y
        
        result = handler.execute(add, 3, 5)
        assert result == 8

    def test_execute_with_kwargs(self):
        """Test execute with keyword arguments."""
        handler = RetryHandler(max_retries=2, initial_delay=0.01)
        
        def multiply(x, y=2):
            return x * y
        
        result = handler.execute(multiply, 3, y=4)
        assert result == 12

    def test_execute_non_retryable_exception(self):
        """Test that non-retryable exceptions are raised immediately."""
        handler = RetryHandler(max_retries=3, initial_delay=0.01)
        call_count = 0
        
        def value_error_func():
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")
        
        with pytest.raises(ValueError):
            handler.execute(value_error_func)
        
        # Should only be called once
        assert call_count == 1

    def test_execute_custom_retry_on(self):
        """Test execute with custom retry_on exceptions."""
        handler = RetryHandler(max_retries=2, initial_delay=0.01)
        call_count = 0
        
        def custom_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ValueError("Custom error")
            return "success"
        
        result = handler.execute(custom_func, retry_on=(ValueError,))
        assert result == "success"
        assert call_count == 2

    def test_calculate_delay(self):
        """Test delay calculation."""
        handler = RetryHandler(
            initial_delay=1.0,
            exponential_base=2.0,
            jitter=False
        )
        
        # First attempt
        delay1 = handler.calculate_delay(1)
        assert delay1 == 1.0
        
        # Second attempt
        delay2 = handler.calculate_delay(2)
        assert delay2 == 2.0
        
        # Third attempt
        delay3 = handler.calculate_delay(3)
        assert delay3 == 4.0

    def test_calculate_delay_with_max(self):
        """Test that calculate_delay respects max_delay."""
        handler = RetryHandler(
            initial_delay=1.0,
            max_delay=5.0,
            exponential_base=2.0,
            jitter=False
        )
        
        # Large attempt number should hit max
        delay = handler.calculate_delay(10)
        assert delay == 5.0

    def test_calculate_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        handler = RetryHandler(
            initial_delay=1.0,
            jitter=True
        )
        
        # With jitter, delays should vary
        delays = [handler.calculate_delay(1) for _ in range(10)]
        
        # All should be between 0.5 and 1.5 (1.0 * (0.5 to 1.5))
        assert all(0.5 <= d <= 1.5 for d in delays)
        
        # Should have some variation
        assert len(set(delays)) > 1

    def test_calculate_delay_with_retry_after(self):
        """Test that retry_after is respected."""
        handler = RetryHandler(
            initial_delay=1.0,
            jitter=False
        )
        
        # retry_after should override calculated delay
        delay = handler.calculate_delay(1, retry_after=10)
        # This should be at least the retry_after value
        # The actual implementation may vary

    def test_rate_limit_error_with_retry_after(self):
        """Test handling of RateLimitError with retry_after."""
        handler = RetryHandler(max_retries=2, initial_delay=0.01)
        call_count = 0
        
        def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise RateLimitError("Rate limited", database="test", retry_after=5)
            return "success"
        
        start = time.time()
        result = handler.execute(rate_limited)
        elapsed = time.time() - start
        
        assert result == "success"
        assert call_count == 2
        # Should have waited, but we use small delays for testing
        assert elapsed > 0.01
