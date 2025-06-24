"""Tests for the connection manager module."""

import pytest
from unittest.mock import Mock, patch

from tron_intelligence.utils.connection_manager import (
    ConnectionManager,
    get_connection_manager,
    get_chroma_client,
    get_memory_collection,
)


class TestConnectionManager:
    """Test suite for ConnectionManager."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton instance before each test."""
        ConnectionManager._instance = None
        yield
        ConnectionManager._instance = None

    def test_singleton_pattern(self):
        """Test that ConnectionManager follows singleton pattern."""
        manager1 = ConnectionManager()
        manager2 = ConnectionManager()
        assert manager1 is manager2

    def test_initialization(self):
        """Test ConnectionManager initialization."""
        manager = ConnectionManager()
        assert hasattr(manager, "_initialized")
        assert hasattr(manager, "_chroma_pool")
        assert hasattr(manager, "_memory_collection")
        assert hasattr(manager, "_connections")
        assert hasattr(manager, "_lock")
        assert hasattr(manager, "_health_check_interval")
        assert hasattr(manager, "_last_health_check")

    @patch("tron_intelligence.utils.connection_manager.chromadb.PersistentClient")
    def test_chroma_client_lazy_initialization(self, mock_chroma):
        """Test lazy initialization of ChromaDB client through connection pool."""
        mock_client = Mock()
        mock_chroma.return_value = mock_client

        manager = ConnectionManager()

        # First access should get a client from the pool
        client1 = manager.chroma_client
        assert client1 is mock_client
        mock_chroma.assert_called_once()

        # Test pooled connection methods
        pooled_conn = manager.get_pooled_connection()
        assert pooled_conn is not None

        # Release it back to the pool
        manager.release_pooled_connection(pooled_conn)

    @patch("tron_intelligence.utils.connection_manager.chromadb.PersistentClient")
    def test_memory_collection_lazy_initialization(self, mock_chroma):
        """Test lazy initialization of memory collection."""
        mock_client = Mock()
        mock_collection = Mock()
        mock_client.create_collection.return_value = mock_collection
        mock_chroma.return_value = mock_client

        manager = ConnectionManager()
        manager._memory_collection = None

        # First access should initialize
        collection = manager.memory_collection
        assert collection is mock_collection
        mock_client.create_collection.assert_called_once_with(
            "memory", get_or_create=True
        )

    @patch("tron_intelligence.utils.connection_manager.chromadb.PersistentClient")
    def test_get_connection_context_manager(self, mock_chroma):
        """Test get_connection context manager."""
        manager = ConnectionManager()
        mock_client = Mock()
        mock_chroma.return_value = mock_client

        # Test chroma connection
        with manager.get_connection("chroma") as conn:
            assert conn is not None
            # Connection should be from the pool
            mock_chroma.assert_called()

        # Test memory connection
        mock_collection = Mock()
        manager._memory_collection = mock_collection
        with manager.get_connection("memory") as conn:
            assert conn is mock_collection

        # Test invalid connection type
        with pytest.raises(ValueError, match="Unknown connection type"):
            with manager.get_connection("invalid"):
                pass

    @pytest.mark.asyncio
    @patch("tron_intelligence.utils.connection_manager.chromadb.PersistentClient")
    async def test_get_async_connection_context_manager(self, mock_chroma):
        """Test get_async_connection context manager."""
        manager = ConnectionManager()
        mock_client = Mock()
        mock_chroma.return_value = mock_client

        # Test chroma connection
        async with manager.get_async_connection("chroma") as conn:
            assert conn is not None
            # Connection should be from the pool
            mock_chroma.assert_called()

        # Test memory connection
        mock_collection = Mock()
        manager._memory_collection = mock_collection
        async with manager.get_async_connection("memory") as conn:
            assert conn is mock_collection

        # Test invalid connection type
        with pytest.raises(ValueError, match="Unknown connection type"):
            async with manager.get_async_connection("invalid"):
                pass

    def test_close_connection(self):
        """Test closing connections."""
        manager = ConnectionManager()

        # Mock the pool's close_all method
        with patch.object(manager._chroma_pool, "close_all") as mock_close_all:
            # Close all connections
            manager.close_connection("all")
            mock_close_all.assert_called_once()
            assert manager._memory_collection is None

        # Set up memory collection
        manager._memory_collection = Mock()

        # Close chroma connection
        with patch.object(manager._chroma_pool, "close_all") as mock_close_all:
            manager.close_connection("chroma")
            mock_close_all.assert_called_once()
            assert manager._memory_collection is None

    def test_cleanup_all(self):
        """Test cleanup_all method."""
        manager = ConnectionManager()
        manager._memory_collection = Mock()

        with patch.object(manager, "close_connection") as mock_close:
            manager._cleanup_all()
            mock_close.assert_called_once_with("all")

    def test_cleanup_all_instances(self):
        """Test cleanup_all_instances class method."""
        # Create some instances
        manager1 = ConnectionManager()
        ConnectionManager()  # Same as manager1 due to singleton

        with patch.object(manager1, "_cleanup_all") as mock_cleanup:
            ConnectionManager.cleanup_all_instances()
            mock_cleanup.assert_called_once()

    @patch("tron_intelligence.utils.connection_manager.atexit.register")
    def test_atexit_registration(self, mock_atexit):
        """Test that cleanup is registered with atexit."""
        # Clear singleton instance for this test
        ConnectionManager._instance = None

        manager = ConnectionManager()
        mock_atexit.assert_called_once_with(manager._cleanup_all)

    @patch("tron_intelligence.utils.connection_manager.chromadb.PersistentClient")
    def test_connection_pool_functionality(self, mock_chroma):
        """Test connection pool acquire and release."""
        mock_clients = [Mock() for _ in range(3)]
        mock_chroma.side_effect = mock_clients

        manager = ConnectionManager()

        # Test acquiring connections
        conn1 = manager.get_pooled_connection()
        assert conn1 is mock_clients[0]

        conn2 = manager.get_pooled_connection()
        assert conn2 is mock_clients[1]

        # Release connections back to pool
        manager.release_pooled_connection(conn1)
        manager.release_pooled_connection(conn2)

        # Next acquire should reuse from pool
        conn3 = manager.get_pooled_connection()
        # Should get one of the released connections
        assert conn3 in [mock_clients[0], mock_clients[1]]

    def test_get_pool_stats(self):
        """Test getting pool statistics."""
        manager = ConnectionManager()
        stats = manager.get_pool_stats()

        assert "chroma_pool" in stats
        assert isinstance(stats["chroma_pool"], dict)


class TestModuleFunctions:
    """Test module-level functions."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton instance before each test."""
        ConnectionManager._instance = None
        yield
        ConnectionManager._instance = None

    def test_get_connection_manager(self):
        """Test get_connection_manager function."""
        manager = get_connection_manager()
        assert isinstance(manager, ConnectionManager)

        # Should return same instance
        manager2 = get_connection_manager()
        assert manager is manager2

    def test_get_chroma_client(self):
        """Test get_chroma_client function."""
        with patch(
            "tron_intelligence.utils.connection_manager.chromadb.PersistentClient"
        ) as mock_chroma:
            mock_client = Mock()
            mock_chroma.return_value = mock_client

            # Reset singleton for clean test
            ConnectionManager._instance = None

            client = get_chroma_client()
            assert client is not None
            # Should create a client through the pool
            mock_chroma.assert_called()

    def test_get_memory_collection(self):
        """Test get_memory_collection function."""
        with patch(
            "tron_intelligence.utils.connection_manager.chromadb.PersistentClient"
        ) as mock_chroma:
            mock_client = Mock()
            mock_collection = Mock()
            mock_client.create_collection.return_value = mock_collection
            mock_chroma.return_value = mock_client

            # Reset singleton for clean test
            ConnectionManager._instance = None
            import tron_intelligence.utils.connection_manager as cm_mod

            cm_mod._connection_manager = (
                ConnectionManager()
            )  # Recreate module-level singleton

            collection = get_memory_collection()
            assert collection is mock_collection
            mock_client.create_collection.assert_called_once_with(
                "memory", get_or_create=True
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
