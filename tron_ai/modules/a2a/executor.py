from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import TaskState, Task, UnsupportedOperationError, Message
from a2a.utils.errors import ServerError
from a2a.types import TaskStatus

from tron_ai.models.agent import Agent
from tron_ai.executors.base import Executor
from tron_ai.modules.a2a.session_manager import A2ASessionManager

from typing import List, Optional
from datetime import datetime, timezone

class TronA2AExecutor(AgentExecutor):
    """
    A2A executor that integrates Tron Intelligence agents with the A2A framework with session continuity.
    
    This executor bridges the gap between Tron Intelligence's agent execution system
    and the A2A (Agent-to-Agent) communication protocol, allowing Tron agents to
    participate in A2A workflows with persistent conversation history.
    
    Attributes:
        agent: The Tron Intelligence agent to be executed
        executor: The base executor that handles the actual agent execution
        agents: The list of agents available for task execution
        session_manager: Manages A2A session continuity and database storage
    """
    def __init__(self, agent: Agent, executor: Executor, agents: List[Agent], session_manager: Optional[A2ASessionManager] = None):
        """
        Initialize the TronA2AExecutor.
        
        Args:
            agent: The Tron Intelligence agent to be executed
            executor: The base executor that handles agent execution logic
            agents: The list of agents available for task execution
            session_manager: Optional session manager for conversation continuity
        """
        self.agent = agent
        self.executor = executor
        self.agents = agents
        self.session_manager = session_manager or A2ASessionManager()

    async def execute(self, context: RequestContext, event_queue: EventQueue):
        """
        Execute the agent with the given request context and enqueue results.
        
        This method processes user queries through the Tron Intelligence executor
        and formats the response according to A2A protocol - either as direct messages
        for simple questions or as tasks with status updates for complex operations.
        Now includes session continuity support.
        
        Args:
            context: The request context containing user input and task metadata
            event_queue: The event queue to enqueue the execution results
        """
        user_query = context.get_user_input()
        
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Processing A2A request: {user_query} (context: {context.context_id}, task: {context.task_id})")
        
        # Initialize session continuity
        await self._ensure_session_continuity(context, user_query)
        
        # Get conversation history for context
        conversation_history = await self.session_manager.get_conversation_history(context.context_id)
        logger.debug(f"Retrieved conversation history with {len(conversation_history)} messages")
        
        # First, get the orchestrator's decision
        task_creator_response = await self.executor.execute(
            user_query=user_query,
            agent=self.agent
        )
        
        logger.debug(f"Orchestrator response type: {type(task_creator_response)}")
        
        # Check if this is a direct response or task delegation
        if hasattr(task_creator_response, 'response') and task_creator_response.response and task_creator_response.response.strip():
            # Direct response - return as message
            logger.info("Direct response from orchestrator")
            
            # Store response in conversation history
            response_message = {
                'kind': 'message',
                'messageId': context.task_id,
                'role': 'agent',
                'parts': [{'kind': 'text', 'text': task_creator_response.response}],
                'timestamp': str(datetime.now(timezone.utc).isoformat())
            }
            await self.session_manager.append_message(context.context_id, response_message)
            
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
                        parts=[{'kind': 'text', 'text': task_creator_response.response}]
                    )
                )
            )
            event_queue.enqueue_event(message)
            
        elif hasattr(task_creator_response, 'tasks') and task_creator_response.tasks:
            # Task delegation - execute tasks and send status updates
            logger.info(f"Task delegation - {len(task_creator_response.tasks)} tasks to execute")
            
            # Update task status to working
            await self.session_manager.update_task_status(
                task_id=context.task_id,
                status_state="working",
                status_message={
                    'kind': 'message',
                    'messageId': context.task_id,
                    'role': 'agent',
                    'parts': [{'kind': 'text', 'text': f"Processing {len(task_creator_response.tasks)} tasks..."}],
                    'timestamp': str(datetime.now(timezone.utc).isoformat())
                }
            )
            
            # Send initial status update
            working_message = Task(
                id=context.task_id,
                contextId=context.context_id,
                kind='task',
                status=TaskStatus(
                    state=TaskState.working,
                    message=Message(
                        kind='message',
                        messageId=context.task_id,
                        role='agent',
                        parts=[{'kind': 'text', 'text': f"Processing {len(task_creator_response.tasks)} tasks..."}]
                    )
                )
            )
            event_queue.enqueue_event(working_message)
            
            # Execute tasks using the swarm executor
            try:
                from tron_ai.executors.swarm.executor import SwarmExecutor
                from tron_ai.executors.swarm.models import SwarmState
                
                
                # Create swarm state with the tasks - use context_id for session continuity
                swarm_state = SwarmState(
                    user_query=user_query,
                    tasks=task_creator_response.tasks,
                    agents=self.agents,
                    session_id=context.context_id
                )
                
                                                  # Create swarm executor with proper config
                swarm_executor = SwarmExecutor(
                     state=swarm_state,
                     config=self.executor._config
                 )
                
                # Execute the tasks
                swarm_result = await swarm_executor.execute(user_query)
                
                # Get comprehensive task results including all tool outputs
                if hasattr(swarm_result, 'task_report') and callable(swarm_result.task_report):
                    # Use the detailed task report that includes all results
                    final_response = swarm_result.task_report()
                    logger.info(f"Using detailed task report with {len(final_response)} characters")
                elif hasattr(swarm_result, 'tasks') and swarm_result.tasks:
                    # Fallback: manually construct results from tasks
                    results = []
                    for i, task in enumerate(swarm_result.tasks):
                        if hasattr(task, 'result') and task.result:
                            if hasattr(task.result, 'response') and task.result.response:
                                results.append(f"**Task {i+1}: {task.description}**\n{task.result.response}")
                            else:
                                results.append(f"**Task {i+1}: {task.description}**\nCompleted")
                    final_response = "\n\n".join(results) if results else "Tasks completed successfully"
                    logger.info(f"Using manual task construction with {len(results)} task results")
                else:
                    # Final fallback: use summary report
                    final_response = swarm_result.report if hasattr(swarm_result, 'report') else "Tasks completed successfully"
                    logger.info("Using summary report as fallback")
                
                # Store final response in conversation history
                final_message = {
                    'kind': 'message',
                    'messageId': context.task_id,
                    'role': 'agent',
                    'parts': [{'kind': 'text', 'text': final_response}],
                    'timestamp': str(datetime.now(timezone.utc).isoformat())
                }
                await self.session_manager.append_message(context.context_id, final_message)
                
                # Store task artifacts if available
                artifacts = []
                if hasattr(swarm_result, 'tasks') and swarm_result.tasks:
                    for task in swarm_result.tasks:
                        if hasattr(task, 'result') and task.result:
                            artifacts.append({
                                'name': task.description,
                                'kind': 'text',
                                'content': task.result.response if hasattr(task.result, 'response') else str(task.result),
                                'timestamp': str(datetime.now(timezone.utc).isoformat())
                            })
                
                # Update task status to completed
                await self.session_manager.update_task_status(
                    task_id=context.task_id,
                    status_state="completed",
                    status_message=final_message,
                    artifacts=artifacts if artifacts else None
                )
                
                completed_message = Task(
                    id=context.task_id,
                    contextId=context.context_id,
                    kind='task',
                    status=TaskStatus(
                        state=TaskState.completed,
                        message=Message(
                            kind='message',
                            messageId=context.task_id,
                            role='agent',
                            parts=[{'kind': 'text', 'text': final_response}]
                        )
                    )
                )
                event_queue.enqueue_event(completed_message)
                
            except Exception as e:
                 logger.error(f"Error executing tasks: {str(e)}")
                 
                 # Store error in session history
                 error_message = {
                     'kind': 'message',
                     'messageId': context.task_id,
                     'role': 'agent',
                     'parts': [{'kind': 'text', 'text': f"Error processing tasks: {str(e)}"}],
                     'timestamp': str(datetime.now(timezone.utc).isoformat()),
                     'error': True
                 }
                 await self.session_manager.append_message(context.context_id, error_message)
                 
                 # Update task status to failed
                 await self.session_manager.update_task_status(
                     task_id=context.task_id,
                     status_state="failed",
                     status_message=error_message,
                     error_details=str(e)
                 )
                 
                 # Send error status - try different state names
                 try:
                     error_state = getattr(TaskState, 'failed', None) or getattr(TaskState, 'error', None) or getattr(TaskState, 'cancelled', TaskState.completed)
                     logger.debug(f"Using error state: {error_state}")
                 except:
                     error_state = TaskState.completed
                     logger.debug(f"Fallback to completed state for error")
                     
                 error_task = Task(
                     id=context.task_id,
                     contextId=context.context_id,
                     kind='task',
                     status=TaskStatus(
                         state=error_state,
                         message=Message(
                             kind='message',
                             messageId=context.task_id,
                             role='agent',
                             parts=[{'kind': 'text', 'text': f"Error processing tasks: {str(e)}"}]
                         )
                     )
                 )
                 event_queue.enqueue_event(error_task)
        
        else:
            # Fallback - no clear response or tasks
            logger.warning("No clear response or tasks from orchestrator")
            
            fallback_text = "I'm ready to help! Please let me know what you'd like me to do."
            
            # Store fallback message in conversation history
            fallback_msg = {
                'kind': 'message',
                'messageId': context.task_id,
                'role': 'agent',
                'parts': [{'kind': 'text', 'text': fallback_text}],
                'timestamp': str(datetime.now(timezone.utc).isoformat()),
                'fallback': True
            }
            await self.session_manager.append_message(context.context_id, fallback_msg)
            
            fallback_message = Task(
                id=context.task_id,
                contextId=context.context_id,
                kind='task',
                status=TaskStatus(
                    state=TaskState.completed,
                    message=Message(
                        kind='message',
                        messageId=context.task_id,
                        role='agent',
                        parts=[{'kind': 'text', 'text': fallback_text}]
                    )
                )
            )
            event_queue.enqueue_event(fallback_message)

    async def _ensure_session_continuity(self, context: RequestContext, user_query: str):
        """Ensure session continuity by creating context and task records."""
        try:
            # Ensure A2A context exists
            await self.session_manager.get_or_create_context(
                context_id=context.context_id,
                agent_name=self.agent.name,
                session_id=context.context_id
            )
            
            # Store the initial user message in conversation history
            user_message = {
                'kind': 'message',
                'messageId': f"user_{context.task_id}",
                'role': 'user',
                'parts': [{'kind': 'text', 'text': user_query}],
                'timestamp': str(datetime.now(timezone.utc).isoformat())
            }
            await self.session_manager.append_message(context.context_id, user_message)
            
            # Create task record
            await self.session_manager.create_task(
                task_id=context.task_id,
                context_id=context.context_id,
                agent_name=self.agent.name,
                initial_message=user_message
            )
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to ensure session continuity: {str(e)}")
            # Continue execution even if session continuity fails

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
        # Try to update task status to cancelled in database
        try:
            await self.session_manager.update_task_status(
                task_id=request.task_id,
                status_state="canceled",
                status_message={
                    'kind': 'message',
                    'messageId': request.task_id,
                    'role': 'system',
                    'parts': [{'kind': 'text', 'text': 'Task cancelled by user request'}],
                    'timestamp': str(datetime.now(timezone.utc).isoformat())
                }
            )
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to update cancelled task status: {str(e)}")
        
        raise ServerError(error=UnsupportedOperationError())