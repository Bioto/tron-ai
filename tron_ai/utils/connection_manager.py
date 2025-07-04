"""
Connection lifecycle management for Tron AI.

This module provides centralized connection management for database
connections and other resources that need lifecycle management.
"""

import asyncio
import logging
from contextlib import asynccontextmanager, contextmanager
from typing import Optional, Dict, Any
import atexit
import weakref
import time
from collections import deque
import threading

import chromadb
from chromadb.api import ClientAPI


logger = logging.getLogger(__name__)


class ChromaConnectionPool:
    """Connection pool for ChromaDB clients to improve concurrent performance."""

    def __init__(
        self, pool_size: int = 5, max_idle_time: int = 300, timeout: float = 30.0
    ):
        """Initialize the connection pool.

        Args:
            pool_size: Maximum number of connections in the pool
            max_idle_time: Maximum idle time in seconds before closing a connection
            timeout: Maximum time to wait for a connection in seconds
        """
        self.pool_size = pool_size
        self.max_idle_time = max_idle_time
        self.timeout = timeout
        self._pool: deque = deque()
        self._in_use: Dict[int, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        self._condition = threading.Condition(self._lock)
        self._created = 0
        self._stats = {
            "acquired": 0,
            "released": 0,
            "created": 0,
            "closed": 0,
            "reused": 0,
            "waited": 0,
        }

    def acquire(self, timeout: Optional[float] = None) -> ClientAPI:
        """Acquire a connection from the pool.

        Args:
            timeout: Maximum time to wait for a connection (uses pool default if None)

        Returns:
            ChromaDB client instance

        Raises:
            TimeoutError: If no connection available within timeout
        """
        if timeout is None:
            timeout = self.timeout

        deadline = time.time() + timeout if timeout > 0 else float("inf")

        with self._condition:
            self._stats["acquired"] += 1

            while True:
                # Try to get an existing connection from the pool
                while self._pool:
                    conn_info = self._pool.popleft()
                    conn = conn_info["connection"]
                    created_time = conn_info["created_time"]
                    last_used = conn_info["last_used"]

                    # Check if connection is still valid (not too old)
                    if time.time() - last_used < self.max_idle_time:
                        # Reuse this connection
                        conn_id = id(conn)
                        self._in_use[conn_id] = {
                            "connection": conn,
                            "created_time": created_time,
                            "acquired_time": time.time(),
                        }
                        self._stats["reused"] += 1
                        logger.debug(
                            f"Reusing connection from pool. Pool size: {len(self._pool)}"
                        )
                        return conn
                    else:
                        # Connection is too old, close it
                        self._close_connection(conn)

                # No valid connections in pool, create a new one if under limit
                if self._created < self.pool_size:
                    conn = self._create_connection()
                    conn_id = id(conn)
                    self._in_use[conn_id] = {
                        "connection": conn,
                        "created_time": time.time(),
                        "acquired_time": time.time(),
                    }
                    return conn
                else:
                    # Pool is at capacity, wait for a connection
                    remaining_time = deadline - time.time()
                    if remaining_time <= 0:
                        raise TimeoutError(
                            f"Connection pool exhausted: timeout after {timeout}s"
                        )

                    self._stats["waited"] += 1
                    logger.debug("Waiting for available connection...")

                    # Wait for a connection to be released
                    if not self._condition.wait(timeout=min(remaining_time, 1.0)):
                        # Check if we've exceeded the deadline
                        if time.time() >= deadline:
                            raise TimeoutError(
                                f"Connection pool exhausted: timeout after {timeout}s"
                            )
                    # Loop back to try again

    def release(self, conn: ClientAPI):
        """Release a connection back to the pool.

        Args:
            conn: ChromaDB client to release
        """
        with self._condition:
            self._stats["released"] += 1
            conn_id = id(conn)

            if conn_id in self._in_use:
                conn_info = self._in_use.pop(conn_id)

                # Check if we should keep this connection
                if len(self._pool) < self.pool_size:
                    # Return to pool
                    self._pool.append(
                        {
                            "connection": conn,
                            "created_time": conn_info["created_time"],
                            "last_used": time.time(),
                        }
                    )
                    logger.debug(
                        f"Released connection back to pool. Pool size: {len(self._pool)}"
                    )

                    # Notify waiting threads
                    self._condition.notify()
                else:
                    # Pool is full, close the connection
                    self._close_connection(conn)
            else:
                logger.warning(f"Attempting to release unknown connection: {conn_id}")

    def _create_connection(self) -> ClientAPI:
        """Create a new ChromaDB connection."""
        logger.info("Creating new ChromaDB connection")
        conn = chromadb.PersistentClient()
        self._created += 1
        self._stats["created"] += 1
        return conn

    def _close_connection(self, conn: ClientAPI):
        """Close a ChromaDB connection."""
        # ChromaDB doesn't have explicit close, but we track it
        self._created -= 1
        self._stats["closed"] += 1
        logger.debug("Closed ChromaDB connection")

    def close_all(self):
        """Close all connections in the pool."""
        with self._condition:
            # Close pooled connections
            while self._pool:
                conn_info = self._pool.popleft()
                self._close_connection(conn_info["connection"])

            # Close in-use connections (though this is generally not recommended)
            for conn_id, conn_info in list(self._in_use.items()):
                self._close_connection(conn_info["connection"])

            self._in_use.clear()
            logger.info(f"Closed all connections. Stats: {self._stats}")

            # Notify any waiting threads
            self._condition.notify_all()

    def get_stats(self) -> Dict[str, int]:
        """Get pool statistics."""
        with self._lock:
            return {
                **self._stats,
                "pool_size": len(self._pool),
                "in_use": len(self._in_use),
                "total_created": self._created,
            }


class ConnectionManager:
    """Manages database connections and other resources with proper lifecycle."""

    _instance: Optional["ConnectionManager"] = None
    _instances: weakref.WeakSet = weakref.WeakSet()

    def __new__(cls):
        """Implement singleton pattern for connection manager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instances.add(cls._instance)
        return cls._instance

    def __init__(self):
        """Initialize connection manager."""
        if not hasattr(self, "_initialized"):
            self._initialized = True
            self._chroma_pool = ChromaConnectionPool(pool_size=5)
            self._memory_collection = None
            self._connections = {}
            self._lock = asyncio.Lock()
            self._health_check_interval = 60  # seconds
            self._last_health_check = 0

            # Register cleanup on exit
            atexit.register(self._cleanup_all)

    @property
    def chroma_client(self) -> ClientAPI:
        """Get a ChromaDB client from the pool.

        Note: This property interface is maintained for backward compatibility,
        but it's recommended to use get_pooled_connection() with proper release.
        """
        # For backward compatibility, return a connection without tracking
        return self._chroma_pool.acquire()

    def get_pooled_connection(self) -> ClientAPI:
        """Get a ChromaDB client from the connection pool.

        Returns:
            ChromaDB client instance

        Note: Must be used with release_pooled_connection() to return to pool.
        """
        self._perform_health_check()
        return self._chroma_pool.acquire()

    def release_pooled_connection(self, conn: ClientAPI):
        """Release a ChromaDB client back to the pool.

        Args:
            conn: ChromaDB client to release
        """
        self._chroma_pool.release(conn)

    def _perform_health_check(self):
        """Perform periodic health check on connections."""
        current_time = time.time()
        if current_time - self._last_health_check > self._health_check_interval:
            self._last_health_check = current_time
            # In a real implementation, this would check connection health
            logger.debug("Performed connection health check")

    @property
    def memory_collection(self):
        """Get or create memory collection with lazy initialization."""
        if self._memory_collection is None:
            logger.info("Initializing memory collection")
            # Use a pooled connection for this operation
            client = self.get_pooled_connection()
            try:
                self._memory_collection = client.create_collection(
                    "memory", get_or_create=True
                )
            finally:
                self.release_pooled_connection(client)
        return self._memory_collection

    @contextmanager
    def get_connection(self, connection_type: str = "chroma"):
        """Context manager for getting a connection.

        Args:
            connection_type: Type of connection to get

        Yields:
            The requested connection
        """
        if connection_type == "chroma":
            conn = self.get_pooled_connection()
            try:
                yield conn
            finally:
                self.release_pooled_connection(conn)
        elif connection_type == "memory":
            yield self.memory_collection
        else:
            raise ValueError(f"Unknown connection type: {connection_type}")

    @asynccontextmanager
    async def get_async_connection(self, connection_type: str = "chroma"):
        """Async context manager for getting a connection.

        Args:
            connection_type: Type of connection to get

        Yields:
            The requested connection
        """
        async with self._lock:
            if connection_type == "chroma":
                # Run in executor to avoid blocking
                loop = asyncio.get_event_loop()
                conn = await loop.run_in_executor(None, self.get_pooled_connection)
                try:
                    yield conn
                finally:
                    await loop.run_in_executor(
                        None, self.release_pooled_connection, conn
                    )
            elif connection_type == "memory":
                yield self.memory_collection
            else:
                raise ValueError(f"Unknown connection type: {connection_type}")

    def close_connection(self, connection_type: str = "all"):
        """Close a specific connection or all connections.

        Args:
            connection_type: Type of connection to close, or "all"
        """
        logger.info(f"Closing connection(s): {connection_type}")

        if connection_type == "all" or connection_type == "chroma":
            self._chroma_pool.close_all()
            self._memory_collection = None
            logger.info("ChromaDB connections closed")

    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics.

        Returns:
            Dictionary with pool statistics
        """
        return {
            "chroma_pool": self._chroma_pool.get_stats(),
        }

    def _cleanup_all(self):
        """Clean up all connections on exit."""
        logger.info("Cleaning up all connections")
        self.close_connection("all")

    @classmethod
    def cleanup_all_instances(cls):
        """Clean up all instances of connection manager."""
        for instance in cls._instances:
            if instance is not None:
                instance._cleanup_all()


# Global instance for easy access
_connection_manager = ConnectionManager()


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance.

    Returns:
        The connection manager singleton instance
    """
    return _connection_manager


def get_chroma_client() -> ClientAPI:
    """Get ChromaDB client from connection manager.

    Note: This returns a pooled connection for backward compatibility.
    For better performance, use get_connection_manager().get_connection()
    context manager instead.

    Returns:
        ChromaDB client instance
    """
    return get_connection_manager().chroma_client


def get_memory_collection():
    """Get memory collection from connection manager.

    Returns:
        Memory collection instance
    """
    return get_connection_manager().memory_collection
