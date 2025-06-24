from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import TaskState, Task, UnsupportedOperationError, Message
from a2a.utils.errors import ServerError
from a2a.types import TaskStatus

from tron_intelligence.executors.agents.models.agent import Agent
from tron_intelligence.executors.base import BaseExecutor

    

class TronA2AExecutor(AgentExecutor):
    def __init__(self, agent: Agent, executor: BaseExecutor):
        self.agent = agent
        self.executor = executor

    async def execute(self, context: RequestContext, event_queue: EventQueue):
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
        raise ServerError(error=UnsupportedOperationError())