"""Database manager for conversation history operations."""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select, delete, desc
from sqlalchemy.exc import IntegrityError

from .config import DatabaseConfig
from .models import Base, Conversation, Message, AgentSession
from .models import ConversationResponse, MessageResponse, AgentSessionResponse

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Manages database operations for conversation history tracking."""
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = create_async_engine(
            config.database_url,
            echo=config.echo,
            pool_size=config.pool_size,
            max_overflow=config.max_overflow,
            pool_timeout=config.pool_timeout,
            pool_recycle=config.pool_recycle,
        )
        self.session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        self._initialized = False

    async def initialize(self):
        if self._initialized:
            return
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        self._initialized = True
        logger.info("Database initialized successfully")

    async def close(self):
        await self.engine.dispose()
        logger.info("Database connections closed")

    @asynccontextmanager
    async def get_session(self):
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Conversation Management
    async def create_conversation(self, session_id: str, agent_name: str, user_id: Optional[str] = None, title: Optional[str] = None, meta: Optional[Dict[str, Any]] = None, root_id: Optional[str] = None) -> ConversationResponse:
        async with self.get_session() as session:
            conversation = Conversation(
                session_id=session_id,
                user_id=user_id,
                agent_name=agent_name,
                title=title,
                meta=meta,
                root_id=root_id,
            )
            session.add(conversation)
            await session.flush()
            return ConversationResponse.model_validate(conversation)

    async def get_conversation(self, session_id: str) -> Optional[ConversationResponse]:
        async with self.get_session() as session:
            stmt = select(Conversation).where(Conversation.session_id == session_id)
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()
            if conversation:
                return ConversationResponse.model_validate(conversation)
            return None

    async def list_conversations(self, user_id: Optional[str] = None, agent_name: Optional[str] = None, limit: int = 50, offset: int = 0, active_only: bool = True) -> List[ConversationResponse]:
        async with self.get_session() as session:
            stmt = select(Conversation)
            if user_id:
                stmt = stmt.where(Conversation.user_id == user_id)
            if agent_name:
                stmt = stmt.where(Conversation.agent_name == agent_name)
            if active_only:
                stmt = stmt.where(Conversation.is_active == True)
            stmt = stmt.order_by(desc(Conversation.updated_at))
            stmt = stmt.offset(offset).limit(limit)
            result = await session.execute(stmt)
            conversations = result.scalars().all()
            return [ConversationResponse.model_validate(conv) for conv in conversations]

    async def update_conversation(self, session_id: str, title: Optional[str] = None, is_active: Optional[bool] = None, meta: Optional[Dict[str, Any]] = None) -> Optional[ConversationResponse]:
        async with self.get_session() as session:
            stmt = select(Conversation).where(Conversation.session_id == session_id)
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()
            if not conversation:
                return None
            if title is not None:
                conversation.title = title
            if is_active is not None:
                conversation.is_active = is_active
            if meta is not None:
                conversation.meta = meta
            conversation.updated_at = datetime.now(timezone.utc)
            return ConversationResponse.model_validate(conversation)

    # Message Management
    async def add_message(self, session_id: str, role: str, content: str, agent_name: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None, meta: Optional[Dict[str, Any]] = None, task_id: Optional[str] = None, root_id: Optional[str] = None) -> Optional[MessageResponse]:
        async with self.get_session() as session:
            stmt = select(Conversation).where(Conversation.session_id == session_id)
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()
            if not conversation:
                # Try to create conversation, handle race condition
                # If root_id is not provided, try to get from meta/context
                root_id_to_use = root_id or (meta.get('root_id') if meta and 'root_id' in meta else session_id)
                conversation = Conversation(
                    session_id=session_id,
                    agent_name=agent_name or "swarm",
                    title=f"Swarm session {session_id}",
                    meta={"auto_created": True},
                    root_id=root_id_to_use,
                )
                session.add(conversation)
                try:
                    await session.flush()
                except IntegrityError:
                    await session.rollback()
                    # Fetch the conversation that was just created by another process
                    result = await session.execute(stmt)
                    conversation = result.scalar_one_or_none()
                    if not conversation:
                        raise  # Unexpected: should exist now
            message = Message(
                conversation_id=conversation.id,
                task_id=task_id,
                role=role,
                content=content,
                agent_name=agent_name,
                tool_calls=tool_calls,
                meta=meta
            )
            session.add(message)
            conversation.updated_at = datetime.now(timezone.utc)
            await session.flush()
            return MessageResponse.model_validate(message)

    async def get_messages(self, session_id: str, limit: int = 100, offset: int = 0) -> List[MessageResponse]:
        async with self.get_session() as session:
            stmt = (
                select(Message)
                .join(Conversation)
                .where(Conversation.session_id == session_id)
                .order_by(Message.created_at)
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            messages = result.scalars().all()
            return [MessageResponse.model_validate(msg) for msg in messages]

    async def get_conversation_history(self, session_id: str, max_messages: int = 50) -> List[Dict[str, str]]:
        messages = await self.get_messages(session_id, limit=max_messages)
        return [
            {
                "role": msg.role,
                "content": msg.content,
                "agent_name": msg.agent_name
            }
            for msg in messages
        ]

    # Agent Session Management
    async def add_agent_session(self, session_id: str, agent_name: str, user_query: str, agent_response: Optional[str] = None, tool_calls: Optional[List[Dict[str, Any]]] = None, execution_time_ms: Optional[int] = None, success: bool = True, error_message: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Optional[AgentSessionResponse]:
        async with self.get_session() as session:
            stmt = select(Conversation).where(Conversation.session_id == session_id)
            result = await session.execute(stmt)
            conversation = result.scalar_one_or_none()
            if not conversation:
                return None
            agent_session = AgentSession(
                conversation_id=conversation.id,
                agent_name=agent_name,
                user_query=user_query,
                agent_response=agent_response,
                tool_calls=tool_calls,
                execution_time_ms=execution_time_ms,
                success=success,
                error_message=error_message,
                meta=meta
            )
            session.add(agent_session)
            await session.flush()
            return AgentSessionResponse.model_validate(agent_session)

    async def get_agent_sessions(self, session_id: str, limit: int = 50, offset: int = 0) -> List[AgentSessionResponse]:
        async with self.get_session() as session:
            stmt = (
                select(AgentSession)
                .join(Conversation)
                .where(Conversation.session_id == session_id)
                .order_by(desc(AgentSession.created_at))
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            sessions = result.scalars().all()
            return [AgentSessionResponse.model_validate(session) for session in sessions]

    # Analytics and Statistics
    async def get_conversation_stats(self, user_id: Optional[str] = None, agent_name: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
        async with self.get_session() as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            conv_stmt = select(Conversation).where(Conversation.created_at >= cutoff_date)
            msg_stmt = select(Message).join(Conversation).where(Conversation.created_at >= cutoff_date)
            session_stmt = select(AgentSession).join(Conversation).where(Conversation.created_at >= cutoff_date)
            if user_id:
                conv_stmt = conv_stmt.where(Conversation.user_id == user_id)
                msg_stmt = msg_stmt.where(Conversation.user_id == user_id)
                session_stmt = session_stmt.where(Conversation.user_id == user_id)
            if agent_name:
                conv_stmt = conv_stmt.where(Conversation.agent_name == agent_name)
                msg_stmt = msg_stmt.where(Conversation.agent_name == agent_name)
                session_stmt = session_stmt.where(Conversation.agent_name == agent_name)
            conv_result = await session.execute(conv_stmt)
            msg_result = await session.execute(msg_stmt)
            session_result = await session.execute(session_stmt)
            conversations = conv_result.scalars().all()
            messages = msg_result.scalars().all()
            agent_sessions = session_result.scalars().all()
            return {
                "total_conversations": len(conversations),
                "total_messages": len(messages),
                "total_agent_sessions": len(agent_sessions),
                "active_conversations": len([c for c in conversations if c.is_active]),
                "avg_messages_per_conversation": len(messages) / max(len(conversations), 1),
                "successful_sessions": len([s for s in agent_sessions if s.success]),
                "failed_sessions": len([s for s in agent_sessions if not s.success]),
                "avg_execution_time_ms": sum(s.execution_time_ms or 0 for s in agent_sessions) / max(len(agent_sessions), 1)
            }

    # Cleanup and Maintenance
    async def cleanup_old_conversations(self, days: int = 90) -> int:
        """Deletes conversations and their related messages/sessions older than `days`."""
        async with self.get_session() as session:
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
            stmt = delete(Conversation).where(Conversation.updated_at < cutoff_date)
            result = await session.execute(stmt)
            return result.rowcount 