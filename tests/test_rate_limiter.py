"""Unit tests for RateLimiter."""

import pytest
import time
from unittest.mock import patch, Mock

from paperseek.utils.rate_limiter import RateLimiter, DatabaseRateLimiter


class TestRateLimiter:
    """Test suite for RateLimiter."""

    @patch('paperseek.utils.rate_limiter.Limiter')
    def test_init_with_per_second(self, mock_limiter_class):
        """Test rate limiter initialization with per-second limit."""
        mock_limiter = Mock()
        mock_limiter_class.return_value = mock_limiter
        
        limiter = RateLimiter(requests_per_second=2.0)
        assert limiter.requests_per_second == 2.0

    @patch('paperseek.utils.rate_limiter.Limiter')
    def test_init_with_per_minute(self, mock_limiter_class):
        """Test rate limiter initialization with per-minute limit."""
        mock_limiter = Mock()
        mock_limiter_class.return_value = mock_limiter
        
        limiter = RateLimiter(requests_per_minute=120.0)
        assert limiter.requests_per_minute == 120.0

    @patch('paperseek.utils.rate_limiter.Limiter')
    def test_init_with_both_limits(self, mock_limiter_class):
        """Test initialization with both per-second and per-minute limits."""
        mock_limiter = Mock()
        mock_limiter_class.return_value = mock_limiter
        
        limiter = RateLimiter(requests_per_second=2.0, requests_per_minute=100.0)
        assert limiter.requests_per_second == 2.0
        assert limiter.requests_per_minute == 100.0

    def test_init_no_limits(self):
        """Test initialization with no rate limits."""
        limiter = RateLimiter()
        assert limiter.limiter is None

    @patch('paperseek.utils.rate_limiter.Limiter')
    def test_wait_if_needed_with_limiter(self, mock_limiter_class):
        """Test wait_if_needed with active limiter."""
        mock_limiter = Mock()
        mock_limiter_class.return_value = mock_limiter
        
        limiter = RateLimiter(requests_per_second=10.0)
        
        # Should not raise
        limiter.wait_if_needed()
        limiter.wait_if_needed()
        
        # Verify the limiter was called
        assert mock_limiter.try_acquire.call_count == 2

    def test_wait_if_needed_without_limiter(self):
        """Test wait_if_needed with no limiter (no limits)."""
        limiter = RateLimiter()
        
        # Should return immediately
        start = time.time()
        for _ in range(10):
            limiter.wait_if_needed()
        elapsed = time.time() - start
        
        assert elapsed < 0.1  # Should be very fast


class TestDatabaseRateLimiter:
    """Test suite for DatabaseRateLimiter."""

    def test_init(self):
        """Test database rate limiter initialization."""
        manager = DatabaseRateLimiter()
        assert manager._limiters == {}

    @patch('paperseek.utils.rate_limiter.Limiter')
    def test_add_database(self, mock_limiter_class):
        """Test adding a database with rate limits."""
        # Mock the Limiter to avoid background thread issues
        mock_limiter = Mock()
        mock_limiter_class.return_value = mock_limiter
        
        manager = DatabaseRateLimiter()
        
        # Create a mock RateLimiter with the mocked Limiter
        mock_rate_limiter = Mock()
        mock_rate_limiter.requests_per_second = 5.0
        mock_rate_limiter.limiter = mock_limiter
        
        with patch('paperseek.utils.rate_limiter.RateLimiter') as mock_rl:
            mock_rl.return_value = mock_rate_limiter
            manager.add_database("test_db", requests_per_second=5.0)
        
        assert "test_db" in manager._limiters

    @patch('paperseek.utils.rate_limiter.RateLimiter')
    def test_add_multiple_databases(self, mock_rl):
        """Test adding multiple databases."""
        mock_limiter1 = Mock()
        mock_limiter2 = Mock()
        mock_rl.side_effect = [mock_limiter1, mock_limiter2]
        
        manager = DatabaseRateLimiter()
        manager.add_database("db1", requests_per_second=5.0)
        manager.add_database("db2", requests_per_minute=100.0)
        
        assert len(manager._limiters) == 2
        assert "db1" in manager._limiters
        assert "db2" in manager._limiters

    @patch('paperseek.utils.rate_limiter.RateLimiter')
    def test_update_existing_database(self, mock_rl):
        """Test updating rate limits for existing database."""
        mock_limiter1 = Mock()
        mock_limiter2 = Mock()
        mock_rl.side_effect = [mock_limiter1, mock_limiter2]
        
        manager = DatabaseRateLimiter()
        manager.add_database("test_db", requests_per_second=5.0)
        manager.add_database("test_db", requests_per_second=10.0)
        
        # Should have replaced the limiter
        assert "test_db" in manager._limiters

    @patch('paperseek.utils.rate_limiter.RateLimiter')
    def test_wait_if_needed_for_database(self, mock_rl):
        """Test waiting for specific database."""
        mock_limiter = Mock()
        mock_rl.return_value = mock_limiter
        
        manager = DatabaseRateLimiter()
        manager.add_database("test_db", requests_per_second=10.0)
        
        # Should not raise
        manager.wait_if_needed("test_db")
        mock_limiter.wait_if_needed.assert_called_once()

    def test_wait_if_needed_for_nonexistent_database(self):
        """Test waiting for database that doesn't exist."""
        manager = DatabaseRateLimiter()
        
        # Should not raise (no limiting for unknown databases)
        manager.wait_if_needed("unknown_db")
