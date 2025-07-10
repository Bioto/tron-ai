from tron_ai.agents.ssh.agent import SSHAgent
from tron_ai.agents.google.agent import GoogleAgent
from tron_ai.agents.todoist.agent import TodoistAgent

from tron_ai.utils.llm.LLMClient import get_llm_client
from tron_ai.executors.swarm.models import SwarmState
from tron_ai.executors.base import ExecutorConfig
from tron_ai.exceptions import ExecutionError
import logging
import uuid
import inspect

logger = logging.getLogger(__name__)


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
    async def execute_on_swarm(query: str, session_id: str = None, context: dict = None) -> dict:
        """Execute a query using the swarm executor with multiple specialized agents.
        
        This method delegates complex queries to a swarm of specialized agents that can
        break down the task, assign subtasks to appropriate agents, execute them in parallel,
        and compile the results into a comprehensive response.
        
        Args:
            query (str): The user query to be processed by the swarm
            session_id (str, optional): The session ID for conversation tracking. If not provided, a new one will be generated.
            context (dict, optional): Optional context dictionary containing additional information
        
        Returns:
            dict: A dictionary containing:
                - 'session_id': The session ID used for this execution
                - 'task_report': The comprehensive response containing the compiled results from all swarm agents
                - 'status': 'success' or 'error'
        """
        from tron_ai.executors.swarm.executor import SwarmExecutor
        
        # Initialize context if None
        if context is None:
            context = {}
        # Generate session_id if not provided
        if not session_id:
            stack = inspect.stack()
            is_subcall = any(
                frame.function == "execute_on_swarm" and frame.frame is not inspect.currentframe()
                for frame in stack[1:]
            )
            if is_subcall:
                logger.warning("[SESSION] execute_on_swarm called as a sub-call without session_id! This will break session tracking. Please propagate session_id from the parent context.")
                assert False, "execute_on_swarm called as a sub-call without session_id. Session tracking will break."
            session_id = uuid.uuid4().hex
        # Set root_id: for root call, root_id = session_id; for sub-calls, inherit from context
        stack = inspect.stack()
        is_subcall = any(
            frame.function == "execute_on_swarm" and frame.frame is not inspect.currentframe()
            for frame in stack[1:]
        )
        context = dict(context)  # copy to avoid mutating caller's dict
        if is_subcall:
            # Inherit root_id from context if present (should always be set by root call)
            root_id = context.get("root_id")
        else:
            # For root call, set root_id = session_id and propagate in context
            root_id = session_id
            context['root_id'] = root_id
        context['session_id'] = session_id
        # Now context['root_id'] is always correct for sub-calls
        
        # Create LLM client for swarm execution
        llm_client = get_llm_client(json_output=True, logging=True)

        # Create executor configuration
        config = ExecutorConfig(client=llm_client, logging=True)
        
        # Initialize swarm state with query and context
        swarm_state = SwarmState(
            session_id=session_id,
            root_id=root_id,
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
        
        try:
            result = await executor.execute(user_query=query)
            # Get the task report as a string - this ensures we don't expose internal objects
            task_report = ""
            if hasattr(result, 'task_report') and callable(result.task_report):
                task_report = result.task_report()
            elif hasattr(result, 'report'):
                task_report = result.report
            else:
                # Fallback: try to extract meaningful information from the result
                if hasattr(result, 'tasks') and result.tasks:
                    task_report = f"Completed {len(result.tasks)} tasks"
                else:
                    task_report = str(result)
            
            # Return only simple, serializable data
            return {
                "session_id": session_id,
                "root_id": root_id,
                "task_report": task_report,
                "status": "success"
            }
        except Exception as e:
            logger.error(f"Error in execute_on_swarm: {str(e)}")
            return {
                "session_id": session_id,
                "root_id": root_id,
                "task_report": f"Error executing swarm: {str(e)}",
                "status": "error",
                "error": str(e)
            }