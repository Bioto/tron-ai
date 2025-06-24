"""
Enhanced exception hierarchy for Tron AI with context and specific error types.

This module provides a comprehensive exception hierarchy that includes:
- Context information for better debugging
- Specific exception types for different error scenarios
- Structured error data for logging and monitoring
"""

from typing import Optional, Dict, Any


class TronAIError(Exception):
    """Base exception class for all TronAI errors."""
    
    def __init__(self, message: str, context: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.context = context or {}


class ExecutionError(TronAIError):
    """Raised when there is an error during task execution."""
    pass


class AgentError(TronAIError):
    """Raised when there is an error related to agents."""
    pass


class TaskError(TronAIError):
    """Raised when there is an error related to tasks."""
    pass


class ConfigError(TronAIError):
    """Raised when there is an error in configuration."""
    pass


# New specific exceptions
class APIKeyError(ConfigError):
    """Raised when API keys are missing or invalid."""
    pass


class MemoryError(TronAIError):
    """Raised when memory operations fail."""
    pass


class TimeoutError(ExecutionError):
    """Raised when operations exceed timeout limits."""
    
    def __init__(self, message: str, timeout: float, operation: str):
        super().__init__(message, {"timeout": timeout, "operation": operation})
        self.timeout = timeout
        self.operation = operation


class RetryExhaustedError(ExecutionError):
    """Raised when all retry attempts have been exhausted."""
    
    def __init__(self, message: str, attempts: int, last_error: Exception):
        super().__init__(message, {"attempts": attempts, "last_error": str(last_error)})
        self.attempts = attempts
        self.last_error = last_error


class LLMError(TronAIError):
    """Base class for LLM-related errors."""
    pass


class LLMResponseError(LLMError):
    """Raised when LLM response cannot be parsed or is invalid."""
    
    def __init__(self, message: str, raw_response: str, expected_format: str):
        super().__init__(message, {
            "raw_response": raw_response[:500],  # Truncate for logging
            "expected_format": expected_format
        })


class ToolExecutionError(ExecutionError):
    """Raised when tool execution fails."""
    
    def __init__(self, message: str, tool_name: str, error: Exception):
        super().__init__(message, {
            "tool_name": tool_name,
            "error": str(error)
        })
        self.tool_name = tool_name


class CLIError(TronAIError):
    """Base exception for CLI-related errors."""
    pass


class ValidationError(TronAIError):
    """Raised when input validation fails."""
    
    def __init__(self, message: str, field: str, value: Any):
        super().__init__(message, {
            "field": field,
            "value": str(value)[:100]  # Truncate large values
        })
        self.field = field
        self.value = value
