# Standard library imports
from pydantic import BaseModel
import pprint
from typing import Optional, Dict, Any, List

# Local imports
from tron_ai.executors.base import Executor
from tron_ai.models.agent import Agent
from tron_ai.agents.tron.utils import memory


import logging

class AgentExecutor(Executor):
    """Base class for agent executors that handle agent execution workflows.
    
    This abstract base class provides a common interface for executing agents
    with user queries. It delegates the actual execution to the underlying
    client's function call mechanism, passing through the agent's prompt and
    tool manager.
    
    Subclasses should implement specific execution strategies while maintaining
    compatibility with the base interface.
    """

    logger = logging.getLogger(__name__)
    
    def __init__(self, *args, **kwargs):
        """Initialize the AgentExecutor with memory configuration."""
        super().__init__(*args, **kwargs)
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
        """Configure memory settings for the executor.
        
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
            "[AgentExecutor] Memory configured - enabled: %s, user_id: %s, search_limit: %d, threshold: %.2f",
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
                "[AgentExecutor] Searching for relevant memories for query: %s", 
                user_query[:100] + "..." if len(user_query) > 100 else user_query
            )
            
            search_results = memory.search(
                query=user_query,
                user_id=self.memory_user_id,
                limit=self.memory_search_limit,
                threshold=self.memory_search_threshold
            )
            
            self.logger.info("[AgentExecutor] Found %d relevant memories", len(search_results))
            return search_results
            
        except Exception as e:
            self.logger.error("[AgentExecutor] Error retrieving memories: %s", str(e))
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
                "[AgentExecutor] Stored interaction memory for agent %s, result: %s", 
                agent_name, 
                result
            )
            
        except Exception as e:
            self.logger.error("[AgentExecutor] Error storing memory: %s", str(e))
    
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
    
    async def execute(self, user_query: str, agent: Agent, prompt_kwargs: dict = {}, process_follow_ups: bool = True) -> dict:
        """Execute an agent with the given user query and handle follow-up queries.
        
        Args:
            user_query: The user's input query to process
            agent: The agent instance to execute
            prompt_kwargs: Additional keyword arguments to pass to the prompt
            process_follow_ups: Whether to process follow-up queries
        
        Returns:
            dict: The combined response from the agent execution and all follow-ups
        """
        # 1. Retrieve relevant memories for context
        enhanced_prompt_kwargs = dict(prompt_kwargs)
        try:
            relevant_memories = await self.retrieve_relevant_memories(user_query)
            # Fix: Extract actual memories from the results structure
            if isinstance(relevant_memories, dict) and 'results' in relevant_memories:
                actual_memories = relevant_memories['results']
                self.logger.debug("[AgentExecutor] Extracted %d memories from results structure", len(actual_memories))
                relevant_memories = actual_memories
            elif not isinstance(relevant_memories, list):
                self.logger.warning("[AgentExecutor] Unexpected memory format: %s", type(relevant_memories))
                relevant_memories = []
            
            # 2. Prepare enhanced prompt kwargs with memory context
            if relevant_memories:
                memory_context = self._format_memories_for_context(relevant_memories)
                enhanced_prompt_kwargs['memory_context'] = memory_context
                self.logger.info("[AgentExecutor] Added memory context with %d relevant memories", len(relevant_memories))
            else:
                # Ensure memory_context is always provided to avoid template errors
                enhanced_prompt_kwargs['memory_context'] = ""
        except Exception as e:
            self.logger.error("[AgentExecutor] Error during memory retrieval: %s", str(e))
            # Continue execution without memory context
            enhanced_prompt_kwargs['memory_context'] = ""
            relevant_memories = []
        
        # 3. Get the initial response
        self.logger.info("[AgentExecutor] Executing initial agent call with user_query: %s", user_query)
        initial_response = self.client.fcall(
            user_query=user_query,
            system_prompt=agent.prompt,
            tool_manager=agent.tool_manager,
            prompt_kwargs=enhanced_prompt_kwargs
        )
        self.logger.debug("[AgentExecutor] Initial response: %r", initial_response)
        
        # 4. Store the interaction in memory
        try:
            await self.store_interaction_memory(
                user_query=user_query,
                agent_response=initial_response,
                agent_name=agent.name if hasattr(agent, 'name') else 'unknown',
                metadata={'has_memory_context': bool(relevant_memories)}
            )
        except Exception as e:
            self.logger.error("[AgentExecutor] Error storing interaction memory: %s", str(e))
            # Continue execution even if memory storage fails
        
        user_questions = getattr(initial_response, "user_questions", [])
        
        for question in user_questions:
            self.logger.info("[AgentExecutor] Executing user question: %s", question)
            
        results = [initial_response]
    
        follow_up_key = getattr(agent, "follow_up_querys_key", None)
        follow_up_queries = getattr(initial_response, follow_up_key, []) if follow_up_key else []
        
        self.logger.info("[AgentExecutor] Follow-up queries: %r", follow_up_queries)
        
        if process_follow_ups:
            for query in follow_up_queries:
                self.logger.info("[AgentExecutor] Executing follow-up query: %s", query)
                follow_up_result = await self.execute(
                    f"Context: {initial_response.generated_output}\n\nFollow-up query: {query}",
                    agent,
                    enhanced_prompt_kwargs,
                    process_follow_ups=False
                )
                results.append(follow_up_result)
                
        if len(results) == 1:
            return results[0]
        
        combined_context = self.combine_responses(results)
        self.logger.info("[AgentExecutor] Combined responses: %d", len(combined_context))
        
        combined_response = self.client.fcall(
            user_query=(
                "Generate a detailed technical report based on the following context, "
                "analyzing from multiple angles with in-depth technical details, methodologies, and insights:\n\n"
                f"{combined_context}\n\nThe original user query is: {user_query}"
            ),
            system_prompt=agent.prompt,
            tool_manager=agent.tool_manager,
            prompt_kwargs=enhanced_prompt_kwargs
        )
        
        # Store the combined response in memory as well
        try:
            await self.store_interaction_memory(
                user_query=f"Combined analysis: {user_query}",
                agent_response=combined_response,
                agent_name=f"{agent.name if hasattr(agent, 'name') else 'unknown'}_combined",
                metadata={'is_combined_response': True, 'num_sub_responses': len(results)}
            )
        except Exception as e:
            self.logger.error("[AgentExecutor] Error storing combined response memory: %s", str(e))
            # Continue execution even if memory storage fails
        
        self.logger.debug("[AgentExecutor] Final combined response: %r", combined_response)
        return combined_response

    def combine_responses(self, responses: list) -> dict:
        """Combine a list of responses into a single dict for context passing."""
        combined = {}
        for idx, response in enumerate(responses):
            # If response is a pydantic model, convert to dict
            if hasattr(response, 'model_dump'):
                response_dict = response.model_dump()
            elif isinstance(response, dict):
                response_dict = response
            else:
                response_dict = {f"response_{idx}": response}
            combined[f"response_{idx}"] = response_dict
        return combined
