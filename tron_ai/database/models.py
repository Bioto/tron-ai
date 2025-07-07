"""Database models for conversation history tracking."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pydantic import BaseModel, Field

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
        print(f"[DEBUG] Message.tool_calls: {kwargs.get('tool_calls')}")

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
        print(f"[DEBUG] AgentSession.tool_calls: {kwargs.get('tool_calls')}")

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
    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True

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
    class Config:
        from_attributes = True 