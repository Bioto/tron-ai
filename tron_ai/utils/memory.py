"""
Memory utilities for the Tron AI system.

This module provides utility functions for memory operations including
storing, retrieving, and managing memories using the mem0 framework.
"""

import logging
from typing import List, Dict, Any, Optional
from tron_ai.agents.tron.utils import memory

logger = logging.getLogger(__name__)


class MemoryUtils:
    """Utility class for memory operations."""
    
    @staticmethod
    def search_memories(
        query: str, 
        user_id: str = "tron", 
        limit: int = 5, 
        threshold: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Search for relevant memories based on a query.
        
        Args:
            query: The search query
            user_id: User ID for memory space identification
            limit: Maximum number of results to return
            threshold: Minimum similarity threshold
            
        Returns:
            List of relevant memories
        """
        try:
            # Validate inputs
            if not query or not query.strip():
                logger.warning("Empty query provided to memory search")
                return []
            
            results = memory.search(
                query=query,
                user_id=user_id,
                limit=limit,
                threshold=threshold
            )
            
            # Ensure results is a list
            if not isinstance(results, list):
                logger.warning(f"Memory search returned non-list result: {type(results)}")
                return []
            
            logger.info(f"Found {len(results)} memories for query: {query[:50]}...")
            return results
        except Exception as e:
            logger.error(f"Error searching memories: {e}")
            return []
    
    @staticmethod
    def add_memory(
        messages: List[Dict[str, str]], 
        user_id: str = "tron", 
        metadata: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Add a new memory from conversation messages.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            user_id: User ID for memory space identification
            metadata: Optional metadata to store with the memory
            
        Returns:
            Result from memory addition
        """
        try:
            result = memory.add(
                messages=messages,
                user_id=user_id,
                metadata=metadata or {}
            )
            logger.info(f"Added memory for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
            return None
    
    @staticmethod
    def get_all_memories(user_id: str = "tron") -> List[Dict[str, Any]]:
        """Get all memories for a user.
        
        Args:
            user_id: User ID for memory space identification
            
        Returns:
            List of all memories for the user
        """
        try:
            results = memory.get_all(user_id=user_id)
            logger.info(f"Retrieved {len(results)} memories for user {user_id}")
            return results
        except Exception as e:
            logger.error(f"Error retrieving all memories: {e}")
            return []
    
    @staticmethod
    def update_memory(memory_id: str, data: str) -> Any:
        """Update a specific memory.
        
        Args:
            memory_id: ID of the memory to update
            data: New data for the memory
            
        Returns:
            Result from memory update
        """
        try:
            result = memory.update(memory_id=memory_id, data=data)
            logger.info(f"Updated memory {memory_id}")
            return result
        except Exception as e:
            logger.error(f"Error updating memory {memory_id}: {e}")
            return None
    
    @staticmethod
    def delete_memory(memory_id: str) -> Any:
        """Delete a specific memory.
        
        Args:
            memory_id: ID of the memory to delete
            
        Returns:
            Result from memory deletion
        """
        try:
            result = memory.delete(memory_id=memory_id)
            logger.info(f"Deleted memory {memory_id}")
            return result
        except Exception as e:
            logger.error(f"Error deleting memory {memory_id}: {e}")
            return None
    
    @staticmethod
    def delete_all_memories(user_id: str = "tron") -> Any:
        """Delete all memories for a user.
        
        Args:
            user_id: User ID for memory space identification
            
        Returns:
            Result from memory deletion
        """
        try:
            result = memory.delete_all(user_id=user_id)
            logger.info(f"Deleted all memories for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Error deleting all memories for user {user_id}: {e}")
            return None
    
    @staticmethod
    def format_memories_as_context(memories: List[Dict[str, Any]]) -> str:
        """Format memories for use as context in prompts.
        
        Args:
            memories: List of memory dictionaries
            
        Returns:
            Formatted context string
        """
        if not memories:
            return ""
        
        context_lines = ["## Previous Context from Memory:\n"]
        
        for idx, memory_item in enumerate(memories, 1):
            if isinstance(memory_item, dict):
                memory_text = memory_item.get('memory', memory_item.get('text', str(memory_item)))
                score = memory_item.get('score', memory_item.get('similarity', 'N/A'))
                context_lines.append(f"{idx}. {memory_text} (relevance: {score})")
            else:
                context_lines.append(f"{idx}. {str(memory_item)}")
        
        context_lines.append("\n---")
        return "\n".join(context_lines)


# Convenience functions for direct usage
def search_memories(query: str, user_id: str = "tron", **kwargs) -> List[Dict[str, Any]]:
    """Search for relevant memories."""
    return MemoryUtils.search_memories(query, user_id, **kwargs)


def add_conversation_to_memory(
    user_message: str, 
    assistant_message: str, 
    user_id: str = "tron",
    metadata: Optional[Dict[str, Any]] = None
) -> Any:
    """Add a user-assistant conversation to memory.
    
    Args:
        user_message: The user's message
        assistant_message: The assistant's response
        user_id: User ID for memory space identification
        metadata: Optional metadata
        
    Returns:
        Result from memory addition
    """
    messages = [
        {"role": "user", "content": user_message},
        {"role": "assistant", "content": assistant_message}
    ]
    return MemoryUtils.add_memory(messages, user_id, metadata)


def get_relevant_context(query: str, user_id: str = "tron", **kwargs) -> str:
    """Get relevant context from memories formatted for prompt injection.
    
    Args:
        query: Search query
        user_id: User ID for memory space identification
        **kwargs: Additional arguments for memory search
        
    Returns:
        Formatted context string
    """
    memories = MemoryUtils.search_memories(query, user_id, **kwargs)
    return MemoryUtils.format_memories_as_context(memories) 