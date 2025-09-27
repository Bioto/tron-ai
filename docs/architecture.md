# Tron AI Architecture Documentation

## Overview

Tron AI is a multi-agent AI framework designed for personal and professional productivity, business operations, DevOps tasks, and integrations with external services. The system features an orchestrator (TronAgent) that delegates tasks to specialized domain agents via a swarm executor, with extensibility through the Model Context Protocol (MCP).

This document provides a comprehensive view of the system architecture, including layers, components, data flows, and design patterns.

## High-Level Architecture

### System Layers

```
┌─────────────────┐
│   CLI Layer     │ ← User Interface (Commands: ask, chat, scan, etc.)
├─────────────────┤
│ Orchestration   │ ← Executors (Swarm, Chain) - Task Routing & Execution
├─────────────────┤
│  Domain Layer   │ ← Agents (Business, DevOps, Productivity) - Specialized AI
├─────────────────┤
│ Integration     │ ← Modules (MCP, A2A, SSH) - External Service Adapters
├─────────────────┤
│  Utilities      │ ← Cross-cutting (LLM, Memory, IO) - Shared Services
├─────────────────┤
│ Persistence     │ ← Database (SQLite) - State & Memory Storage
└─────────────────┘
```

### Core Components

- **CLI (`tron_ai.cli`)**: Command-line interface using asyncclick. Entry point for user interactions.
- **AgentFactory (`tron_ai.cli.agent_factory`)**: Factory pattern for dynamic agent loading and caching.
- **Agents (`tron_ai.agents`)**: Domain-specific AI agents (17+ specialized agents).
- **Executors (`tron_ai.executors`)**: Workflow engines (Swarm for multi-agent orchestration).
- **MCP (`tron_ai.modules.mcp`)**: Model Context Protocol for dynamic tool discovery and distributed execution.
- **Database (`tron_ai.database`)**: SQLite-based persistence for conversations and memory.
- **Utils (`tron_ai.utils`)**: Shared utilities (LLM clients, memory management, IO).

## Data Flow

### User Query to Response Flow

```
User Query (CLI Command)
    ↓
AgentFactory (Load Agents)
    ↓
SwarmExecutor (State Machine)
    ├── generate_tasks (LLM → Task List)
    ├── assign_agents (Selector → Agent Mapping)
    ├── enrich_context (Memory → Contextual Tasks)
    ├── execute_tasks (Parallel → Tool Execution)
    └── handle_results (Synthesis → Final Report)
    ↓
Database Persistence (Conversations/Messages)
    ↓
Response to User
```

### Key Data Structures

- **SwarmState**: Pydantic model tracking query, tasks, agents, results, and session IDs.
- **Task**: Domain model for executable work units with descriptions and assignments.
- **Agent**: Pydantic entity with name, prompt, and tool manager.
- **Conversation/Message**: Database models for chat history and memory.

## Design Patterns

### Factory Pattern (AgentFactory)

Centralizes agent creation with:
- Registry-based loading (core, productivity, devops, business, MCP agents)
- Caching for performance
- Graceful error handling for missing dependencies

### State Machine Pattern (SwarmExecutor)

Uses StateGraph for workflow orchestration:
- Nodes: Async functions processing state
- Edges: Conditional transitions
- Cycle detection and timeout safety

### Proxy Pattern (MCP ToolRegistry)

Dynamically creates proxies for remote MCP tools:
- Async function wrappers
- Connection pooling
- Retry logic with exponential backoff

### Repository Pattern (DatabaseManager)

Abstracts data persistence:
- Async CRUD operations
- Transaction management
- Race condition handling

## Agent Architecture

### TronAgent (Orchestrator)

- **Role**: Central coordinator delegating to specialized agents
- **Capabilities**: Swarm execution, memory integration, proactive task management
- **Prompt Strategy**: Action-oriented with memory context injection

### Specialized Agents

Grouped by domain (DDD Bounded Contexts):

- **Business (8 agents)**: Marketing, Sales, Customer Success, Financial Planning, AI Ethics, Content Creation, Community Relations
- **DevOps (4 agents)**: Code Scanner, Editor, Repo Scanner, SSH
- **Productivity (5 agents)**: Google, Android, Todoist, Notion, WordPress

Each agent:
- Inherits from base `Agent` model
- Has domain-specific prompts and tools
- Uses keyword-only arguments for tool calls
- Maintains actual IDs for entities (e.g., Message IDs in Gmail)

## Executor Architecture

### SwarmExecutor

Multi-agent task delegation using StateGraph:

```python
graph = StateGraph()
graph.add_node("generate_tasks", tools.process_tasks)
graph.add_node("assign_agents", tools.assign_agents)
graph.add_node("execute_tasks", tools.execute_tasks)
graph.add_edge("generate_tasks", "assign_agents", condition=lambda s: bool(s.tasks))
```

### Safety Features

- **Cycle Detection**: Prevents infinite loops by tracking visited nodes
- **Timeout Protection**: Async timeouts on node execution (30s default)
- **Error Handling**: Graceful failure with logging and fallback paths

## MCP Integration

### Components

- **Client**: Multi-server connection manager (Stdio/SSE transports)
- **Manager**: Singleton for MCP agent initialization
- **ToolRegistry**: Dynamic tool discovery and proxy creation
- **ConnectionPool**: Thread-safe connection management

### Workflow

```
1. Load MCP server configs (mcp_servers.json)
2. Initialize connections (Stdio/SSE)
3. Discover available tools
4. Create proxy functions for remote calls
5. Register as agents in factory
```

## Database Architecture

### Schema

- **Conversation**: Session tracking with metadata
- **Message**: Chat history with tool calls
- **A2AContext**: Agent-to-agent conversation state
- **A2ATask**: Distributed task lifecycle

### Memory Integration

- **DatabaseManager**: Async CRUD with race protection
- **Memory Utils**: Context retrieval and injection
- **ChromaDB**: Vector storage for embeddings

## Security Considerations

- Environment variable management for API keys
- MCP server authentication (configurable)
- Input validation for tool calls
- Connection encryption for sensitive data

## Performance Characteristics

- **Async-First**: Full asyncio stack for I/O operations
- **Parallel Execution**: Swarm tasks run concurrently
- **Caching**: Agent and tool result caching
- **Optimized JSON**: orjson for fast serialization

## Scalability

- **Horizontal**: MCP enables distributed tool execution
- **Vertical**: Async patterns maximize I/O throughput
- **Database**: SQLite for development, PostgreSQL for production
- **Agent Count**: Scales to 100s with proper sharding

## Development Guidelines

- **Async Everywhere**: All I/O operations are async
- **Pydantic Models**: Type-safe state management
- **Keyword Arguments Only**: Tool calls enforce kwargs
- **Modular Imports**: Graceful degradation for missing dependencies
- **Comprehensive Logging**: Structured logging throughout

## Deployment Considerations

- **Containerization**: Docker support for MCP servers
- **Configuration**: Environment-based config management
- **Monitoring**: Built-in logging and error tracking
- **Testing**: Async test support with coverage requirements

---

This architecture prioritizes modularity, extensibility, and safety while maintaining high performance for AI agent orchestration. The MCP integration provides a powerful plugin system for extending capabilities without code changes.
