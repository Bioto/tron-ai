from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import TaskState, Task, UnsupportedOperationError, Message
from a2a.utils.errors import ServerError
from a2a.types import TaskStatus

from tron_ai.executors.agents.models.agent import Agent
from tron_ai.executors.base import BaseExecutor


class TronA2AExecutor(AgentExecutor):
    """
    A2A executor that integrates Tron Intelligence agents with the A2A framework.
    
    This executor bridges the gap between Tron Intelligence's agent execution system
    and the A2A (Agent-to-Agent) communication protocol, allowing Tron agents to
    participate in A2A workflows.
    
    Attributes:
        agent: The Tron Intelligence agent to be executed
        executor: The base executor that handles the actual agent execution
    """
    
    def __init__(self, agent: Agent, executor: BaseExecutor):
        """
        Initialize the TronA2AExecutor.
        
        Args:
            agent: The Tron Intelligence agent to be executed
            executor: The base executor that handles agent execution logic
        """
        self.agent = agent
        self.executor = executor

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        """
        Execute the agent with the given request context and enqueue results.
        
        This method processes user queries through the Tron Intelligence executor
        and formats the response as an A2A task message for the event queue.
        
        Args:
            context: The request context containing user input and task metadata
            event_queue: The event queue to enqueue the execution results
        """
        user_query = context.get_user_input()
        
        task_creator_response = await self.executor.execute(
            user_query=user_query
        )
    
        message = Task(
            id=context.task_id,
            contextId=context.context_id,
            kind='task',
            status=TaskStatus(
                state=TaskState.completed,
                message=Message(
                    kind='message',
                    messageId=context.task_id,
                    role='agent',
                    parts=[{'kind': 'text', 'text': task_creator_response.report}]
                )
            )
        )
        
        event_queue.enqueue_event(message)
        

        
    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        """
        Cancel the current task execution.
        
        This operation is not supported by the TronA2AExecutor as it delegates
        to the underlying Tron Intelligence executor which doesn't support
        cancellation.
        
        Args:
            request: The request context for the task to cancel
            event_queue: The event queue (unused in cancellation)
            
        Raises:
            ServerError: Always raised as cancellation is not supported
        """
        raise ServerError(error=UnsupportedOperationError())