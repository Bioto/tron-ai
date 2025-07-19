# Tron AI API Documentation

Executors, agents, models, and related concepts are key building blocks in the Tron AI framework. Below are explanations of each major category, followed by usage examples. These draw from the project's architecture and follow clean code, performance optimization, and domain-driven design principles.

## Table of Contents

- [Executors](#executors)
- [Agents](#agents)
- [Models](#models)
- [Utils](#utils)
- [Modules](#modules)
- [Exceptions](#exceptions)
- [Constants](#constants)

## Executors

Executors are the "runners" or orchestration layers in Tron AI that handle how tasks are processed and executed. They take inputs (like user queries or prompts) and coordinate with LLMs, agents, or other components to produce outputs. Think of them as the engine that drives task completion, supporting different execution strategies for flexibility.

- **Purpose**: They abstract away the complexity of running AI tasks, allowing for simple completions, chained operations, or multi-agent swarms.
- **Why They Matter**: Executors make the system modular—swap them based on task complexity (e.g., use Swarm for collaborative AI, Completion for quick queries).

### BaseExecutor

Abstract base class for all executors, providing common configuration and logging.

```python
from tron_ai.executors.base import BaseExecutor, ExecutorConfig

class MyExecutor(BaseExecutor):
    def execute(self, *args, **kwargs):
        pass
```

### AgentExecutor

Handles execution of single or multiple agents, supporting follow-up queries.

```python
from tron_ai.executors.agent import AgentExecutor

executor = AgentExecutor(config=ExecutorConfig(client=llm_client))
response = await executor.execute(user_query="Task", agent=my_agent)
```

### CompletionExecutor

Performs simple LLM completions without agents.

```python
from tron_ai.executors.completion import CompletionExecutor

executor = CompletionExecutor(config=ExecutorConfig(client=llm_client, prompt=my_prompt))
response = await executor.execute(user_query="Query")
```

### ChainExecutor

Executes sequences of prompts in a chain.

```python
from tron_ai.executors.chain import ChainExecutor, Step

executor = ChainExecutor(config=ExecutorConfig(client=llm_client))
results = executor.execute("Query", steps=[Step(prompt=p1), Step(prompt=p2)])
```

### SwarmExecutor

Orchestrates multiple agents using task decomposition and delegation.

```python
from tron_ai.executors.swarm import SwarmExecutor, SwarmState

executor = SwarmExecutor(state=SwarmState(agents=my_agents))
result = await executor.execute(user_query="Complex task")
```

## Agents

Agents are intelligent "workers" that perform specific tasks using prompts, tools, and reasoning. They're like specialized AI personas that can think, use tools (e.g., APIs, databases), and respond to queries.

- **Purpose**: Agents encapsulate domain-specific logic (e.g., marketing, code scanning) and can be orchestrated by executors.
- **Why They Matter**: Agents enable modular, reusable AI behaviors. In a swarm, they collaborate (e.g., one agent researches, another analyzes).

### Base Agent

Foundation for all agents, defining name, description, prompt, and tools.

```python
from tron_ai.models.agent import Agent
from adalflow.core.tool_manager import ToolManager
from tron_ai.models.prompts import Prompt

agent = Agent(
    name="MyAgent",
    description="Description",
    prompt=Prompt(text="Prompt template"),
    tool_manager=ToolManager(tools=[])
)
```

### TronAgent

Core orchestration agent that delegates tasks to other agents via swarm.

```python
from tron_ai.agents.tron.agent import TronAgent

agent = TronAgent()
```

### GoogleAgent

Manages Google services like email and calendar.

```python
from tron_ai.agents.productivity.google.agent import GoogleAgent

agent = GoogleAgent()
```

<!-- Add similar for other key agents -->

Add entries for other specialized agents as needed, following the same pattern. Agents are organized by category (e.g., business, devops, productivity) in the codebase.

## Models

Models refer to data structures and configurations that represent core entities in the system. These aren't ML models (like neural nets) but rather Python classes for configs, prompts, tasks, etc.

- **Purpose**: They provide typed, structured ways to define and pass data between components.
- **Why They Matter**: They ensure consistency and type safety across the app.

### ExecutorConfig

Configuration for executors, including LLM client and logging.

```python
from tron_ai.models.executors import ExecutorConfig

config = ExecutorConfig(client=llm_client, logging=True)
```

### Prompt

Template for LLM prompts with variable substitution.

```python
from tron_ai.models.prompts import Prompt

prompt = Prompt(text="Template {var}")
rendered = prompt.build(var="value")
```

### Task

Represents a unit of work with operations and dependencies.

```python
from tron_ai.modules.tasks.models import Task

task = Task(description="Task desc", operations=["op1", "op2"], agent=my_agent)
```

## Utils

Utils are helper modules for common operations, often focused on I/O, concurrency, or LLM interactions.

- **Purpose**: Support the main components with reusable functions (e.g., file handling, LLM calls).
- **Why They Matter**: They optimize performance (e.g., async I/O) and keep the codebase DRY.

### LLMClient

Wrapper for LLM interactions, supporting function calling and retries.

```python
from tron_ai.utils.llm.LLMClient import LLMClient, LLMClientConfig
from adalflow import OpenAIClient

config = LLMClientConfig(model_name="gpt-4o")
client = LLMClient(client=OpenAIClient(), config=config)
response = client.call(user_query="Query", system_prompt=my_prompt)
```

## Modules

Modules are higher-level features or integrations that build on the core components (e.g., for specific protocols or services).

- **Purpose**: Handle cross-cutting concerns like task management, external connections, or protocols.
- **Why They Matter**: They extend the core system for real-world integrations (e.g., databases, remote execution).

### MCPAgentManager

Manages multiple MCP agents connected to different servers.

```python
from tron_ai.modules.mcp.manager import MCPAgentManager

manager = MCPAgentManager()
await manager.initialize("mcp_servers.json")
agent = manager.get_default_agent()
```

### DatabaseManager

Handles database operations for conversation history.

```python
from tron_ai.database.manager import DatabaseManager, DatabaseConfig

config = DatabaseConfig()
manager = DatabaseManager(config)
await manager.initialize()
conv = await manager.create_conversation(session_id="id", agent_name="agent")
```

## Exceptions

Custom exceptions for error handling in Tron AI.

- **Purpose**: Provide meaningful error handling with context-specific messages.
- **Why They Matter**: Improve debugging and robustness.

```python
from tron_ai.exceptions import TronAIError, ExecutionError, AgentError
```

## Constants

Global configuration constants like timeouts and limits used across the app for consistency.

- **Purpose**: Define limits, timeouts, and defaults to prevent magic numbers.
- **Why They Matter**: Make configuration easy to tweak and maintain.

```python
from tron_ai.constants import LLM_MAX_RETRIES, TIMEOUT_TASK_EXECUTION
```