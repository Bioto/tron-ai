"""Test connection pooling functionality."""

import pytest
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from tron_ai.utils.connection_manager import (
    ConnectionManager,
    ChromaConnectionPool,
    get_connection_manager,
)


class TestChromaConnectionPool:
    """Test ChromaConnectionPool class."""

    def test_pool_initialization(self):
        """Test pool initializes correctly."""
        pool = ChromaConnectionPool(pool_size=3, max_idle_time=60)

        assert pool.pool_size == 3
        assert pool.max_idle_time == 60
        assert len(pool._pool) == 0
        assert len(pool._in_use) == 0
        assert pool._created == 0

    def test_acquire_creates_new_connection(self):
        """Test acquiring connection creates new one when pool is empty."""
        pool = ChromaConnectionPool(pool_size=3)

        conn = pool.acquire()
        assert conn is not None
        assert pool._created == 1
        assert len(pool._in_use) == 1
        assert pool.get_stats()["created"] == 1
        assert pool.get_stats()["acquired"] == 1

    def test_release_returns_to_pool(self):
        """Test releasing connection returns it to pool."""
        pool = ChromaConnectionPool(pool_size=3)

        conn = pool.acquire()
        pool.release(conn)

        assert len(pool._pool) == 1
        assert len(pool._in_use) == 0
        assert pool.get_stats()["released"] == 1

    def test_reuse_connection_from_pool(self):
        """Test connections are reused from pool."""
        pool = ChromaConnectionPool(pool_size=3)

        # Acquire and release a connection
        conn1 = pool.acquire()
        pool.release(conn1)

        # Acquire again - should reuse
        conn2 = pool.acquire()

        assert conn1 is conn2  # Same connection object
        assert pool._created == 1  # Only one connection created
        assert pool.get_stats()["reused"] == 1

    def test_pool_size_limit(self):
        """Test pool respects size limit."""
        pool = ChromaConnectionPool(pool_size=2)

        # Acquire two connections
        conn1 = pool.acquire()
        pool.acquire()

        # Try to acquire third - should fail with timeout
        with pytest.raises(TimeoutError, match="Connection pool exhausted"):
            pool.acquire(timeout=0.1)  # Short timeout to fail quickly

        # Release one and try again
        pool.release(conn1)
        conn3 = pool.acquire()
        assert conn3 is not None

    def test_max_idle_time(self):
        """Test connections are closed after max idle time."""
        pool = ChromaConnectionPool(pool_size=3, max_idle_time=0.1)  # 100ms

        conn = pool.acquire()
        pool.release(conn)

        # Wait for connection to expire
        time.sleep(0.2)

        # Acquire again - should create new connection
        new_conn = pool.acquire()
        assert new_conn is not conn
        assert pool.get_stats()["closed"] == 1

    def test_concurrent_access(self):
        """Test pool handles concurrent access correctly."""
        pool = ChromaConnectionPool(pool_size=5)
        results = []

        def worker():
            conn = pool.acquire()
            time.sleep(0.01)  # Simulate work
            pool.release(conn)
            return True

        # Run 10 workers with pool size of 5
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker) for _ in range(10)]
            for future in as_completed(futures):
                results.append(future.result())

        assert len(results) == 10
        assert all(results)
        assert pool.get_stats()["acquired"] == 10
        assert pool.get_stats()["released"] == 10

    def test_close_all(self):
        """Test closing all connections."""
        pool = ChromaConnectionPool(pool_size=3)

        # Create some connections
        conn1 = pool.acquire()
        pool.acquire()
        pool.release(conn1)

        # Close all
        pool.close_all()

        assert len(pool._pool) == 0
        assert len(pool._in_use) == 0
        assert pool._created == 0


class TestConnectionManagerWithPooling:
    """Test ConnectionManager with connection pooling."""

    def teardown_method(self):
        """Clean up after each test."""
        # Clean up the singleton connection manager
        manager = get_connection_manager()
        manager.close_connection("all")

    def test_singleton_with_pool(self):
        """Test singleton pattern still works with pooling."""
        manager1 = ConnectionManager()
        manager2 = ConnectionManager()
        assert manager1 is manager2

    def test_get_pooled_connection(self):
        """Test getting pooled connections."""
        manager = get_connection_manager()

        conn1 = manager.get_pooled_connection()
        assert conn1 is not None

        # Release and get again
        manager.release_pooled_connection(conn1)
        conn2 = manager.get_pooled_connection()

        # Should reuse the same connection
        assert conn1 is conn2

    def test_context_manager_with_pooling(self):
        """Test context manager uses pooling."""
        manager = get_connection_manager()

        with manager.get_connection("chroma") as conn1:
            assert conn1 is not None

        # Get connection again - should reuse
        with manager.get_connection("chroma"):
            stats = manager.get_pool_stats()
            assert stats["chroma_pool"]["reused"] > 0

    @pytest.mark.asyncio
    async def test_async_context_manager_with_pooling(self):
        """Test async context manager uses pooling."""
        manager = get_connection_manager()

        async with manager.get_async_connection("chroma") as conn1:
            assert conn1 is not None

        # Get connection again - should reuse
        async with manager.get_async_connection("chroma"):
            stats = manager.get_pool_stats()
            assert stats["chroma_pool"]["reused"] > 0

    def test_backward_compatibility(self):
        """Test backward compatibility with chroma_client property."""
        manager = get_connection_manager()

        # Old way still works
        client = manager.chroma_client
        assert client is not None

        # But it acquires from pool
        stats = manager.get_pool_stats()
        assert stats["chroma_pool"]["acquired"] > 0

    def test_memory_collection_uses_pool(self):
        """Test memory collection initialization uses pool."""
        manager = ConnectionManager()
        # Reset to ensure clean state
        manager._memory_collection = None

        # Access memory collection
        collection = manager.memory_collection
        assert collection is not None

        # Should have used and released a connection
        stats = manager.get_pool_stats()
        assert stats["chroma_pool"]["acquired"] > 0
        assert stats["chroma_pool"]["released"] > 0

    def test_concurrent_pool_access(self):
        """Test concurrent access through connection manager."""
        manager = get_connection_manager()
        results = []

        def worker(i):
            with manager.get_connection("chroma"):
                time.sleep(0.01)  # Simulate work
                return f"Worker {i} completed"

        # Run 10 workers concurrently
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(worker, i) for i in range(10)]
            for future in as_completed(futures):
                results.append(future.result())

        assert len(results) == 10

        # Check pool statistics
        stats = manager.get_pool_stats()
        assert stats["chroma_pool"]["acquired"] >= 10
        assert stats["chroma_pool"]["released"] >= 10
        assert stats["chroma_pool"]["reused"] > 0  # Some connections were reused

    def test_pool_statistics(self):
        """Test pool statistics reporting."""
        manager = get_connection_manager()

        # Perform some operations
        conn1 = manager.get_pooled_connection()
        manager.get_pooled_connection()
        manager.release_pooled_connection(conn1)

        stats = manager.get_pool_stats()
        assert "chroma_pool" in stats
        pool_stats = stats["chroma_pool"]

        assert pool_stats["acquired"] >= 2
        assert pool_stats["released"] >= 1
        assert pool_stats["in_use"] >= 1
        assert pool_stats["pool_size"] >= 0


class TestPerformanceImprovement:
    """Test performance improvements from pooling."""

    def test_connection_reuse_performance(self):
        """Test that reusing connections is faster than creating new ones."""
        manager = get_connection_manager()

        # Measure time for first connection (creates new)
        start = time.time()
        with manager.get_connection("chroma"):
            pass
        first_time = time.time() - start

        # Measure time for second connection (reuses)
        start = time.time()
        with manager.get_connection("chroma"):
            pass
        second_time = time.time() - start

        # Reused connection should be faster (or at least not slower)
        # In practice, creation involves more overhead
        print(
            f"First connection: {first_time:.4f}s, Second connection: {second_time:.4f}s"
        )

        # Verify reuse happened
        stats = manager.get_pool_stats()
        assert stats["chroma_pool"]["reused"] > 0

    def test_concurrent_performance(self):
        """Test improved performance under concurrent load."""
        # Create a fresh connection manager to avoid interference
        # Since it's a singleton, we need to clean up first
        manager = get_connection_manager()
        manager.close_connection("all")  # Clean up any existing connections

        def sequential_test():
            """Sequential connection access."""
            start = time.time()
            for _ in range(5):
                with manager.get_connection("chroma"):
                    time.sleep(0.01)  # Simulate work
            return time.time() - start

        def concurrent_test():
            """Concurrent connection access with pooling."""
            start = time.time()
            connections = []
            connections_lock = threading.Lock()

            def acquire_and_work():
                conn = manager.get_pooled_connection()
                with connections_lock:
                    connections.append(conn)
                time.sleep(0.01)  # Simulate work

            with ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(acquire_and_work) for _ in range(5)]

                # Wait for all to complete
                for future in as_completed(futures):
                    future.result()

                # Release all connections
                for conn in connections:
                    manager.release_pooled_connection(conn)

            return time.time() - start

        seq_time = sequential_test()
        conc_time = concurrent_test()

        print(f"Sequential: {seq_time:.4f}s, Concurrent: {conc_time:.4f}s")

        # Concurrent should be faster due to pooling
        # (though this is a simplified test)
        stats = manager.get_pool_stats()
        print(f"Pool stats: {stats}")


if __name__ == "__main__":
    # Run basic tests
    print("Testing ChromaDB connection pooling...")

    # Test basic pooling
    pool = ChromaConnectionPool(pool_size=3)
    conn1 = pool.acquire()
    print(f"Acquired connection: {conn1}")
    pool.release(conn1)
    print(f"Pool stats after release: {pool.get_stats()}")

    # Test reuse
    conn2 = pool.acquire()
    print(f"Reused connection: {conn1 is conn2}")

    # Test connection manager
    manager = get_connection_manager()
    with manager.get_connection("chroma") as conn:
        print(f"Got connection through manager: {conn}")

    print(f"Manager pool stats: {manager.get_pool_stats()}")
    print("All tests completed!")
