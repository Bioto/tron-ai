"""
Constants and configuration values for Tron AI.

This module centralizes all magic numbers and configuration constants
used throughout the application.
"""

# LLM Client Constants
LLM_MAX_RETRIES = 25
LLM_DEFAULT_TEMPERATURE = 0.0
LLM_MAX_PARALLEL_TOOLS = 5

# Timeout Constants (in seconds)
TIMEOUT_MCP_AGENT = 1024
TIMEOUT_COMPLETION = 1024
TIMEOUT_DEFAULT = 60
TIMEOUT_MCP_INIT = 2
TIMEOUT_TASK_EXECUTION = 2048

# CLI Constants
CLI_MEMORY_QUERY_LIMIT = 5
CLI_CHAT_HISTORY_CONTEXT_SIZE = 100

# Memory Time Ranges
MEMORY_TIME_TODAY = "TODAY"
MEMORY_TIME_WEEK = "WEEK"
MEMORY_TIME_MONTH = "MONTH"
MEMORY_TIME_ALL = "ALL"

# Memory Time Deltas (in days)
MEMORY_DAYS_WEEK = 7
MEMORY_DAYS_MONTH = 30

# Agent Executor Constants
AGENT_MIN_REQUIRED = 1

# File Operation Constants
FILE_READ_CHUNK_SIZE = 1024 * 1024  # 1MB
FILE_MAX_SIZE = 100 * 1024 * 1024  # 100MB

# Connection Pool Settings
CONNECTION_POOL_SIZE = 10
CONNECTION_POOL_TIMEOUT = 30

# Retry Settings
RETRY_MAX_ATTEMPTS = 3
RETRY_BACKOFF_FACTOR = 2
RETRY_MAX_BACKOFF = 60  # seconds
