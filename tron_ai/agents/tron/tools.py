from tron_ai.agents.ssh.agent import SSHAgent
from tron_ai.agents.google.agent import GoogleAgent
from tron_ai.agents.todoist.agent import TodoistAgent

from tron_ai.utils.llm.LLMClient import LLMClient
from tron_ai.models.config import LLMClientConfig
from adalflow import OpenAIClient


class TronTools:
    @staticmethod
    def query_memory(query: str) -> str:
        """
        Query the agent's memory system to retrieve relevant information about the user.
        
        This function searches through the agent's persistent memory store to find
        information that matches the provided query. The memory system uses vector
        similarity search to identify the most relevant stored memories.
        
        Args:
            query (str): The search query to find relevant memories
            
        Returns:
            str: A JSON-formatted string containing search results with the following structure:
                {
                    "results": [
                        {
                            "memory": str,  # The stored memory text
                            "similarity": float,  # Similarity score (0-1)
                            "metadata": dict  # Additional metadata about the memory
                        }
                    ]
                }
                
        The search is performed with these parameters:
        - user_id: "tron" (identifies this agent's memory space)
        - limit: 5 (maximum number of results returned)
        - threshold: 0.5 (minimum similarity score for inclusion)
        
        This enables the agent to access context about previous conversations,
        user preferences, and stored information to provide more personalized
        and contextually aware responses.
        """
        from .utils import memory
        return memory.search(query=query, user_id="tron", limit=5, threshold=0.5)
    
    @staticmethod
    async def execute_on_swarm(query: str, context: dict = None) -> str:
        """Execute a query using the swarm executor with multiple specialized agents.
        
        This method delegates complex queries to a swarm of specialized agents that can
        break down the task, assign subtasks to appropriate agents, execute them in parallel,
        and compile the results into a comprehensive response.
        
        YOU MUST PASS KWARGS TO THIS FUNCTION.
        
        kwargs:
            query (str): The user query to be processed by the swarm
            context (dict, optional): Optional context dictionary containing additional information
            
        Returns:
            str: A comprehensive response containing the compiled results from all swarm agents.
                The response includes:
                - Task breakdown and assignment details
                - Individual agent execution results
                - Consolidated final answer
                - Any errors or issues encountered during execution
        """
        from tron_ai.executors.swarm.executor import SwarmExecutor
        from tron_ai.executors.swarm.models import SwarmState
        from tron_ai.executors.base import ExecutorConfig
        from tron_ai.exceptions import ExecutionError
        
        # Initialize context if None
        if context is None:
            context = {}
            
        # Create LLM client for swarm execution
        llm_client = LLMClient(
            client=OpenAIClient(),
            config=LLMClientConfig(
                model_name="gpt-4o", 
                json_output=True, 
                logging=True
            ),
        )

        # Create executor configuration
        config = ExecutorConfig(client=llm_client, logging=True)
        
        # Initialize swarm state with query and context
        swarm_state = SwarmState(
            user_query=query,
            agents=[
                SSHAgent(),
                TodoistAgent(),
                GoogleAgent(),
            ]
        )
        
        # Create and execute swarm executor
        executor = SwarmExecutor(
            config=config,
            state=swarm_state,
        )
        
        # try:
        result = await executor.execute(user_query=query)
        # Return the detailed task report which includes all results
        task_report = result.task_report()
        return task_report
        # except Exception as e:
        #     raise ExecutionError(f"Swarm execution failed: {str(e)}") from e