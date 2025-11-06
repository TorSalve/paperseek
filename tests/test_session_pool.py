"""Tests for HTTP session pool."""

import pytest
import requests

from paperseek.utils.session_pool import SessionPool, get_session


class TestSessionPool:
    """Tests for SessionPool."""

    def setup_method(self):
        """Reset session pool before each test."""
        SessionPool.reset()

    def teardown_method(self):
        """Clean up after each test."""
        SessionPool.reset()

    def test_singleton_pattern(self):
        """Test that SessionPool follows singleton pattern."""
        pool1 = SessionPool()
        pool2 = SessionPool()
        assert pool1 is pool2

    def test_get_session_creates_new(self):
        """Test getting a session creates a new one if not exists."""
        session = SessionPool.get_session("test_db")
        assert isinstance(session, requests.Session)

    def test_get_session_returns_same(self):
        """Test getting same session returns cached instance."""
        session1 = SessionPool.get_session("test_db")
        session2 = SessionPool.get_session("test_db")
        assert session1 is session2

    def test_get_session_different_databases(self):
        """Test different databases get different sessions."""
        session1 = SessionPool.get_session("db1")
        session2 = SessionPool.get_session("db2")
        assert session1 is not session2

    def test_get_session_has_adapters(self):
        """Test that sessions have HTTP adapters mounted."""
        session = SessionPool.get_session("test_db")
        # Check that adapters are mounted
        assert "http://" in session.adapters
        assert "https://" in session.adapters

    def test_close_session(self):
        """Test closing a session removes it from pool."""
        SessionPool.get_session("test_db")
        assert SessionPool.get_pool_size() == 1
        
        SessionPool.close_session("test_db")
        assert SessionPool.get_pool_size() == 0

    def test_close_session_nonexistent(self):
        """Test closing a nonexistent session doesn't error."""
        # Should not raise an exception
        SessionPool.close_session("nonexistent")
        assert SessionPool.get_pool_size() == 0

    def test_close_all_sessions(self):
        """Test closing all sessions."""
        SessionPool.get_session("db1")
        SessionPool.get_session("db2")
        SessionPool.get_session("db3")
        assert SessionPool.get_pool_size() == 3
        
        SessionPool.close_all_sessions()
        assert SessionPool.get_pool_size() == 0

    def test_get_pool_size(self):
        """Test getting pool size."""
        assert SessionPool.get_pool_size() == 0
        
        SessionPool.get_session("db1")
        assert SessionPool.get_pool_size() == 1
        
        SessionPool.get_session("db2")
        assert SessionPool.get_pool_size() == 2

    def test_get_database_names(self):
        """Test getting database names."""
        SessionPool.get_session("arxiv")
        SessionPool.get_session("pubmed")
        SessionPool.get_session("crossref")
        
        names = SessionPool.get_database_names()
        assert set(names) == {"arxiv", "pubmed", "crossref"}

    def test_get_database_names_empty(self):
        """Test getting database names when pool is empty."""
        names = SessionPool.get_database_names()
        assert names == []

    def test_reset(self):
        """Test resetting the pool."""
        SessionPool.get_session("db1")
        SessionPool.get_session("db2")
        assert SessionPool.get_pool_size() == 2
        
        SessionPool.reset()
        assert SessionPool.get_pool_size() == 0

    def test_session_can_make_requests(self):
        """Test that sessions can actually make HTTP requests."""
        session = SessionPool.get_session("test_db")
        
        # Just verify the session is properly configured
        # We won't make actual network requests in tests
        assert hasattr(session, "get")
        assert hasattr(session, "post")
        assert callable(session.get)
        assert callable(session.post)

    def test_get_session_custom_pool_connections(self):
        """Test getting session with custom pool connections."""
        session = SessionPool.get_session("test_db", pool_connections=20)
        assert isinstance(session, requests.Session)
        # The session should exist and be configured

    def test_get_session_custom_pool_maxsize(self):
        """Test getting session with custom pool maxsize."""
        session = SessionPool.get_session("test_db", pool_maxsize=50)
        assert isinstance(session, requests.Session)

    def test_get_session_thread_safety(self):
        """Test that session pool is thread-safe."""
        import threading
        
        sessions = []
        
        def get_session_thread():
            session = SessionPool.get_session("test_db")
            sessions.append(session)
        
        threads = [threading.Thread(target=get_session_thread) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All threads should get the same session
        assert len(set(id(s) for s in sessions)) == 1

    def test_convenience_function(self):
        """Test the convenience get_session function."""
        session = get_session("test_db")
        assert isinstance(session, requests.Session)
        
        # Should be the same as using SessionPool directly
        session2 = SessionPool.get_session("test_db")
        assert session is session2

    def test_session_persistence_after_multiple_gets(self):
        """Test that session persists across multiple get calls."""
        session1 = SessionPool.get_session("persistent_db")
        session_id1 = id(session1)
        
        # Get the same session multiple times
        for _ in range(5):
            session = SessionPool.get_session("persistent_db")
            assert id(session) == session_id1

    def test_multiple_databases_isolation(self):
        """Test that different databases have isolated sessions."""
        databases = ["arxiv", "pubmed", "crossref", "openalex", "semantic_scholar"]
        sessions = {db: SessionPool.get_session(db) for db in databases}
        
        # All sessions should be different objects
        session_ids = [id(s) for s in sessions.values()]
        assert len(set(session_ids)) == len(databases)
        
        # Verify all databases are tracked
        assert set(SessionPool.get_database_names()) == set(databases)

    def test_close_and_recreate_session(self):
        """Test closing and recreating a session."""
        session1 = SessionPool.get_session("test_db")
        session_id1 = id(session1)
        
        SessionPool.close_session("test_db")
        
        session2 = SessionPool.get_session("test_db")
        session_id2 = id(session2)
        
        # Should be a different session object
        assert session_id1 != session_id2

    def test_session_has_correct_configuration(self):
        """Test that session has correct default configuration."""
        session = SessionPool.get_session("test_db")
        
        # Verify adapters exist
        http_adapter = session.get_adapter("http://example.com")
        https_adapter = session.get_adapter("https://example.com")
        
        assert http_adapter is not None
        assert https_adapter is not None
