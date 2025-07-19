"""Database models for conversation history tracking."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field, ConfigDict

# Create declarative base for SQLAlchemy models
Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(String(255), index=True, nullable=True)
    agent_name = Column(String(100), index=True, nullable=False)
    title = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    meta = Column(JSON, nullable=True)
    root_id = Column(String(255), index=True, nullable=True)
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    agent_sessions = relationship("AgentSession", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    task_id = Column(String(64), nullable=True, index=True)
    role = Column(String(50), nullable=False, index=True)  # user, assistant, system
    content = Column(Text, nullable=False)
    agent_name = Column(String(100), nullable=True, index=True)
    tool_calls = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meta = Column(JSON, nullable=True)
    conversation = relationship("Conversation", back_populates="messages")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class AgentSession(Base):
    __tablename__ = "agent_sessions"
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    agent_name = Column(String(100), nullable=False, index=True)
    user_query = Column(Text, nullable=False)
    agent_response = Column(Text, nullable=True)
    tool_calls = Column(JSON, nullable=True)
    execution_time_ms = Column(Integer, nullable=True)
    success = Column(Boolean, default=True, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    meta = Column(JSON, nullable=True)
    conversation = relationship("Conversation", back_populates="agent_sessions")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class A2AContext(Base):
    """Store A2A conversation context for session continuity across tasks."""
    __tablename__ = "a2a_contexts"
    
    id = Column(Integer, primary_key=True, index=True)
    context_id = Column(String(255), unique=True, index=True, nullable=False)
    session_id = Column(String(255), index=True, nullable=True)  # Link to main conversation if needed
    agent_name = Column(String(100), nullable=False, index=True)
    conversation_history = Column(JSON, nullable=True)  # Store A2A message history
    agent_state = Column(JSON, nullable=True)  # Store agent-specific state/context
    extra_metadata = Column(JSON, nullable=True)  # Additional A2A metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    tasks = relationship("A2ATask", back_populates="context", cascade="all, delete-orphan")

class A2ATask(Base):
    """Store A2A task information and lifecycle state."""
    __tablename__ = "a2a_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    context_id = Column(String(255), ForeignKey("a2a_contexts.context_id"), nullable=False, index=True)
    parent_task_id = Column(String(255), nullable=True, index=True)  # For task chaining
    
    # A2A Task Fields
    kind = Column(String(50), default="task", nullable=False)  # 'task' per A2A spec
    status_state = Column(String(50), nullable=False, index=True)  # submitted, working, completed, failed, etc.
    status_message = Column(JSON, nullable=True)  # A2A message object
    
    # Task Content
    initial_message = Column(JSON, nullable=True)  # Original request message
    artifacts = Column(JSON, nullable=True)  # Task outputs/results
    message_history = Column(JSON, nullable=True)  # Task-specific message exchanges
    
    # Metadata
    agent_name = Column(String(100), nullable=False, index=True)
    execution_start = Column(DateTime(timezone=True), nullable=True)
    execution_end = Column(DateTime(timezone=True), nullable=True)
    error_details = Column(Text, nullable=True)
    extra_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    context = relationship("A2AContext", back_populates="tasks")
    interactions = relationship("A2AAgentInteraction", back_populates="task", cascade="all, delete-orphan")

class A2AAgentInteraction(Base):
    """Track interactions between agents in A2A protocol."""
    __tablename__ = "a2a_agent_interactions"
    
    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(String(255), unique=True, index=True, nullable=False)
    task_id = Column(String(255), ForeignKey("a2a_tasks.task_id"), nullable=False, index=True)
    
    # Agent Information
    client_agent = Column(String(100), nullable=False, index=True)  # Requesting agent
    remote_agent = Column(String(100), nullable=False, index=True)  # Target agent
    remote_agent_url = Column(String(500), nullable=True)  # A2A endpoint
    
    # Interaction Details
    interaction_type = Column(String(50), nullable=False, index=True)  # message_send, message_stream, etc.
    request_message = Column(JSON, nullable=True)  # Outgoing A2A message
    response_message = Column(JSON, nullable=True)  # Incoming A2A response
    
    # Status and Timing
    status = Column(String(50), nullable=False, index=True)  # pending, completed, failed
    started_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    
    extra_metadata = Column(JSON, nullable=True)
    
    # Relationships
    task = relationship("A2ATask", back_populates="interactions")

# Pydantic models for API responses
class ConversationResponse(BaseModel):
    id: int
    session_id: str
    user_id: Optional[str] = None
    agent_name: str
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    meta: Optional[dict] = None
    root_id: Optional[str] = None
    message_count: int = Field(default=0, description="Number of messages in conversation")
    model_config = ConfigDict(from_attributes=True)

class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    task_id: Optional[str] = None
    role: str
    content: str
    agent_name: Optional[str] = None
    tool_calls: Optional[List[dict]] = None
    created_at: datetime
    meta: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)

class AgentSessionResponse(BaseModel):
    id: int
    conversation_id: int
    agent_name: str
    user_query: str
    agent_response: Optional[str] = None
    tool_calls: Optional[List[dict]] = None
    execution_time_ms: Optional[int] = None
    success: bool
    error_message: Optional[str] = None
    created_at: datetime
    meta: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True) 

class A2AContextResponse(BaseModel):
    id: int
    context_id: str
    session_id: Optional[str] = None
    agent_name: str
    conversation_history: Optional[List[dict]] = None
    agent_state: Optional[dict] = None
    extra_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    is_active: bool
    task_count: int = Field(default=0, description="Number of tasks in this context")
    model_config = ConfigDict(from_attributes=True)

class A2ATaskResponse(BaseModel):
    id: int
    task_id: str
    context_id: str
    parent_task_id: Optional[str] = None
    kind: str
    status_state: str
    status_message: Optional[dict] = None
    initial_message: Optional[dict] = None
    artifacts: Optional[List[dict]] = None
    message_history: Optional[List[dict]] = None
    agent_name: str
    execution_start: Optional[datetime] = None
    execution_end: Optional[datetime] = None
    error_details: Optional[str] = None
    extra_metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class A2AAgentInteractionResponse(BaseModel):
    id: int
    interaction_id: str
    task_id: str
    client_agent: str
    remote_agent: str
    remote_agent_url: Optional[str] = None
    interaction_type: str
    request_message: Optional[dict] = None
    response_message: Optional[dict] = None
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    extra_metadata: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True) 