"""A2A Session Manager for handling conversation continuity with database storage."""

import logging
from typing import Optional, List, Dict, Any
from uuid import uuid4
from datetime import datetime, timezone

from tron_ai.database.manager import DatabaseManager
from tron_ai.database.config import DatabaseConfig

logger = logging.getLogger(__name__)

class A2ASessionManager:
    """Manages A2A session continuity using database storage."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize the A2A session manager.
        
        Args:
            db_manager: Optional database manager instance. If not provided, creates one with default config.
        """
        self.db_manager = db_manager or DatabaseManager(DatabaseConfig())
        self._initialized = False
    
    async def initialize(self):
        """Initialize the database connection."""
        if not self._initialized:
            await self.db_manager.initialize()
            self._initialized = True
    
    async def create_context(self, context_id: str, agent_name: str, session_id: Optional[str] = None) -> str:
        """Create a new A2A context for session continuity.
        
        Args:
            context_id: Unique identifier for the A2A context
            agent_name: Name of the agent handling this context
            session_id: Optional session ID to link with existing conversations
            
        Returns:
            The context_id that was created
        """
        await self.initialize()
        
        try:
            await self.db_manager.create_a2a_context(
                context_id=context_id,
                agent_name=agent_name,
                session_id=session_id,
                conversation_history=[],
                agent_state={},
                extra_metadata={"created_by": "a2a_session_manager"}
            )
            logger.info(f"Created A2A context: {context_id} for agent: {agent_name}")
            return context_id
        except Exception as e:
            logger.error(f"Failed to create A2A context {context_id}: {str(e)}")
            raise
    
    async def get_or_create_context(self, context_id: str, agent_name: str, session_id: Optional[str] = None) -> str:
        """Get an existing context or create a new one.
        
        Args:
            context_id: Unique identifier for the A2A context
            agent_name: Name of the agent handling this context
            session_id: Optional session ID to link with existing conversations
            
        Returns:
            The context_id that was retrieved or created
        """
        await self.initialize()
        
        # Try to get existing context
        existing_context = await self.db_manager.get_a2a_context(context_id)
        if existing_context:
            logger.debug(f"Retrieved existing A2A context: {context_id}")
            return context_id
        
        # Create new context if it doesn't exist
        return await self.create_context(context_id, agent_name, session_id)
    
    async def get_conversation_history(self, context_id: str) -> List[Dict[str, Any]]:
        """Get the conversation history for a context.
        
        Args:
            context_id: The A2A context ID
            
        Returns:
            List of messages in the conversation history
        """
        await self.initialize()
        
        context = await self.db_manager.get_a2a_context(context_id)
        if context and context.conversation_history:
            return context.conversation_history
        return []
    
    async def append_message(self, context_id: str, message: Dict[str, Any]) -> bool:
        """Append a message to the conversation history.
        
        Args:
            context_id: The A2A context ID
            message: The message to append (A2A format)
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            result = await self.db_manager.append_to_a2a_conversation_history(context_id, message)
            if result:
                logger.debug(f"Appended message to A2A context: {context_id}")
                return True
            else:
                logger.warning(f"Failed to append message - context not found: {context_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to append message to context {context_id}: {str(e)}")
            return False
    
    async def update_agent_state(self, context_id: str, agent_state: Dict[str, Any]) -> bool:
        """Update the agent state for a context.
        
        Args:
            context_id: The A2A context ID
            agent_state: The new agent state
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            result = await self.db_manager.update_a2a_context(
                context_id=context_id,
                agent_state=agent_state
            )
            if result:
                logger.debug(f"Updated agent state for A2A context: {context_id}")
                return True
            else:
                logger.warning(f"Failed to update agent state - context not found: {context_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to update agent state for context {context_id}: {str(e)}")
            return False
    
    async def create_task(self, task_id: str, context_id: str, agent_name: str, initial_message: Optional[Dict[str, Any]] = None) -> str:
        """Create a new A2A task.
        
        Args:
            task_id: Unique identifier for the task
            context_id: The A2A context ID this task belongs to
            agent_name: Name of the agent handling this task
            initial_message: The initial message that started this task
            
        Returns:
            The task_id that was created
        """
        await self.initialize()
        
        try:
            await self.db_manager.create_a2a_task(
                task_id=task_id,
                context_id=context_id,
                agent_name=agent_name,
                status_state="submitted",
                initial_message=initial_message,
                extra_metadata={"created_by": "a2a_session_manager"}
            )
            logger.info(f"Created A2A task: {task_id} in context: {context_id}")
            return task_id
        except Exception as e:
            logger.error(f"Failed to create A2A task {task_id}: {str(e)}")
            raise
    
    async def update_task_status(self, task_id: str, status_state: str, status_message: Optional[Dict[str, Any]] = None, artifacts: Optional[List[Dict[str, Any]]] = None) -> bool:
        """Update the status of an A2A task.
        
        Args:
            task_id: The task ID to update
            status_state: New status (submitted, working, completed, failed, canceled)
            status_message: Optional status message
            artifacts: Optional task artifacts/results
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            result = await self.db_manager.update_a2a_task_status(
                task_id=task_id,
                status_state=status_state,
                status_message=status_message,
                artifacts=artifacts
            )
            if result:
                logger.debug(f"Updated A2A task {task_id} status to: {status_state}")
                return True
            else:
                logger.warning(f"Failed to update task status - task not found: {task_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to update task status for {task_id}: {str(e)}")
            return False
    
    async def get_task(self, task_id: str):
        """Get an A2A task by ID.
        
        Args:
            task_id: The task ID to retrieve
            
        Returns:
            The task data if found, None otherwise
        """
        await self.initialize()
        return await self.db_manager.get_a2a_task(task_id)
    
    async def append_task_message(self, task_id: str, message: Dict[str, Any]) -> bool:
        """Append a message to the task history.
        
        Args:
            task_id: The task ID
            message: The message to append
            
        Returns:
            True if successful, False otherwise
        """
        await self.initialize()
        
        try:
            result = await self.db_manager.append_to_a2a_task_history(task_id, message)
            if result:
                logger.debug(f"Appended message to A2A task: {task_id}")
                return True
            else:
                logger.warning(f"Failed to append message - task not found: {task_id}")
                return False
        except Exception as e:
            logger.error(f"Failed to append message to task {task_id}: {str(e)}")
            return False
    
    async def generate_context_id(self) -> str:
        """Generate a new unique context ID.
        
        Returns:
            A new UUID-based context ID
        """
        return str(uuid4())
    
    async def generate_task_id(self) -> str:
        """Generate a new unique task ID.
        
        Returns:
            A new UUID-based task ID
        """
        return str(uuid4())
    
    async def close(self):
        """Close the database connection."""
        if self._initialized:
            await self.db_manager.close()
            self._initialized = False 