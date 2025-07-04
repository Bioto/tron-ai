"""
Async wrappers for ChromaDB operations.

This module provides async-compatible wrappers around synchronous ChromaDB
operations to prevent blocking the event loop in async applications.
"""

import asyncio
import logging
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

# Register cleanup
import atexit

from chromadb.api.models.Collection import Collection

from tron_ai.exceptions import MemoryError

logger = logging.getLogger(__name__)

# Global thread pool executor for ChromaDB operations
_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="chromadb")


class ChromaClient:
    """Async wrapper for ChromaDB collection operations."""

    def __init__(self, collection: Collection):
        """Initialize async wrapper with a ChromaDB collection.

        Args:
            collection: The ChromaDB collection to wrap
        """
        self._collection = collection
        self._loop = None

    @property
    def collection(self) -> Collection:
        """Get the underlying collection."""
        return self._collection

    async def add(
        self,
        ids: List[str],
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """Add documents to the collection asynchronously.

        Args:
            ids: List of unique IDs for the documents
            documents: List of document strings
            metadatas: Optional list of metadata dictionaries
            embeddings: Optional list of embeddings
        """
        loop = asyncio.get_event_loop()

        def _add():
            return self._collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )

        await loop.run_in_executor(_executor, _add)
        logger.debug(f"Added {len(documents)} documents to collection")

    async def query(
        self,
        query_texts: Optional[List[str]] = None,
        query_embeddings: Optional[List[List[float]]] = None,
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Query the collection asynchronously.

        Args:
            query_texts: List of query strings
            query_embeddings: List of query embeddings
            n_results: Number of results to return
            where: Metadata filter
            where_document: Document filter
            include: Fields to include in results

        Returns:
            Query results dictionary
        """
        loop = asyncio.get_event_loop()

        def _query():
            # Build kwargs to avoid passing None values
            kwargs = {
                "query_texts": query_texts,
                "query_embeddings": query_embeddings,
                "n_results": n_results,
            }

            # Only add optional parameters if they're not None
            if where is not None:
                kwargs["where"] = where
            if where_document is not None:
                kwargs["where_document"] = where_document
            if include is not None:
                kwargs["include"] = include

            return self._collection.query(**kwargs)

        results = await loop.run_in_executor(_executor, _query)
        logger.debug(f"Query returned {len(results.get('documents', [[]])[0])} results")
        return results

    async def get(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Get documents from the collection asynchronously.

        Args:
            ids: List of document IDs to retrieve
            where: Metadata filter
            limit: Maximum number of results
            offset: Number of results to skip
            where_document: Document filter
            include: Fields to include in results

        Returns:
            Retrieved documents dictionary
        """
        loop = asyncio.get_event_loop()

        def _get():
            return self._collection.get(
                ids=ids,
                where=where,
                limit=limit,
                offset=offset,
                where_document=where_document,
                include=include,
            )

        return await loop.run_in_executor(_executor, _get)

    async def update(
        self,
        ids: List[str],
        documents: Optional[List[str]] = None,
        metadatas: Optional[List[Dict[str, Any]]] = None,
        embeddings: Optional[List[List[float]]] = None,
    ) -> None:
        """Update documents in the collection asynchronously.

        Args:
            ids: List of document IDs to update
            documents: Optional list of new document strings
            metadatas: Optional list of new metadata dictionaries
            embeddings: Optional list of new embeddings
        """
        loop = asyncio.get_event_loop()

        def _update():
            return self._collection.update(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings,
            )

        await loop.run_in_executor(_executor, _update)
        logger.debug(f"Updated {len(ids)} documents in collection")

    async def delete(
        self,
        ids: Optional[List[str]] = None,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Delete documents from the collection asynchronously.

        Args:
            ids: List of document IDs to delete
            where: Metadata filter for deletion
            where_document: Document filter for deletion
        """
        loop = asyncio.get_event_loop()

        def _delete():
            return self._collection.delete(
                ids=ids,
                where=where,
                where_document=where_document,
            )

        await loop.run_in_executor(_executor, _delete)
        logger.debug("Deleted documents from collection")

    async def count(self) -> int:
        """Get the count of documents in the collection asynchronously.

        Returns:
            Number of documents in the collection
        """
        loop = asyncio.get_event_loop()

        def _count():
            return self._collection.count()

        return await loop.run_in_executor(_executor, _count)


# Helper functions for easy memory operations
async def store_memory_async(
    collection: Union[Collection, ChromaClient],
    memory_text: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Store a memory asynchronously.

    Args:
        collection: ChromaDB collection or async wrapper
        memory_text: The text to store
        metadata: Optional metadata dictionary

    Returns:
        Success message

    Raises:
        MemoryError: If storing the memory fails
    """
    # Wrap collection if needed
    if not isinstance(collection, ChromaClient):
        collection = ChromaClient(collection)

    memory_time = datetime.now()
    memory_id = str(uuid.uuid4())

    # Merge provided metadata with timestamp
    final_metadata = {
        "timestamp": memory_time.timestamp(),  # Store as float for filtering
        "timestamp_iso": memory_time.isoformat(),  # Also store ISO format for display
    }
    if metadata:
        final_metadata.update(metadata)

    try:
        await collection.add(
            ids=[memory_id],
            documents=[memory_text],
            metadatas=[final_metadata],
        )
        logger.info(f"Memory stored successfully with ID: {memory_id}")
        return "Memory stored successfully"
    except Exception as e:
        logger.error(f"Error storing memory: {e}")
        raise MemoryError(
            "Failed to store memory in ChromaDB",
            context={
                "memory_id": memory_id,
                "memory_text_preview": memory_text[:100],
                "metadata": final_metadata,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )


async def query_memory_async(
    collection: Union[Collection, ChromaClient],
    query: str,
    n_results: int = 5,
    where: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Query memories asynchronously.

    Args:
        collection: ChromaDB collection or async wrapper
        query: Query text
        n_results: Number of results to return
        where: Optional metadata filter

    Returns:
        Query results dictionary

    Raises:
        MemoryError: If querying memories fails
    """
    # Wrap collection if needed
    if not isinstance(collection, ChromaClient):
        collection = ChromaClient(collection)

    try:
        results = await collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )
        logger.info(f"Query returned {len(results.get('documents', [[]])[0])} results")
        return results
    except Exception as e:
        logger.error(f"Error querying memory: {e}")
        raise MemoryError(
            "Failed to query memories from ChromaDB",
            context={
                "query": query,
                "n_results": n_results,
                "where_filter": where,
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        )


def cleanup_executor():
    """Clean up the thread pool executor."""
    _executor.shutdown(wait=True)
    logger.info("Async ChromaDB executor cleaned up")


atexit.register(cleanup_executor)
