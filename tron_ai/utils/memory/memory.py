
import logging
from typing import Optional, Dict, Any, List
import pprint

from tron_ai.agents.tron.utils import memory

class AgentMemoryManager:
    logger = logging.getLogger(__name__)

    def __init__(self):
        """Initialize the AgentMemoryManager with default configuration."""
        self.memory_enabled = True  # Enable memory by default
        self.memory_user_id = "tron"  # Default user ID for memory operations
        self.memory_search_limit = 5  # Number of relevant memories to retrieve
        self.memory_search_threshold = 0.5  # Minimum similarity threshold for memory retrieval
    
    def configure_memory(
        self, 
        enabled: bool = True, 
        user_id: str = "tron",
        search_limit: int = 5,
        search_threshold: float = 0.5
    ):
        """Configure memory settings for the manager.
        
        Args:
            enabled: Whether to enable memory storage and retrieval
            user_id: User ID for memory operations (identifies the memory space)
            search_limit: Maximum number of relevant memories to retrieve
            search_threshold: Minimum similarity threshold for memory retrieval
        """
        self.memory_enabled = enabled
        self.memory_user_id = user_id
        self.memory_search_limit = search_limit
        self.memory_search_threshold = search_threshold
        self.logger.info(
            "[AgentMemoryManager] Memory configured - enabled: %s, user_id: %s, search_limit: %d, threshold: %.2f",
            enabled, user_id, search_limit, search_threshold
        )
    
    async def retrieve_relevant_memories(self, user_query: str) -> List[Dict[str, Any]]:
        """Retrieve relevant memories for the given user query.
        
        Args:
            user_query: The user's input query to find relevant memories for
            
        Returns:
            List of relevant memories with their metadata
        """
        if not self.memory_enabled:
            return []
            
        try:
            self.logger.info(
                "[AgentMemoryManager] Searching for relevant memories for query: %s", 
                user_query[:100] + "..." if len(user_query) > 100 else user_query
            )
            
            search_results = memory.search(
                query=user_query,
                user_id=self.memory_user_id,
                limit=self.memory_search_limit,
                threshold=self.memory_search_threshold
            )
            
            self.logger.info("[AgentMemoryManager] Found %d relevant memories", len(search_results))
            return search_results
            
        except Exception as e:
            self.logger.error("[AgentMemoryManager] Error retrieving memories: %s", str(e))
            return []
    
    async def store_interaction_memory(
        self, 
        user_query: str, 
        agent_response: Any, 
        agent_name: str,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Store the interaction in memory for future reference.
        
        Args:
            user_query: The user's input query
            agent_response: The agent's response
            agent_name: Name of the agent that handled the query
            metadata: Optional metadata to store with the memory
        """
        if not self.memory_enabled:
            return
            
        try:
            # Extract the generated output from the response
            if hasattr(agent_response, 'generated_output'):
                response_content = agent_response.generated_output
            elif hasattr(agent_response, 'model_dump'):
                response_dict = agent_response.model_dump()
                response_content = response_dict.get('generated_output', str(agent_response))
            else:
                response_content = str(agent_response)
            
            # Create conversation messages for memory storage
            messages = [
                {"role": "user", "content": user_query},
                {"role": "assistant", "content": response_content}
            ]
            
            # Prepare metadata
            memory_metadata = {
                "agent_name": agent_name,
                "timestamp": pprint.pformat({"timestamp": "now"}),  # mem0 will add actual timestamp
                "interaction_type": "agent_execution"
            }
            if metadata:
                memory_metadata.update(metadata)
            
            # Store in memory
            result = memory.add(
                messages=messages,
                user_id=self.memory_user_id,
                metadata=memory_metadata
            )
            
            self.logger.info(
                "[AgentMemoryManager] Stored interaction memory for agent %s, result: %s", 
                agent_name, 
                result
            )
            
        except Exception as e:
            self.logger.error("[AgentMemoryManager] Error storing memory: %s", str(e))
    
    def _format_memories_for_context(self, memories: List[Dict[str, Any]]) -> str:
        """Format retrieved memories into context string for prompt injection.
        
        Args:
            memories: List of memory dictionaries from memory search
            
        Returns:
            Formatted context string containing relevant memories
        """
        if not memories:
            return ""
        
        context_parts = ["## Relevant Context from Previous Interactions:"]
        
        for idx, memory_item in enumerate(memories, 1):
            # Extract memory content - handle different memory formats
            if isinstance(memory_item, dict):
                memory_text = memory_item.get('memory', memory_item.get('text', str(memory_item)))
                score = memory_item.get('score', memory_item.get('similarity', 'N/A'))
                # Clean the memory text to avoid template and JSON issues
                memory_text = str(memory_text).replace('\n', ' ').replace('\r', ' ').replace('"', "'").replace('{', '(').replace('}', ')').strip()
            else:
                memory_text = str(memory_item).replace('\n', ' ').replace('\r', ' ').replace('"', "'").replace('{', '(').replace('}', ')').strip()
                score = 'N/A'
            
            # Truncate very long memories to avoid overwhelming the context
            if len(memory_text) > 200:
                memory_text = memory_text[:200] + "..."
            
            context_parts.append(f"{idx}. {memory_text} (relevance: {score})")
        
        context_parts.append("---")
        return "\n".join(context_parts)
