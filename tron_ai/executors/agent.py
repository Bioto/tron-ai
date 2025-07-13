# Standard library imports
from pydantic import BaseModel
import pprint

# Local imports
from tron_ai.executors.base import Executor
from tron_ai.models.agent import Agent


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
    
    async def execute(self, user_query: str, agent: Agent, prompt_kwargs: dict = {}, process_follow_ups: bool = True) -> dict:
        """Execute an agent with the given user query and handle follow-up queries.
        
        Args:
            user_query: The user's input query to process
            agent: The agent instance to execute
            prompt_kwargs: Additional keyword arguments to pass to the prompt
        
        Returns:
            dict: The combined response from the agent execution and all follow-ups
        """
        # 1. Get the initial response
        self.logger.info("[AgentExecutor] Executing initial agent call with user_query: %s", user_query)
        initial_response = self.client.fcall(
            user_query=user_query,
            system_prompt=agent.prompt,
            tool_manager=agent.tool_manager,
            prompt_kwargs=prompt_kwargs
        )
        self.logger.debug("[AgentExecutor] Initial response: %r", initial_response)
        
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
                    prompt_kwargs,
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
            prompt_kwargs=prompt_kwargs
        )
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
