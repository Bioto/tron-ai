"""
Tron AI - An intelligent AI assistant framework.

This package provides tools for building AI agents with memory,
tool execution capabilities, and robust error handling.
"""

from tron_intelligence.exceptions import (
    # Base exceptions
    TronAIError,
    ExecutionError,
    AgentError,
    TaskError,
    ConfigError,
    
    # Specific exceptions
    APIKeyError,
    MemoryError,
    TimeoutError,
    RetryExhaustedError,
    LLMError,
    LLMResponseError,
    ToolExecutionError,
    CLIError,
    ValidationError,
)

__version__ = "0.1.0"

__all__ = [
    # Base exceptions
    "TronAIError",
    "ExecutionError",
    "AgentError",
    "TaskError",
    "ConfigError",
    
    # Specific exceptions
    "APIKeyError",
    "MemoryError",
    "TimeoutError",
    "RetryExhaustedError",
    "LLMError",
    "LLMResponseError",
    "ToolExecutionError",
    "CLIError",
    "ValidationError",
]
