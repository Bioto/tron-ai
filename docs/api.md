# Tron AI API Documentation

## Table of Contents

- [Executors](#executors)
  - [BaseExecutor](#baseexecutor)
  - [CompletionExecutor](#completionexecutor)
  - [ChainExecutor](#chainexecutor)
  - [AgentExecutor](#agentexecutor)
- [Agents](#agents)
  - [Agent Base Class](#agent-base-class)
  - [Built-in Agents](#built-in-agents)
- [Utils](#utils)
  - [LLMClient](#llmclient)
  - [ConnectionManager](#connectionmanager)
- [Models](#models)
- [Exceptions](#exceptions)

## Executors

### BaseExecutor

Abstract base class for all executors.

```python
from tron_ai.executors.base import BaseExecutor, ExecutorConfig

class BaseExecutor(ABC):
    def __init__(self, config: ExecutorConfig, *args, **kwargs):
        """Initialize base executor.
        
        Args:
            config: Executor configuration including client and optional prompt
        """
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> BaseModel:
        """Execute the task. Must be implemented by subclasses."""
```

### CompletionExecutor

Simple completion executor for direct LLM calls.

```python
from tron_ai.executors.completion import CompletionExecutor

executor = CompletionExecutor(config=ExecutorConfig(client=llm_client))

# Basic execution
response = executor.execute(
    user_query="What is Python?",
    tool_manager=None,
    system_prompt=Prompt(prompt="You are a helpful assistant")
)
```

### ChainExecutor

Executes multi-step reasoning chains.

```python
from tron_ai.executors.chain import ChainExecutor, Step

executor = ChainExecutor(config=ExecutorConfig(client=llm_client))

results = executor.execute(
    "Write a story",
    steps=[
        Step(prompt=Prompt(prompt="Create character")),
        Step(prompt=Prompt(prompt="Develop plot")),
        Step(prompt=Prompt(prompt="Write story"))
    ]
)
```

### AgentExecutor

Orchestrates multiple agents for complex tasks.

```python
from tron_ai.executors.agents import AgentExecutor

# Synchronous execution
executor = AgentExecutor(config=config, agents=[agent1, agent2])
result = await executor.execute(
    user_query="Complex task",
    parallel=False  # Sequential execution
)

# Parallel execution
result = await executor.execute(
    user_query="Complex task",
    parallel=True  # Parallel execution where possible
)
```

## Agents

### Agent Base Class

```python
from tron_ai.executors.agents.models.agent import Agent

class Agent(BaseModel):
    name: str
    description: str
    prompt: Prompt
    tools: Optional[ToolManager] = None
    supports_multiple_operations: bool = True
```

### Built-in Agents

#### CodeAgent

Analyzes and manipulates code.

```python
from tron_ai.executors.agents.builtin import CodeAgent

agent = CodeAgent()
# Tools: analyze_code_structure, check_code_quality, format_code,
#        generate_tests, analyze_dependencies, suggest_improvements
```

#### DockerAgent

Manages Docker containers.

```python
from tron_ai.executors.agents.builtin import DockerAgent

agent = DockerAgent()
# Tools: list_containers, create_container, start_container,
#        stop_container, remove_container, get_logs, inspect_container
```

#### FileAgent

Handles file system operations.

```python
from tron_ai.executors.agents.builtin import FileAgent

agent = FileAgent()
# Tools: create_file, read_file, update_file, delete_file, list_directory
```

#### MCPAgent

Model Context Protocol operations.

```python
from tron_ai.modules.mcp.agent import Agent as MCPAgent

# MCP agents are managed through MCPAgentManager
# See MCPAgentManager section below for usage
```

#### MCPAgentManager

Manages a pool of MCPAgent instances, each connected to a different MCP server. Provides async initialization, dynamic agent addition/removal, and config-based reloading.

```python
from tron_ai.modules.mcp.manager import MCPAgentManager

manager = MCPAgentManager()
await manager.initialize("mcp_servers.json")  # Load all agents from config

# Get default agent
agent = manager.get_default_agent()

# Get agent by name
agent = manager.get_agent("my-mcp-server")

# Add a new agent
await manager.add_agent("new-server", server_config)

# Remove an agent
await manager.remove_agent("old-server")

# Reload all agents
await manager.reload_agents("mcp_servers.json")

# Cleanup all agents
await manager.cleanup()
```

#### SearchAgent

Web search capabilities.

```python
from tron_ai.executors.agents.builtin import SearchAgent

agent = SearchAgent()
# Tools: search_internet
```

## Utils

### LLMClient

Wrapper for LLM operations with tool support.

```python
from tron_ai.utils.llm.LLMClient import LLMClient, LLMClientConfig

config = LLMClientConfig(
    model_name="gpt-4o",
    json_output=True,
    logging=False
)

client = LLMClient(client=OpenAIClient(), config=config)

# Simple call
response = client.call(
    user_query="Question",
    prompt=Prompt(prompt="Template", output_format=ResponseModel)
)

# Function call with tools
response = client.fcall(
    user_query="Question",
    system_prompt=Prompt(...),
    tool_manager=ToolManager(tools=[...]),
    max_parallel_tools=5
)
```

#### LLMClient Methods

- `call(user_query, prompt, prompt_kwargs)`: Direct LLM call
- `fcall(user_query, system_prompt, tool_manager, prompt_kwargs, max_parallel_tools)`: Function calling with tools
- `_build_generator(prompt, output_processors, override_json_format)`: Build generator instance

### ConnectionManager

Manages database connections and resource lifecycle.

```python
from tron_ai.utils.concurrency.connection_manager import get_connection_manager

manager = get_connection_manager()

# Get ChromaDB client
client = manager.chroma_client

# Get memory collection
memory = manager.memory_collection

# Context manager usage
with manager.get_connection("chroma") as conn:
    # Use connection
    pass

# Async context manager
async with manager.get_async_connection("memory") as conn:
    # Use connection
    pass

# Manual cleanup
manager.close_connection("all")
```

## Models

### ExecutorConfig

```python
from tron_ai.executors.base import ExecutorConfig

config = ExecutorConfig(
    client=llm_client,      # Required: LLMClient instance
    prompt=prompt,          # Optional: Default prompt
    logging=True           # Optional: Enable logging
)
```

### Prompt

```python
from tron_ai.prompts.models import Prompt

prompt = Prompt(
    prompt="Template with {variable}",
    output_format=ResponseModel  # Pydantic model
)

# Build prompt with variables
rendered = prompt.build(variable="value")
```

### Task

```python
from tron_ai.modules.tasks import Task

task = Task(
    identifier="task-001",
    description="Task description",
    priority=1,
    dependencies=["task-000"],
    operations=["operation1", "operation2"],
    assigned_agent=None,
    result=None
)
```

## Exceptions

Custom exception hierarchy for better error handling.

```python
from tron_ai.exceptions import (
    TronAIError,      # Base exception
    ExecutionError,   # Task execution errors
    AgentError,       # Agent-related errors
    TaskError,        # Task-related errors
    ConfigError       # Configuration errors
)

try:
    # Execute task
    pass
except ExecutionError as e:
    # Handle execution error
    pass
except TronAIError as e:
    # Handle any Tron AI error
    pass
```

## Constants

Centralized configuration constants.

```python
from tron_ai.constants import (
    # LLM Settings
    LLM_MAX_RETRIES,
    LLM_DEFAULT_TEMPERATURE,
    LLM_MAX_PARALLEL_TOOLS,
    
    # Timeouts
    TIMEOUT_MCP_AGENT,
    TIMEOUT_COMPLETION,
    TIMEOUT_DEFAULT,
    
    # Memory Settings
    CLI_MEMORY_QUERY_LIMIT,
    MEMORY_TIME_TODAY,
    MEMORY_TIME_WEEK,
    MEMORY_TIME_MONTH,
    MEMORY_TIME_ALL,
    
    # Connection Settings
    CONNECTION_POOL_SIZE,
    CONNECTION_POOL_TIMEOUT
)
```

## Usage Examples

### Basic Completion

```python
from tron_ai.utils.llm.LLMClient import LLMClient, LLMClientConfig
from tron_ai.executors.completion import CompletionExecutor
from tron_ai.executors.base import ExecutorConfig
from tron_ai.prompts.models import Prompt

# Setup
client = LLMClient(
    client=OpenAIClient(),
    config=LLMClientConfig(model_name="gpt-4o")
)
executor = CompletionExecutor(
    config=ExecutorConfig(client=client)
)

# Execute
response = executor.execute(
    user_query="Explain Python decorators",
    system_prompt=Prompt(prompt="You are a Python expert")
)
```

### Agent-Based Task

```python
from tron_ai.executors.agents import AgentExecutor
from tron_ai.executors.agents.builtin import CodeAgent, FileAgent

async def analyze_project():
    agents = [CodeAgent(), FileAgent()]
    executor = AgentExecutor(
        config=ExecutorConfig(client=client),
        agents=agents
    )
    
    result = await executor.execute(
        user_query="Analyze the Python files in this project",
        parallel=True
    )
    
    print(result.report)
```

### Memory-Enabled Assistant

```python
from tron_ai.cli import generate_memory_tool

# Create memory tool
memory_tool = generate_memory_tool()

# Use in executor
response = executor.execute(
    user_query="Remember that my favorite color is blue",
    tool_manager=memory_tool
)

# Query memories
response = executor.execute(
    user_query="What is my favorite color?",
    tool_manager=memory_tool
)
``` 